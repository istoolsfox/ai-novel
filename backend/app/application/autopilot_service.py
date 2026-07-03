"""Application: one-click hosted generation preparation.

This service turns a bare project into a runnable hosted generation job by
creating the minimum story bible, chapter outlines, blueprint, and job params.
It does not replace richer manual editing; it gives the autonomous path a
complete starting sequence.
"""
from typing import Any

from ..infrastructure.storage import require_project
from ..workflows.blueprint_generator import generate_blueprint
from .blueprint_service import approve_blueprint, create_project_blueprint, list_project_blueprints
from .job_service import start_generation_job
from .memory_service import create_structured_record, list_records_for_context


def start_autopilot_generation_job(
    project_id: str,
    start_chapter: int = 1,
    target_count: int | None = None,
    generation_mode: str = "fast",
    checkpoint_strategy: str = "none",
    auto_finalize: bool = True,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Prepare story assets and start a hosted generation job."""
    project = require_project(project_id)
    count = _positive_int(target_count) or _positive_int(project.get("target_chapter_count")) or 15

    _ensure_character_profile(project_id, project)
    _ensure_chapter_outlines(project_id, project, start_chapter, count)
    _ensure_taboo_rules(project_id)
    blueprint = _ensure_active_blueprint(project_id, project, start_chapter, count)

    job_params = {
        "hosting_mode": "pure",
        "generation_mode": generation_mode,
        "smart_stop_policy": "warn",
    }
    job_params.update(params or {})
    job = start_generation_job(
        project_id=project_id,
        blueprint_id=blueprint["id"],
        start_chapter=start_chapter,
        target_count=count,
        checkpoint_strategy=checkpoint_strategy,
        auto_finalize=auto_finalize,
        params=job_params,
    )
    return {
        "job": job,
        "blueprint": blueprint,
        "prepared": {
            "characters": len(list_records_for_context(project_id, "character-profiles", 100)),
            "outlines": len(list_records_for_context(project_id, "outlines", 300)),
            "taboo_rules": len(list_records_for_context(project_id, "taboo-rules", 100)),
        },
    }


def _positive_int(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0


def _ensure_character_profile(project_id: str, project: dict[str, Any]) -> None:
    if list_records_for_context(project_id, "character-profiles", 1):
        return
    protagonist = "顾栖月" if "记忆" in (project.get("topic") or project.get("synopsis") or "") else "主角"
    create_structured_record(
        project_id=project_id,
        resource="character-profiles",
        title=protagonist,
        category="主角",
        content=(
            f"{protagonist}是《{project.get('title') or '未命名'}》的主角。"
            "她必须在核心谜题和个人代价之间做出选择。"
        ),
        payload={
            "name": protagonist,
            "role": "主角",
            "desire": project.get("logline") or project.get("topic") or "完成主线目标",
            "fear": "在推进真相时失去重要之物",
            "arc": "从被动卷入到主动承担代价，并在终章完成选择。",
        },
        status="active",
    )


def _ensure_chapter_outlines(project_id: str, project: dict[str, Any], start_chapter: int, count: int) -> None:
    existing = list_records_for_context(project_id, "outlines", 500)
    existing_numbers = {
        str((record.get("payload") or {}).get("chapter_number"))
        for record in existing
        if isinstance(record.get("payload"), dict)
    }
    end_chapter = start_chapter + count - 1
    for chapter_number in range(start_chapter, end_chapter + 1):
        if str(chapter_number) in existing_numbers:
            continue
        is_final = chapter_number == end_chapter
        if chapter_number == start_chapter:
            goal = "建立主角目标、核心异常和第一枚会在终章回收的伏笔。"
        elif is_final:
            goal = "回收主要伏笔，结算核心冲突和情感选择，给出明确结尾。"
        else:
            goal = f"推进第 {chapter_number} 章独有线索，制造新后果，但避免重复前章事件。"
        create_structured_record(
            project_id=project_id,
            resource="outlines",
            title=f"第 {chapter_number} 章大纲",
            category="chapter_outline",
            content=goal,
            payload={
                "chapter_number": str(chapter_number),
                "chapter_title": f"第 {chapter_number} 章",
                "chapter_goal": goal,
                "main_conflict": "主角必须推进真相，同时承担代价。" if not is_final else "主角必须做出最终选择。",
                "key_events": goal,
                "hook": "下一章继续偿还本章后果。" if not is_final else "故事在主要冲突完成后收束。",
                "completion_status": "draft",
            },
            status="active",
        )


def _ensure_taboo_rules(project_id: str) -> None:
    if list_records_for_context(project_id, "taboo-rules", 1):
        return
    for title, content in [
        ("避免现实政治立场对立", "不要挑起现实政治立场、地域、群体身份之间的对立。"),
        ("禁止烂尾式结局", "终章必须回收主线冲突，不得只抛出下一章钩子或写成未完待续。"),
    ]:
        create_structured_record(
            project_id=project_id,
            resource="taboo-rules",
            title=title,
            category="全书",
            content=content,
            payload={"severity": "high", "scope": "全书"},
            status="active",
        )


def _ensure_active_blueprint(project_id: str, project: dict[str, Any], start_chapter: int, count: int) -> dict[str, Any]:
    blueprints = list_project_blueprints(project_id)
    usable = next((bp for bp in blueprints if bp.get("status") in {"active", "approved"}), None)
    if usable:
        return usable

    blueprint_data = generate_blueprint(project_id, 1, project)
    blueprint_data["chapter_range"] = {"start": start_chapter, "end": start_chapter + count - 1}
    generation_params = blueprint_data.get("generation_params")
    if not isinstance(generation_params, dict):
        generation_params = {}
    generation_params.setdefault("words_per_chapter", _positive_int(project.get("target_words_per_chapter")) or 3000)
    generation_params["ending_required"] = True
    generation_params.setdefault("word_count_tolerance", 1.0)
    blueprint_data["generation_params"] = generation_params
    blueprint = create_project_blueprint(project_id, blueprint_data)
    return approve_blueprint(project_id, blueprint["id"])
