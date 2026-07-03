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

    job = create_job(project_id, {
        "volume_blueprint_id": blueprint_id,
        "start_chapter_number": start_chapter,
        "target_chapter_count": target_count,
        "checkpoint_strategy": checkpoint_strategy,
        "auto_finalize": auto_finalize,
        "params": params or {},
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
