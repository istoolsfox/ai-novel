"""应用层 · 卷记忆与章节快照管理。

从 main.py 迁出，负责：
- 卷记忆重建（rebuild_volume_memory）
- 章节定稿后同步到 wiki（sync_chapter_memory_to_wiki）
- 章节快照写入文件系统（write_chapter_snapshot）
- 章节衔接包自动生成（_auto_generate_bridge）
- wiki 页面 CRUD（upsert/append/delete + revisions）
- 结构化记录创建 + wiki 同步
"""
import json
from pathlib import Path
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
from ..infrastructure.storage import project_root, require_project, safe_wiki_path
from .context_builder import trim_text
from ..workflows.generation import (
    clean_chapter_title,
    narrative_focus_from_brief,
    structured_output_for_workflow,
)
from ..workflows.llm_client import resolve_model_config, run_model_or_stub

BODY_MEMORY_PATH = "关键记忆.md"


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
        "本文件保存章节定稿后的关键事实、状态变化、衔接信息和反重复提示；正文全文保存在章节草稿与导出文件中。",
        "",
    ]
    for chapter in chapters:
        chapter_number = chapter.get("chapter_number") or 0
        title = clean_chapter_title(chapter)
        summary = chapter_memory_summary(chapter)
        change = narrative_focus_from_brief(str(chapter.get("brief") or ""), title)
        if change == f'一份与"{title}"有关的旧档案正在灰塔深处苏醒':
            change = summary
        # 查询该章的衔接包
        bridge = get_chapter_bridge(project_id, chapter.get("id", ""))
        bridge_lines = []
        if bridge:
            bridge_json = bridge.get("bridge_json")
            if isinstance(bridge_json, str):
                try:
                    bridge_json = json.loads(bridge_json)
                except json.JSONDecodeError:
                    bridge_json = {}
            if isinstance(bridge_json, dict):
                hooks = bridge_json.get("open_hooks", []) or []
                revealed = bridge_json.get("info_revealed", []) or []
                tension = bridge_json.get("unresolved_tension", "")
                if tension:
                    bridge_lines.append(f"- 未解张力：{tension}")
                if hooks:
                    hook_texts = [h.get("hook", str(h)) if isinstance(h, dict) else str(h) for h in hooks[:3]]
                    bridge_lines.append(f"- 未决钩子：{'；'.join(hook_texts)}")
                if revealed:
                    bridge_lines.append(f"- 已揭示：{'；'.join(str(r) for r in revealed[:3])}")
        lines.extend(
            [
                f"## 第 {chapter_number} 章 · {title}",
                f"- 主要事件：{summary}",
                f"- 关键变化：{change or summary}",
                f"- 已用冲突：{summary}",
                "- 已埋伏笔：见本项目伏笔与时间线记录。",
                f"- 不要重复：不要再次生成 [{summary}] 这一事件、信息揭示或冲突解决方式。",
            ]
        )
        lines.extend(bridge_lines)
        lines.append("")
    return upsert_wiki_page(project_id, volume_memory_path(volume_name), "\n".join(lines).rstrip() + "\n")


# ---------------------------------------------------------------------------
# 章节定稿后同步
# ---------------------------------------------------------------------------
def sync_chapter_memory_to_wiki(project_id: str, chapter: dict[str, Any]) -> None:
    chapter_number = chapter.get("chapter_number") or 0
    title = chapter.get("title") or f"第 {chapter_number} 章"
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
            },
            "open",
        )


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
    bridge_payload = AiWorkflowIn(chapter_id=chapter_id, content=draft, prompt="生成章节衔接包")
    bridge_context = {"chapter": chapter, "characters": list_records_for_context(project_id, "character-profiles")}
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
        # 查数据库判断是否存在（文件可能已存在但 db 行不一定）
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
        for key in ["name", "role", "faction", "appearance", "traits", "desire", "fear", "mainline_relation", "arc", "voice", "related_chapters", "notes"]:
            if payload.get(key):
                lines.append(f"- {key}：{payload[key]}")
    elif resource == "character-relationships":
        for key in ["name", "from", "to", "type", "relation", "conflict", "description", "notes"]:
            if payload.get(key):
                lines.append(f"- {key}：{payload[key]}")
    elif resource == "outlines":
        # outlines 的 title 就是章节标题，不再重复输出 chapter_title
        for key in ["volume", "chapter_number", "chapter_goal", "main_conflict", "key_events", "emotional_rhythm", "foreshadowing", "hook", "related_characters", "completion_status"]:
            if payload.get(key):
                lines.append(f"- {key}：{payload[key]}")
        content_text = record.get("content") or payload.get("content")
        if content_text:
            lines.append(f"- 大纲：{content_text}")
    elif resource == "timeline-events":
        for key in ["event_time", "chapter", "characters", "cause", "status"]:
            if payload.get(key):
                lines.append(f"- {key}：{payload[key]}")
    elif resource == "foreshadowings":
        for key in ["setup_chapter", "payoff_chapter", "status", "related_characters", "hint"]:
            if payload.get(key):
                lines.append(f"- {key}：{payload[key]}")
    else:
        content = record.get("content") or ""
        if content:
            lines.append(content)
    return "\n".join(lines)


def aggregate_markdown(project_id: str, resource: str, heading: str) -> str:
    records = list_records_for_context(project_id, resource)
    if not records:
        return ""
    parts = [f"# {heading}", ""]
    for record in records:
        parts.append(markdown_for_record(resource, record))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def outline_record_key(record: dict[str, Any]) -> str:
    payload = record_payload(record)
    chapter_number = payload.get("chapter_number") or record.get("chapter_number")
    title = payload.get("chapter_title") or record.get("title") or "未命名章节"
    return f"{chapter_number}-{title}" if chapter_number else title


def aggregate_outline_markdown(project_id: str) -> str:
    records = list_records_for_context(project_id, "outlines")
    if not records:
        return ""
    # 按 chapter_number 去重：同章节号只保留最新（updated_at 最大）的一条
    by_chapter: dict[str, dict[str, Any]] = {}
    no_chapter: list[dict[str, Any]] = []
    for record in records:
        cn = str(record_payload(record).get("chapter_number") or "")
        if cn:
            # 保留 updated_at 最大的
            if cn not in by_chapter or str(record.get("updated_at") or "") > str(by_chapter[cn].get("updated_at") or ""):
                by_chapter[cn] = record
        else:
            no_chapter.append(record)
    ordered = sorted(by_chapter.values(), key=lambda r: str(record_payload(r).get("chapter_number") or 0))
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
    }
    if resource not in resource_map:
        return
    heading, subdir, filename = resource_map[resource]

    # 1. 单条记录的 wiki 页（按标题命名，放在子目录）
    #    注意：outlines 只用聚合页（outline.md），不建 per-record 页
    if resource != "outlines":
        title = record.get("title") or "未命名"
        safe_name = safe_wiki_filename(title, "record")
        per_record_path = f"{subdir}/{safe_name}.md"
        per_record_content = markdown_for_record(resource, record)
        upsert_wiki_page(project_id, per_record_path, per_record_content, record.get("id", ""))

    # 2. 聚合 wiki 页（所有记录汇总）
    if resource == "outlines":
        content = aggregate_outline_markdown(project_id)
    else:
        content = aggregate_markdown(project_id, resource, heading)
    upsert_wiki_page(project_id, filename, content)


def delete_record_from_wiki(project_id: str, resource: str, record: dict[str, Any]) -> None:
    # 删除单条记录的 wiki 页
    resource_map = {
        "character-profiles": "characters",
        "character-relationships": "relationships",
        "outlines": "outlines",
        "timeline-events": "timeline",
        "foreshadowings": "foreshadowings",
        "taboo-rules": "taboo",
        "knowledge-documents": "knowledge",
        "style-profiles": "style",
    }
    subdir = resource_map.get(resource)
    if subdir:
        title = record.get("title") or "未命名"
        safe_name = safe_wiki_filename(title, "record")
        try:
            from ..infrastructure.storage import safe_wiki_path
            per_record_path = f"{subdir}/{safe_name}.md"
            target = safe_wiki_path(project_id, per_record_path)
            if target.exists():
                target.unlink()
        except Exception:
            pass
    # 重建聚合页
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
