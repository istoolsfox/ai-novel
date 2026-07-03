"""Application: job service.

Use cases for generation jobs: start / pause / resume / abort.
Includes concurrency control (one active job per project).
"""
from typing import Any

from fastapi import HTTPException

from ..infrastructure.database import (
    create_job,
    get_active_jobs,
    get_job,
    list_jobs,
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
    return job


def pause_job(project_id: str, job_id: str) -> dict[str, Any]:
    """Request a running job to pause."""
    job = get_job(job_id)
    if not job or job["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] not in ("running",):
        raise HTTPException(status_code=409, detail=f"Cannot pause job in status '{job['status']}'")
    return update_job_status(job_id, "paused", pause_reason="user_paused")


def resume_job(project_id: str, job_id: str) -> dict[str, Any]:
    """Resume a paused or checkpoint job."""
    job = get_job(job_id)
    if not job or job["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] not in ("paused", "checkpoint"):
        raise HTTPException(status_code=409, detail=f"Cannot resume job in status '{job['status']}'")
    update_job_status(job_id, "running", pause_reason="", pause_detail="")
    start_job_thread(job_id)
    return get_job(job_id)


def abort_job(project_id: str, job_id: str) -> dict[str, Any]:
    """Abort a running/paused job."""
    job = get_job(job_id)
    if not job or job["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Job not found")
    request_abort(job_id)
    return update_job_status(job_id, "aborted", pause_reason="user_aborted")


def continue_checkpoint(project_id: str, job_id: str) -> dict[str, Any]:
    """Continue from a checkpoint (same as resume)."""
    return resume_job(project_id, job_id)


def get_job_detail(project_id: str, job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if not job or job["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def list_project_jobs(project_id: str) -> list[dict[str, Any]]:
    return list_jobs(project_id)
