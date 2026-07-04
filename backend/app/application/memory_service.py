"""应用层 · llmwiki 记忆、章节全文与衔接包管理。

职责：
- 卷记忆重建（rebuild_volume_memory）
- 章节定稿后同步到 llmwiki（全文、摘要、时间线、伏笔、衔接包）
- 章节快照写入文件系统
- 章节衔接包自动生成
- wiki 页面 CRUD（upsert/append/delete + revisions）
- 结构化记录创建 + wiki 同步
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException

from ..domain.models import AiWorkflowIn
from ..infrastructure.database import (
    connect,
    create_chapter_bridge,
    get_chapter_bridge,
    new_id,
    row_to_dict,
    rows_to_dicts,
    utc_now,
)
from ..infrastructure.storage import project_root, safe_wiki_path
from .context_builder import trim_text
from ..workflows.generation import (
    clean_chapter_title,
    narrative_focus_from_brief,
    structured_output_for_workflow,
)
from ..workflows.llm_client import resolve_model_config, run_model_or_stub

BODY_MEMORY_PATH = "关键记忆.md"
CHAPTER_INDEX_PATH = "chapters/index.md"
BRIDGE_INDEX_PATH = "bridges/index.md"


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def _positive_int(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return {}


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return []
        return decoded if isinstance(decoded, list) else []
    return []


def _chapter_slug(chapter: dict[str, Any]) -> str:
    chapter_number = _positive_int(chapter.get("chapter_number")) or 0
    return f"chapter-{chapter_number:03}"


def _chapter_title(chapter: dict[str, Any]) -> str:
    chapter_number = chapter.get("chapter_number") or 0
    return chapter.get("title") or f"第 {chapter_number} 章"


def _bridge_json(bridge: dict[str, Any] | None) -> dict[str, Any]:
    if not bridge:
        return {}
    return _json_dict(bridge.get("bridge_json"))


def _format_list(values: list[Any], *, key: str = "") -> str:
    lines: list[str] = []
    for item in values:
        if isinstance(item, dict):
            if key and item.get(key):
                text = str(item.get(key))
            else:
                text = "；".join(f"{k}：{v}" for k, v in item.items() if v not in (None, "", []))
        else:
            text = str(item)
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines) if lines else "- 无"


# ---------------------------------------------------------------------------
# 卷记忆
# ---------------------------------------------------------------------------
def volume_name_for_chapter(_chapter: dict[str, Any] | None = None) -> str:
    return "第一卷"


def chapter_memory_summary(chapter: dict[str, Any]) -> str:
    summary = str(chapter.get("summary") or chapter.get("brief") or (chapter.get("draft") or "")[:160] or "暂无摘要")
    return str(trim_text(summary, 260))


def volume_memory_path(_volume_name: str) -> str:
    return BODY_MEMORY_PATH


def rebuild_volume_memory(project_id: str, volume_name: str = "第一卷") -> dict[str, Any]:
    """重建面向 LLM 的全书关键记忆。

    注意：正文全文不塞进这一页，全文单独保存到 chapters/chapter-xxx.md。
    这样上下文可以优先读取摘要和衔接包，需要时再检索全文。
    """
    with connect() as conn:
        chapters = rows_to_dicts(
            conn.execute(
                """
                SELECT id, chapter_number, title, brief, summary, draft, status
                FROM chapters
                WHERE project_id = ? AND status = 'final'
                ORDER BY chapter_number
                """,
                (project_id,),
            ).fetchall()
        )
    lines = [
        "# 关键记忆",
        "",
        "本文件保存章节定稿后的关键事实、状态变化、衔接信息和反重复提示。",
        "正文全文保存在 `chapters/chapter-xxx.md`，章节衔接包保存在 `bridges/chapter-xxx-bridge.md`。",
        "",
    ]
    for chapter in chapters:
        chapter_number = chapter.get("chapter_number") or 0
        title = clean_chapter_title(chapter)
        summary = chapter_memory_summary(chapter)
        change = narrative_focus_from_brief(str(chapter.get("brief") or ""), title)
        if change == f'一份与"{title}"有关的旧档案正在灰塔深处苏醒':
            change = summary
        bridge = get_chapter_bridge(project_id, chapter.get("id", ""))
        bridge_data = _bridge_json(bridge)
        hooks = bridge_data.get("open_hooks", []) or []
        revealed = bridge_data.get("info_revealed", []) or []
        residue = bridge_data.get("emotional_residue", []) or []
        next_seeds = bridge_data.get("next_chapter_seeds", []) or bridge_data.get("next_seeds", []) or []
        tension = bridge_data.get("unresolved_tension", "")

        lines.extend(
            [
                f"## 第 {chapter_number} 章 · {title}",
                f"- 全文页：chapters/{_chapter_slug(chapter)}.md",
                f"- 衔接包：bridges/{_chapter_slug(chapter)}-bridge.md",
                f"- 主要事件：{summary}",
                f"- 关键变化：{change or summary}",
                f"- 已用冲突：{summary}",
                "- 已埋伏笔：见本项目伏笔与时间线记录。",
                f"- 不要重复：不要再次生成 [{summary}] 这一事件、信息揭示或冲突解决方式。",
            ]
        )
        if tension:
            lines.append(f"- 未解张力：{tension}")
        if hooks:
            hook_texts = [h.get("hook", str(h)) if isinstance(h, dict) else str(h) for h in hooks[:3]]
            lines.append(f"- 未决钩子：{'；'.join(hook_texts)}")
        if revealed:
            lines.append(f"- 已揭示：{'；'.join(str(r) for r in revealed[:3])}")
        if residue:
            residue_texts = []
            for item in residue[:3]:
                if isinstance(item, dict):
                    residue_texts.append(f"{item.get('character', '?')}：{item.get('emotion', '')}")
                else:
                    residue_texts.append(str(item))
            lines.append(f"- 情感余波：{'；'.join(residue_texts)}")
        if next_seeds:
            lines.append(f"- 下一章种子：{'；'.join(str(s) for s in next_seeds[:3])}")
        lines.append("")
    return upsert_wiki_page(project_id, volume_memory_path(volume_name), "\n".join(lines).rstrip() + "\n")


# ---------------------------------------------------------------------------
# 章节全文 / 衔接包 / 索引同步
# ---------------------------------------------------------------------------
def chapter_full_wiki_path(chapter: dict[str, Any]) -> str:
    return f"chapters/{_chapter_slug(chapter)}.md"


def chapter_bridge_wiki_path(chapter: dict[str, Any]) -> str:
    return f"bridges/{_chapter_slug(chapter)}-bridge.md"


def chapter_full_markdown(chapter: dict[str, Any], bridge: dict[str, Any] | None = None) -> str:
    chapter_number = chapter.get("chapter_number") or 0
    title = _chapter_title(chapter)
    brief = chapter.get("brief") or ""
    summary = chapter.get("summary") or brief or (chapter.get("draft") or "")[:160]
    draft = chapter.get("draft") or ""
    bridge_data = _bridge_json(bridge)
    hooks = bridge_data.get("open_hooks", []) or []
    residue = bridge_data.get("emotional_residue", []) or []
    next_seeds = bridge_data.get("next_chapter_seeds", []) or bridge_data.get("next_seeds", []) or []
    tension = bridge_data.get("unresolved_tension", "")
    revealed = bridge_data.get("info_revealed", []) or []
    withheld = bridge_data.get("info_withheld", []) or []

    return "\n".join(
        [
            f"# 第 {chapter_number} 章 · {title}",
            "",
            "## llmwiki 元信息",
            "",
            f"- 章节号：{chapter_number}",
            f"- 状态：{chapter.get('status') or 'draft'}",
            f"- 字数：{len(draft)}",
            f"- 章节衔接包：{chapter_bridge_wiki_path(chapter)}",
            "",
            "## 本章摘要",
            "",
            str(summary or "暂无摘要"),
            "",
            "## 本章大纲 / 写作目标",
            "",
            str(brief or "暂无大纲"),
            "",
            "## 章末承接要求",
            "",
            f"- 未解张力：{tension or '无'}",
            "- 未决钩子：",
            _format_list(hooks, key="hook"),
            "- 情感余波：",
            _format_list(residue),
            "- 下一章种子：",
            _format_list(next_seeds),
            "- 已揭示信息：",
            _format_list(revealed),
            "- 暂不揭示信息：",
            _format_list(withheld),
            "",
            "## 正文全文",
            "",
            draft or "暂无正文",
            "",
        ]
    )


def chapter_bridge_markdown(chapter: dict[str, Any], bridge: dict[str, Any] | None) -> str:
    chapter_number = chapter.get("chapter_number") or 0
    title = _chapter_title(chapter)
    bridge_data = _bridge_json(bridge)
    ending = bridge_data.get("ending_state", {}) or {}
    hooks = bridge_data.get("open_hooks", []) or []
    residue = bridge_data.get("emotional_residue", []) or []
    revealed = bridge_data.get("info_revealed", []) or []
    withheld = bridge_data.get("info_withheld", []) or []
    next_seeds = bridge_data.get("next_chapter_seeds", []) or bridge_data.get("next_seeds", []) or []
    tension = bridge_data.get("unresolved_tension", "")

    return "\n".join(
        [
            f"# 第 {chapter_number} 章衔接包 · {title}",
            "",
            "这个页面是下一章生成时必须读取的硬约束，用于防止章节断裂、情绪跳跃和信息重复揭示。",
            "",
            "## 上一章末尾状态",
            "",
            _format_list([ending] if ending else []),
            "",
            "## 下一章必须承接",
            "",
            "1. 开头必须承接上一章末尾的时间、地点、人物状态和最后动作。",
            "2. 人物情绪必须从情感余波起步，不得凭空切换。",
            "3. 至少回应一个未决钩子，不得全部悬置。",
            "4. 不要重复揭示已揭示信息，要在其后果上推进。",
            "",
            "## 未决钩子",
            "",
            _format_list(hooks, key="hook"),
            "",
            "## 情感余波",
            "",
            _format_list(residue),
            "",
            "## 已揭示信息",
            "",
            _format_list(revealed),
            "",
            "## 暂不揭示信息",
            "",
            _format_list(withheld),
            "",
            "## 下一章种子",
            "",
            _format_list(next_seeds),
            "",
            "## 未解张力",
            "",
            tension or "无",
            "",
            "## 原始 JSON",
            "",
            "```json",
            json.dumps(bridge_data, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )


def sync_chapter_full_to_wiki(project_id: str, chapter: dict[str, Any], bridge: dict[str, Any] | None = None) -> dict[str, Any]:
    page = upsert_wiki_page(
        project_id,
        chapter_full_wiki_path(chapter),
        chapter_full_markdown(chapter, bridge),
        chapter.get("id", ""),
    )
    rebuild_chapter_index(project_id)
    return page


def sync_bridge_to_wiki(project_id: str, chapter: dict[str, Any], bridge: dict[str, Any] | None) -> dict[str, Any] | None:
    if not bridge:
        return None
    page = upsert_wiki_page(
        project_id,
        chapter_bridge_wiki_path(chapter),
        chapter_bridge_markdown(chapter, bridge),
        chapter.get("id", ""),
    )
    rebuild_bridge_index(project_id)
    return page


def rebuild_chapter_index(project_id: str) -> dict[str, Any]:
    with connect() as conn:
        chapters = rows_to_dicts(
            conn.execute(
                """
                SELECT id, chapter_number, title, summary, brief, word_count, status, updated_at
                FROM chapters
                WHERE project_id = ?
                ORDER BY chapter_number
                """,
                (project_id,),
            ).fetchall()
        )
    lines = [
        "# 章节全文索引",
        "",
        "所有定稿章节会自动写入 `chapters/chapter-xxx.md`。这一页供 llmwiki 检索和人工检查。",
        "",
    ]
    for chapter in chapters:
        summary = chapter_memory_summary(chapter)
        lines.extend(
            [
                f"## 第 {chapter.get('chapter_number') or 0} 章 · {_chapter_title(chapter)}",
                f"- 全文页：{chapter_full_wiki_path(chapter)}",
                f"- 状态：{chapter.get('status') or 'draft'}",
                f"- 字数：{chapter.get('word_count') or 0}",
                f"- 摘要：{summary}",
                "",
            ]
        )
    return upsert_wiki_page(project_id, CHAPTER_INDEX_PATH, "\n".join(lines).rstrip() + "\n")


def rebuild_bridge_index(project_id: str) -> dict[str, Any]:
    with connect() as conn:
        bridges = rows_to_dicts(
            conn.execute(
                """
                SELECT cb.*, c.title, c.brief, c.summary
                FROM chapter_bridges cb
                LEFT JOIN chapters c ON c.id = cb.chapter_id
                WHERE cb.project_id = ?
                ORDER BY cb.chapter_number
                """,
                (project_id,),
            ).fetchall()
        )
    lines = [
        "# 章节衔接包索引",
        "",
        "每章定稿后生成一个衔接包，下一章生成时必须承接上一章衔接包。",
        "",
    ]
    for bridge in bridges:
        chapter = {
            "chapter_number": bridge.get("chapter_number"),
            "title": bridge.get("title") or f"第 {bridge.get('chapter_number') or 0} 章",
        }
        data = _bridge_json(bridge)
        hooks = data.get("open_hooks", []) or []
        tension = data.get("unresolved_tension", "")
        hook_text = "；".join(h.get("hook", str(h)) if isinstance(h, dict) else str(h) for h in hooks[:3]) or "无"
        lines.extend(
            [
                f"## 第 {bridge.get('chapter_number') or 0} 章 · {_chapter_title(chapter)}",
                f"- 衔接包：{chapter_bridge_wiki_path(chapter)}",
                f"- 未决钩子：{hook_text}",
                f"- 未解张力：{tension or '无'}",
                "",
            ]
        )
    return upsert_wiki_page(project_id, BRIDGE_INDEX_PATH, "\n".join(lines).rstrip() + "\n")


# ---------------------------------------------------------------------------
# 章节定稿后同步
# ---------------------------------------------------------------------------
def sync_chapter_memory_to_wiki(project_id: str, chapter: dict[str, Any]) -> None:
    chapter_number = chapter.get("chapter_number") or 0
    title = _chapter_title(chapter)
    summary = chapter.get("summary") or chapter.get("brief") or (chapter.get("draft") or "")[:120]
    draft = chapter.get("draft") or ""

    create_structured_record(
        project_id,
        "timeline-events",
        f"第 {chapter_number} 章事件",
        "chapter_event",
        summary,
        {
            "event_time": f"第 {chapter_number} 章",
            "chapter": title,
            "characters": "",
            "cause": chapter.get("brief") or "",
            "status": "已定稿",
            "full_text_path": chapter_full_wiki_path(chapter),
            "bridge_path": chapter_bridge_wiki_path(chapter),
        },
        "active",
    )
    if "伏笔" in draft or "埋下" in draft:
        create_structured_record(
            project_id,
            "foreshadowings",
            f"第 {chapter_number} 章伏笔",
            "open",
            "章节定稿时自动提取的伏笔线索。",
            {
                "setup_chapter": title,
                "payoff_chapter": "",
                "status": "未回收",
                "related_characters": "",
                "hint": "章节中出现伏笔或埋线提示。",
                "source_path": chapter_full_wiki_path(chapter),
            },
            "open",
        )


def finalize_chapter_wiki_sync(project_id: str, chapter: dict[str, Any]) -> dict[str, Any]:
    """定稿后的完整 llmwiki 落盘流程。

    顺序很重要：先生成/获取衔接包，再写全文页，因为全文页末尾要附带下一章承接要求。
    """
    bridge = auto_generate_bridge(project_id, chapter)
    sync_chapter_memory_to_wiki(project_id, chapter)
    full_page = sync_chapter_full_to_wiki(project_id, chapter, bridge)
    bridge_page = sync_bridge_to_wiki(project_id, chapter, bridge)
    volume_page = rebuild_volume_memory(project_id, volume_name_for_chapter(chapter))
    write_chapter_snapshot(project_id, chapter)
    return {
        "chapter_page": full_page,
        "bridge_page": bridge_page,
        "volume_page": volume_page,
    }


def write_chapter_snapshot(project_id: str, chapter: dict[str, Any]) -> None:
    root = project_root(project_id)
    path = root / "manuscript" / f"chapter-{int(chapter['chapter_number']):03}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {chapter['title'] or '未命名章节'}\n\n{chapter['draft'] or ''}", encoding="utf-8")


def auto_generate_bridge(project_id: str, chapter: dict[str, Any]) -> dict[str, Any] | None:
    """定稿后自动生成章节衔接包。优先用远程模型，失败用 stub。"""
    chapter_id = chapter.get("id", "")
    chapter_number = int(chapter.get("chapter_number") or 0)
    draft = chapter.get("draft") or ""
    if not draft:
        return None
    existing = get_chapter_bridge(project_id, chapter_id)
    if existing:
        return existing
    with connect() as conn:
        project = row_to_dict(
            conn.execute("SELECT target_chapter_count FROM projects WHERE id = ?", (project_id,)).fetchone()
        ) or {}
    target_count = int(project.get("target_chapter_count") or 0)
    is_final_chapter = bool(target_count and chapter_number >= target_count)
    bridge_payload = AiWorkflowIn(chapter_id=chapter_id, content=draft, prompt="生成章节衔接包")
    bridge_context = {
        "chapter": chapter,
        "characters": list_records_for_context(project_id, "character-profiles"),
        "generation_contract": {
            "target_chapter_count": target_count,
            "is_final_chapter": is_final_chapter,
            "ending_required": is_final_chapter,
        },
    }
    config = resolve_model_config(project_id, "generate_chapter_bridge")
    bridge_data: dict[str, Any] | None = None
    if config:
        output = run_model_or_stub(project_id, "generate_chapter_bridge", bridge_payload, bridge_context)
        structured = output.get("structured")
        if isinstance(structured, dict) and structured.get("ending_state"):
            bridge_data = structured
    if not bridge_data:
        bridge_data = structured_output_for_workflow("generate_chapter_bridge", bridge_payload, bridge_context)
    if not isinstance(bridge_data, dict) or not bridge_data.get("ending_state"):
        return None
    bridge_data.pop("_chapter_id", None)
    bridge_data.pop("_chapter_number", None)
    return create_chapter_bridge(project_id, chapter_id, chapter_number, bridge_data)


# ---------------------------------------------------------------------------
# wiki 页面 CRUD
# ---------------------------------------------------------------------------
def upsert_wiki_page(project_id: str, relative_path: str, content: str, source_chapter_id: str = "") -> dict[str, Any]:
    target = safe_wiki_path(project_id, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    old_content = target.read_text(encoding="utf-8") if target.exists() else ""
    target.write_text(content, encoding="utf-8")
    title = relative_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    now = utc_now()
    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM wiki_pages WHERE project_id = ? AND path = ?",
            (project_id, relative_path),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE wiki_pages SET title = ?, content = ?, source_chapter_id = ?, updated_at = ? WHERE project_id = ? AND path = ?",
                (title, content, source_chapter_id, now, project_id, relative_path),
            )
        else:
            conn.execute(
                """
                INSERT INTO wiki_pages (id, project_id, path, title, content, source_chapter_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (new_id(), project_id, relative_path, title, content, source_chapter_id, now, now),
            )
        conn.execute(
            """
            INSERT INTO wiki_page_revisions (id, project_id, path, content, source_chapter_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (new_id(), project_id, relative_path, old_content, source_chapter_id, now),
        )
        page = row_to_dict(
            conn.execute(
                "SELECT * FROM wiki_pages WHERE project_id = ? AND path = ?",
                (project_id, relative_path),
            ).fetchone()
        )
    return page


def append_wiki_page(project_id: str, relative_path: str, content: str, source_chapter_id: str = "") -> dict[str, Any]:
    target = safe_wiki_path(project_id, relative_path)
    if not target.exists():
        return upsert_wiki_page(project_id, relative_path, content, source_chapter_id)
    old_content = target.read_text(encoding="utf-8")
    new_content = old_content.rstrip() + "\n\n" + content
    return upsert_wiki_page(project_id, relative_path, new_content, source_chapter_id)


def delete_wiki_page(project_id: str, relative_path: str) -> None:
    target = safe_wiki_path(project_id, relative_path)
    if target.exists():
        target.unlink()
    with connect() as conn:
        conn.execute("DELETE FROM wiki_pages WHERE project_id = ? AND path = ?", (project_id, relative_path))


# ---------------------------------------------------------------------------
# 结构化记录 + wiki 同步
# ---------------------------------------------------------------------------
def safe_wiki_filename(value: str, fallback: str) -> str:
    cleaned = "".join(c for c in value if c.isalnum() or c in "-_./ ")
    cleaned = cleaned.strip().replace(" ", "-")
    return cleaned or fallback


def record_payload(record: dict[str, Any]) -> dict[str, Any]:
    payload = record.get("payload")
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {}
    if isinstance(payload, dict):
        return payload
    return {}


def markdown_for_record(resource: str, record: dict[str, Any]) -> str:
    title = record.get("title") or "未命名记录"
    payload = record_payload(record)
    lines = [f"# {title}", ""]
    if resource == "character-profiles":
        for key in [
            "name", "role", "faction", "appearance", "traits", "desire", "fear",
            "mainline_relation", "arc", "voice", "function", "emotional_wound",
            "emotional_need", "memory_role", "related_chapters", "notes",
        ]:
            if payload.get(key):
                lines.append(f"- {key}：{payload[key]}")
    elif resource == "character-relationships":
        for key in [
            "name", "from", "to", "source_character", "target_character", "type",
            "relationship_type", "relation", "strength", "conflict", "description",
            "change_history", "related_chapters", "notes",
        ]:
            if payload.get(key):
                lines.append(f"- {key}：{payload[key]}")
    elif resource == "outlines":
        for key in [
            "volume", "chapter_number", "chapter_goal", "main_conflict", "key_events",
            "emotional_rhythm", "foreshadowing", "hook", "related_characters", "completion_status",
        ]:
            if payload.get(key):
                lines.append(f"- {key}：{payload[key]}")
        content_text = record.get("content") or payload.get("content")
        if content_text:
            lines.append(f"- 大纲：{content_text}")
    elif resource == "timeline-events":
        for key in ["event_time", "chapter", "characters", "cause", "status", "full_text_path", "bridge_path"]:
            if payload.get(key):
                lines.append(f"- {key}：{payload[key]}")
    elif resource == "foreshadowings":
        for key in ["setup_chapter", "payoff_chapter", "status", "related_characters", "hint", "source_path"]:
            if payload.get(key):
                lines.append(f"- {key}：{payload[key]}")
    else:
        content = record.get("content") or ""
        if content:
            lines.append(content)
    return "\n".join(lines)


def aggregate_markdown(project_id: str, resource: str, heading: str) -> str:
    records = list_records_for_context(project_id, resource, 500)
    if not records:
        return ""
    parts = [f"# {heading}", ""]
    for record in records:
        parts.append(markdown_for_record(resource, record))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def aggregate_outline_markdown(project_id: str) -> str:
    records = list_records_for_context(project_id, "outlines", 1000)
    if not records:
        return ""
    by_chapter: dict[str, dict[str, Any]] = {}
    no_chapter: list[dict[str, Any]] = []
    for record in records:
        cn = str(record_payload(record).get("chapter_number") or "")
        if cn:
            if cn not in by_chapter or str(record.get("updated_at") or "") > str(by_chapter[cn].get("updated_at") or ""):
                by_chapter[cn] = record
        else:
            no_chapter.append(record)
    ordered = sorted(by_chapter.values(), key=lambda r: _positive_int(record_payload(r).get("chapter_number")))
    ordered.extend(no_chapter)
    parts = ["# 总纲", ""]
    for record in ordered:
        parts.append(markdown_for_record("outlines", record))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def sync_record_to_wiki(project_id: str, resource: str, record: dict[str, Any]) -> None:
    resource_map = {
        "character-profiles": ("角色档案", "characters", "characters.md"),
        "character-relationships": ("角色关系", "relationships", "relationships.md"),
        "outlines": ("总纲", "outlines", "outline.md"),
        "timeline-events": ("时间线", "timeline", "timeline.md"),
        "foreshadowings": ("伏笔", "foreshadowings", "foreshadowing.md"),
        "taboo-rules": ("雷点", "taboo", "taboo.md"),
        "knowledge-documents": ("知识库", "knowledge", "knowledge.md"),
        "style-profiles": ("风格", "style", "style.md"),
        "prompt-templates": ("Prompt Skills", "skills", "skills.md"),
    }
    if resource not in resource_map:
        return
    heading, subdir, filename = resource_map[resource]

    if resource != "outlines":
        title = record.get("title") or "未命名"
        safe_name = safe_wiki_filename(title, "record")
        per_record_path = f"{subdir}/{safe_name}.md"
        per_record_content = markdown_for_record(resource, record)
        upsert_wiki_page(project_id, per_record_path, per_record_content, record.get("id", ""))

    if resource == "outlines":
        content = aggregate_outline_markdown(project_id)
    else:
        content = aggregate_markdown(project_id, resource, heading)
    upsert_wiki_page(project_id, filename, content)


def delete_record_from_wiki(project_id: str, resource: str, record: dict[str, Any]) -> None:
    resource_map = {
        "character-profiles": "characters",
        "character-relationships": "relationships",
        "outlines": "outlines",
        "timeline-events": "timeline",
        "foreshadowings": "foreshadowings",
        "taboo-rules": "taboo",
        "knowledge-documents": "knowledge",
        "style-profiles": "style",
        "prompt-templates": "skills",
    }
    subdir = resource_map.get(resource)
    if subdir:
        title = record.get("title") or "未命名"
        safe_name = safe_wiki_filename(title, "record")
        try:
            per_record_path = f"{subdir}/{safe_name}.md"
            target = safe_wiki_path(project_id, per_record_path)
            if target.exists():
                target.unlink()
        except Exception:
            pass
    sync_record_to_wiki(project_id, resource, record)


def list_records_for_context(project_id: str, resource: str, limit: int = 20) -> list[dict[str, Any]]:
    table = table_for_resource(resource)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                f"SELECT * FROM {table} WHERE project_id = ? ORDER BY updated_at DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
        )


def table_for_resource(resource: str) -> str:
    from ..infrastructure.database import GENERIC_TABLES
    table = GENERIC_TABLES.get(resource)
    if not table:
        raise HTTPException(status_code=404, detail=f"Unknown resource: {resource}")
    return table


def create_structured_record(
    project_id: str,
    resource: str,
    title: str,
    category: str,
    content: str,
    payload: dict[str, Any],
    status: str = "active",
) -> dict[str, Any]:
    table = table_for_resource(resource)
    now = utc_now()
    record_id = new_id()
    with connect() as conn:
        conn.execute(
            f"""
            INSERT INTO {table} (id, project_id, title, category, content, payload, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (record_id, project_id, title, category, content, json.dumps(payload, ensure_ascii=False), status, now, now),
        )
        record = row_to_dict(conn.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,)).fetchone())
    sync_record_to_wiki(project_id, resource, record)
    return record
