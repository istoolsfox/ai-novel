"""Application: job service.

Use cases for generation jobs: start / pause / resume / abort.
Includes concurrency control (one active job per project).
"""
from typing import Any

from fastapi import HTTPException

from ..infrastructure.database import (
    connect,
    create_job,
    get_active_jobs,
    get_job,
    list_jobs,
    rows_to_dicts,
    update_job_status,
)
from ..engine.orchestrator import start_job_thread, request_abort

DEFAULT_SKIP_BY_MODE: dict[str, set[str]] = {
    "fast": {"dialogue", "reader_pull", "anti_ai"},
    "standard": {"dialogue", "reader_pull", "anti_ai"},
    "deep": set(),
}


def normalize_job_params(params: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize generation params before persisting a job.

    The UI can choose a coarse generation_mode while advanced callers may pass
    skip_steps directly. Both are supported; explicit skip_steps are merged with
    mode defaults so the orchestrator receives one simple contract.
    """
    normalized = dict(params or {})
    mode = str(normalized.get("generation_mode") or normalized.get("hosting_mode") or "standard")
    if mode not in DEFAULT_SKIP_BY_MODE:
        mode = "standard"
    explicit_skip = normalized.get("skip_steps") or []
    if not isinstance(explicit_skip, list):
        explicit_skip = []
    skip_steps = sorted(DEFAULT_SKIP_BY_MODE[mode] | {str(step) for step in explicit_skip})
    hosting_mode = str(normalized.get("hosting_mode") or "checkpoint")
    if "smart_stop_policy" not in normalized:
        normalized["smart_stop_policy"] = "warn" if hosting_mode == "pure" else "pause"
    normalized["generation_mode"] = mode
    normalized["skip_steps"] = skip_steps
    return normalized


def start_generation_job(
    project_id: str,
    blueprint_id: str = "",
    start_chapter: int = 1,
    target_count: int = 1,
    checkpoint_strategy: str = "none",
    auto_finalize: bool = True,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Start a new generation job. Raises 400 if project already has an active job."""
    # Concurrency control
    active = get_active_jobs(project_id)
    if active:
        raise HTTPException(
            status_code=409,
            detail="project already has an active job. Complete or abort it first.",
        )

    normalized_params = normalize_job_params(params)

    job = create_job(project_id, {
        "volume_blueprint_id": blueprint_id,
        "start_chapter_number": start_chapter,
        "target_chapter_count": target_count,
        "checkpoint_strategy": checkpoint_strategy,
        "auto_finalize": auto_finalize,
        "params": normalized_params,
    })

    # Start background thread
    start_job_thread(job["id"])
    return enrich_job_progress(job)


def pause_job(project_id: str, job_id: str) -> dict[str, Any]:
    """Request a running job to pause."""
    job = get_job(job_id)
    if not job or job["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] not in ("running",):
        raise HTTPException(status_code=409, detail=f"Cannot pause job in status '{job['status']}'")
    updated = update_job_status(job_id, "paused", pause_reason="user_paused")
    return enrich_job_progress(updated) if updated else job


def resume_job(project_id: str, job_id: str) -> dict[str, Any]:
    """Resume a paused/checkpoint job or retry a failed autonomous job."""
    job = get_job(job_id)
    if not job or job["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] not in ("paused", "checkpoint", "failed"):
        raise HTTPException(status_code=409, detail=f"Cannot resume job in status '{job['status']}'")
    update_job_status(job_id, "running", pause_reason="", pause_detail="", error_message="")
    start_job_thread(job_id)
    resumed = get_job(job_id)
    return enrich_job_progress(resumed) if resumed else job


def abort_job(project_id: str, job_id: str) -> dict[str, Any]:
    """Abort a running/paused job."""
    job = get_job(job_id)
    if not job or job["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Job not found")
    request_abort(job_id)
    updated = update_job_status(job_id, "aborted", pause_reason="user_aborted")
    return enrich_job_progress(updated) if updated else job


def continue_checkpoint(project_id: str, job_id: str) -> dict[str, Any]:
    """Continue from a checkpoint (same as resume)."""
    return resume_job(project_id, job_id)


def get_job_detail(project_id: str, job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if not job or job["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return enrich_job_progress(job)


def list_project_jobs(project_id: str) -> list[dict[str, Any]]:
    return [enrich_job_progress(job) for job in list_jobs(project_id)]


def enrich_job_progress(job: dict[str, Any]) -> dict[str, Any]:
    """Add durable progress fields derived from persisted step records."""
    start = _positive_int(job.get("start_chapter_number")) or 1
    target = _positive_int(job.get("target_chapter_count")) or 1
    last = start + target - 1
    required_steps = {"brief", "seed", "draft", "archaeology", "deepen", "finalize"}
    with connect() as conn:
        rows = rows_to_dicts(
            conn.execute(
                """
                SELECT chapter_number, step_name, step_status, error_message, created_at, completed_at
                FROM chapter_generation_steps
                WHERE job_id = ? AND chapter_number BETWEEN ? AND ?
                ORDER BY created_at ASC
                """,
                (job["id"], start, last),
            ).fetchall()
        )
    completed_by_chapter: dict[int, set[str]] = {}
    latest_failed: dict[str, Any] | None = None
    latest_seen_chapter = _positive_int(job.get("current_chapter_number"))
    for row in rows:
        chapter_number = _positive_int(row.get("chapter_number"))
        if chapter_number:
            latest_seen_chapter = max(latest_seen_chapter, chapter_number)
        if row.get("step_status") == "completed":
            completed_by_chapter.setdefault(chapter_number, set()).add(str(row.get("step_name") or ""))
        if row.get("step_status") == "failed":
            latest_failed = row
    completed_count = sum(1 for steps in completed_by_chapter.values() if required_steps.issubset(steps))
    progress_percent = round((completed_count / target) * 100) if target else 0
    enriched = dict(job)
    enriched["completed_chapter_count"] = completed_count
    enriched["progress_percent"] = min(100, max(0, progress_percent))
    enriched["current_chapter_number"] = latest_seen_chapter
    if latest_failed:
        enriched["failed_chapter_number"] = latest_failed.get("chapter_number")
        enriched["failed_step"] = latest_failed.get("step_name")
        enriched["last_step_error"] = latest_failed.get("error_message") or ""
    return enriched


def _positive_int(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0
