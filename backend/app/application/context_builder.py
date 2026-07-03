"""应用层 · 上下文装配与压缩。

从 main.py 迁出，包含：
- build_generation_context：装配生成上下文（章节/卷记忆/角色/大纲/伏笔/情感种子/衔接包）
- trim_text / compact_value / compact_record 等压缩工具
- compact_payload_for_remote / max_tokens_for_config / request_timeout_for_workflow
"""
import json
import os
from typing import Any

from ..domain.models import AiWorkflowIn
from ..infrastructure.database import (
    connect,
    get_emotion_seed,
    get_previous_chapter_bridge,
    row_to_dict,
    rows_to_dicts,
)
from ..infrastructure.storage import require_project


# ---------------------------------------------------------------------------
# 生成上下文装配
# ---------------------------------------------------------------------------
def build_generation_context(project_id: str, chapter_id: str = "") -> dict[str, Any]:
    """装配 LLM 生成上下文。"""
    from .memory_service import (
        list_records_for_context,
        rebuild_volume_memory,
        volume_memory_path,
        volume_name_for_chapter,
    )
    from ..interfaces.dependencies import require_chapter

    chapter = require_chapter(project_id, chapter_id) if chapter_id else None
    volume_name = volume_name_for_chapter(chapter)
    volume_path = volume_memory_path(volume_name)
    with connect() as conn:
        if chapter:
            recent_chapters = rows_to_dicts(
                conn.execute(
                    """
                    SELECT id, chapter_number, title, brief, summary
                    FROM chapters
                    WHERE project_id = ? AND chapter_number < ?
                    ORDER BY chapter_number DESC
                    LIMIT 3
                    """,
                    (project_id, chapter.get("chapter_number") or 0),
                ).fetchall()
            )
        else:
            recent_chapters = rows_to_dicts(
                conn.execute(
                    """
                    SELECT id, chapter_number, title, brief, summary
                    FROM chapters
                    WHERE project_id = ?
                    ORDER BY chapter_number DESC
                    LIMIT 3
                    """,
                    (project_id,),
                ).fetchall()
            )
        wiki_pages = rows_to_dicts(
            conn.execute(
                "SELECT path, title, content FROM wiki_pages WHERE project_id = ? ORDER BY updated_at DESC LIMIT 12",
                (project_id,),
            ).fetchall()
        )
        volume_memory = row_to_dict(
            conn.execute(
                "SELECT path, title, content FROM wiki_pages WHERE project_id = ? AND path = ?",
                (project_id, volume_path),
            ).fetchone()
        )
    if not volume_memory:
        volume_memory = rebuild_volume_memory(project_id, volume_name)
    # 情感深度增强 v2：查询当前章节的情感种子
    emotion_seed = None
    if chapter_id:
        emotion_seed = get_emotion_seed(project_id, chapter_id)
    # 章节衔接包：查询上一章的衔接包（用于本章承接）
    prev_bridge = None
    if chapter:
        chapter_number = int(chapter.get("chapter_number") or 0)
        if chapter_number > 1:
            prev_bridge = get_previous_chapter_bridge(project_id, chapter_number)
    return {
        "chapter": chapter,
        "recent_chapters": recent_chapters,
        "volume_memory": volume_memory,
        "anti_repetition_notes": (
            f"生成新大纲或正文前必须读取 {volume_path}，避免重复本卷已发生事件、信息揭示、冲突解决方式和伏笔呈现。"
            if volume_memory
            else f"当前尚无 {volume_path}；定稿章节后会重建本卷记忆。"
        ),
        "characters": list_records_for_context(project_id, "character-profiles"),
        "relationships": list_records_for_context(project_id, "character-relationships"),
        "outlines": list_records_for_context(project_id, "outlines"),
        "styles": list_records_for_context(project_id, "style-profiles"),
        "timeline": list_records_for_context(project_id, "timeline-events"),
        "foreshadowings": list_records_for_context(project_id, "foreshadowings"),
        "taboo_rules": list_records_for_context(project_id, "taboo-rules"),
        "knowledge": list_records_for_context(project_id, "knowledge-documents"),
        "wiki_pages": wiki_pages,
        "emotion_seed": emotion_seed,
        "prev_chapter_bridge": prev_bridge,
    }


def trim_text(value: Any, max_chars: int = 1200) -> Any:
    if not isinstance(value, str):
        return value
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + f"\n...[已截断 {len(value) - max_chars} 字]"


def compact_value(value: Any, max_string_chars: int = 1000, max_items: int = 12, depth: int = 0) -> Any:
    if isinstance(value, str):
        return trim_text(value, max_string_chars)
    if isinstance(value, list):
        return [compact_value(item, max_string_chars, max_items, depth + 1) for item in value[:max_items]]
    if isinstance(value, dict):
        if depth >= 4:
            return trim_text(json.dumps(value, ensure_ascii=False), max_string_chars)
        return {
            key: compact_value(item, max_string_chars, max_items, depth + 1)
            for key, item in value.items()
            if key not in {"api_key", "generation_context"}
        }
    return value


def compact_record(record: dict[str, Any], content_limit: int = 700) -> dict[str, Any]:
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    return {
        "id": record.get("id", ""),
        "title": record.get("title", ""),
        "category": record.get("category", ""),
        "status": record.get("status", ""),
        "content": trim_text(record.get("content", ""), content_limit),
        "payload": compact_value(payload, 420, 10),
    }


def compact_chapter_for_prompt(chapter: dict[str, Any] | None) -> dict[str, Any] | None:
    if not chapter:
        return None
    return {
        "id": chapter.get("id", ""),
        "chapter_number": chapter.get("chapter_number", 0),
        "title": chapter.get("title", ""),
        "brief": trim_text(chapter.get("brief", ""), 900),
        "summary": trim_text(chapter.get("summary", ""), 900),
        "status": chapter.get("status", ""),
        "draft_excerpt": trim_text(chapter.get("draft", ""), 2200),
    }


def compact_generation_context(context: dict[str, Any]) -> dict[str, Any]:
    # 情感种子压缩
    emotion_seed = context.get("emotion_seed")
    compact_seed = None
    if isinstance(emotion_seed, dict):
        seed_data = emotion_seed.get("emotion_seed", emotion_seed)
        if isinstance(seed_data, dict):
            compact_seed = {
                "core_tension": trim_text(seed_data.get("core_tension", ""), 200),
                "scene_temperature": trim_text(seed_data.get("scene_temperature", ""), 200),
                "open_question": trim_text(seed_data.get("open_question", ""), 200),
            }

    # 上一章衔接包压缩
    prev_bridge = context.get("prev_chapter_bridge")
    compact_bridge = None
    if isinstance(prev_bridge, dict):
        bridge_json = prev_bridge.get("bridge_json")
        if isinstance(bridge_json, str):
            try:
                bridge_json = json.loads(bridge_json)
            except json.JSONDecodeError:
                bridge_json = {}
        if isinstance(bridge_json, dict):
            compact_bridge = {
                "chapter_number": prev_bridge.get("chapter_number", 0),
                "ending_state": bridge_json.get("ending_state", {}),
                "open_hooks": (bridge_json.get("open_hooks", []) or [])[:5],
                "emotional_residue": (bridge_json.get("emotional_residue", []) or [])[:5],
                "info_revealed": (bridge_json.get("info_revealed", []) or [])[:8],
                "info_withheld": (bridge_json.get("info_withheld", []) or [])[:5],
                "next_chapter_seeds": (bridge_json.get("next_chapter_seeds", []) or [])[:5],
                "unresolved_tension": trim_text(bridge_json.get("unresolved_tension", ""), 200),
            }

    return {
        "chapter": compact_chapter_for_prompt(context.get("chapter")),
        "volume_memory": (
            {
                "path": context["volume_memory"].get("path", ""),
                "title": context["volume_memory"].get("title", ""),
                "content": trim_text(context["volume_memory"].get("content", ""), 2600),
            }
            if isinstance(context.get("volume_memory"), dict)
            else None
        ),
        "anti_repetition_notes": trim_text(context.get("anti_repetition_notes", ""), 1000),
        "recent_chapters": [
            {
                "id": chapter.get("id", ""),
                "chapter_number": chapter.get("chapter_number", 0),
                "title": chapter.get("title", ""),
                "brief": trim_text(chapter.get("brief", ""), 500),
                "summary": trim_text(chapter.get("summary", ""), 700),
            }
            for chapter in (context.get("recent_chapters") or [])[:3]
            if isinstance(chapter, dict)
        ],
        "characters": [compact_record(record, 600) for record in (context.get("characters") or [])[:12] if isinstance(record, dict)],
        "relationships": [compact_record(record, 500) for record in (context.get("relationships") or [])[:16] if isinstance(record, dict)],
        "outlines": [compact_record(record, 900) for record in (context.get("outlines") or [])[:12] if isinstance(record, dict)],
        "styles": [compact_record(record, 900) for record in (context.get("styles") or [])[:6] if isinstance(record, dict)],
        "timeline": [compact_record(record, 500) for record in (context.get("timeline") or [])[:16] if isinstance(record, dict)],
        "foreshadowings": [compact_record(record, 500) for record in (context.get("foreshadowings") or [])[:16] if isinstance(record, dict)],
        "taboo_rules": [compact_record(record, 500) for record in (context.get("taboo_rules") or [])[:16] if isinstance(record, dict)],
        "knowledge": [compact_record(record, 700) for record in (context.get("knowledge") or [])[:8] if isinstance(record, dict)],
        "wiki_pages": [
            {
                "path": page.get("path", ""),
                "title": page.get("title", ""),
                "content": trim_text(page.get("content", ""), 1000),
            }
            for page in (context.get("wiki_pages") or [])[:8]
            if isinstance(page, dict)
        ],
        "emotion_seed": compact_seed,
        "prev_chapter_bridge": compact_bridge,
    }


def compact_payload_for_remote(workflow: str, payload: AiWorkflowIn) -> dict[str, Any]:
    data = payload.model_dump()
    data.pop("generation_context", None)
    if workflow in {"generate_chapter_draft", "revise_selection"}:
        data["current_draft"] = trim_text(data.get("current_draft", ""), 3500)
        data["selected_text"] = trim_text(data.get("selected_text", ""), 2500)
        data["prompt"] = trim_text(data.get("prompt", ""), 1600)
        if isinstance(data.get("style_profile"), dict):
            data["style_profile"] = compact_record(data["style_profile"], 800)
        if isinstance(data.get("style_profiles"), list):
            data["style_profiles"] = [
                {"id": item.get("id", ""), "title": item.get("title", "")}
                for item in data["style_profiles"][:8]
                if isinstance(item, dict)
            ]
    return compact_value(data, 1400, 12)


def max_tokens_for_config(config_payload: dict[str, Any]) -> int:
    try:
        value = int(config_payload.get("max_tokens") or 4000)
    except (TypeError, ValueError):
        value = 4000
    return max(128, min(value, 32000))


def request_timeout_for_workflow(workflow: str) -> int:
    generation_workflows = {
        "generate_chapter_draft",
        "generate_chapter_brief",
        "generate_outline",
        "revise_selection",
    }
    env_key = "AI_NOVEL_GENERATION_TIMEOUT_SECONDS" if workflow in generation_workflows else "AI_NOVEL_MODEL_TIMEOUT_SECONDS"
    default_timeout = 600 if workflow in generation_workflows else 90
    try:
        value = int(os.getenv(env_key) or default_timeout)
    except ValueError:
        value = default_timeout
    return max(30, min(value, 1800))
