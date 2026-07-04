"""Application: one-click hosted generation preparation.

This service turns a bare project into a runnable hosted generation job by
preparing a connected story asset chain before starting the generation thread:

outline -> characters -> relationships -> relationship canvas -> emotional
constraints -> llmwiki memory -> chapter generation.
"""
from typing import Any

from ..infrastructure.storage import require_project
from ..workflows.blueprint_generator import generate_blueprint
from .blueprint_service import approve_blueprint, create_project_blueprint, list_project_blueprints
from .job_service import start_generation_job
from .memory_service import list_records_for_context
from .story_asset_service import prepare_autopilot_story_assets


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
    start_chapter = _positive_int(start_chapter) or 1

    prepared_assets = prepare_autopilot_story_assets(project_id, project, start_chapter, count)
    blueprint = _ensure_active_blueprint(project_id, project, start_chapter, count)

    job_params = {
        "hosting_mode": "pure",
        "generation_mode": generation_mode,
        "smart_stop_policy": "warn",
        "auto_prepare_assets": True,
        "memory_mode": "llmwiki",
        "relationship_canvas": "relationships/canvas.md",
        "chapter_memory_policy": "full_chapter_and_bridge",
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
            "relationships": len(list_records_for_context(project_id, "character-relationships", 100)),
            "outlines": len(list_records_for_context(project_id, "outlines", 500)),
            "taboo_rules": len(list_records_for_context(project_id, "taboo-rules", 100)),
            "prompt_skills": len(list_records_for_context(project_id, "prompt-templates", 100)),
            "assets": prepared_assets,
        },
    }


def _positive_int(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0


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
    generation_params["memory_mode"] = "llmwiki"
    generation_params["relationship_canvas"] = "relationships/canvas.md"
    generation_params["chapter_bridge_required"] = True
    generation_params.setdefault("word_count_tolerance", 1.0)
    blueprint_data["generation_params"] = generation_params
    blueprint = create_project_blueprint(project_id, blueprint_data)
    return approve_blueprint(project_id, blueprint["id"])
