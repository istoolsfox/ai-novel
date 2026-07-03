"""Routes: generation jobs + SSE stream."""
import json
import time
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ...application.job_service import (
    abort_job,
    continue_checkpoint,
    get_job_detail,
    list_project_jobs,
    pause_job,
    resume_job,
    start_generation_job,
)
from ...infrastructure.database import list_steps
from ...infrastructure.storage import require_project
from ...engine.orchestrator import consume_events, get_event_count

router = APIRouter(prefix="/api/projects/{project_id}/jobs", tags=["jobs"])


class JobStartIn(BaseModel):
    blueprint_id: str = ""
    start_chapter: int = 1
    count: int = 1
    checkpoint_strategy: str = "none"
    auto_finalize: bool = True
    params: dict[str, Any] = {}


@router.post("")
def start_job_route(project_id: str, payload: JobStartIn) -> dict[str, Any]:
    require_project(project_id)
    return start_generation_job(
        project_id=project_id,
        blueprint_id=payload.blueprint_id,
        start_chapter=payload.start_chapter,
        target_count=payload.count,
        checkpoint_strategy=payload.checkpoint_strategy,
        auto_finalize=payload.auto_finalize,
        params=payload.params,
    )


@router.get("")
def list_jobs_route(project_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    return list_project_jobs(project_id)


@router.get("/{job_id}")
def get_job_route(project_id: str, job_id: str) -> dict[str, Any]:
    require_project(project_id)
    return get_job_detail(project_id, job_id)


@router.post("/{job_id}/pause")
def pause_job_route(project_id: str, job_id: str) -> dict[str, Any]:
    require_project(project_id)
    return pause_job(project_id, job_id)


@router.post("/{job_id}/resume")
def resume_job_route(project_id: str, job_id: str) -> dict[str, Any]:
    require_project(project_id)
    return resume_job(project_id, job_id)


@router.post("/{job_id}/abort")
def abort_job_route(project_id: str, job_id: str) -> dict[str, Any]:
    require_project(project_id)
    return abort_job(project_id, job_id)


@router.post("/{job_id}/checkpoint/continue")
def checkpoint_continue_route(project_id: str, job_id: str) -> dict[str, Any]:
    require_project(project_id)
    return continue_checkpoint(project_id, job_id)


@router.get("/{job_id}/steps")
def list_job_steps_route(project_id: str, job_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    return list_steps(job_id)


@router.get("/{job_id}/stream")
def job_stream_route(project_id: str, job_id: str):
    """SSE endpoint for real-time job progress."""
    require_project(project_id)

    def event_generator():
        last_index = 0
        from ...infrastructure.database import get_job
        while True:
            # Check if job is done
            job = get_job(job_id)
            if not job:
                yield f"data: {json.dumps({'type': 'error', 'message': 'job not found'})}\n\n"
                break
            if job["status"] in ("completed", "failed", "aborted"):
                # Send remaining events
                events = consume_events(job_id, last_index)
                for evt in events:
                    yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'status': job['status']})}\n\n"
                break

            # Send new events
            events = consume_events(job_id, last_index)
            for evt in events:
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
            last_index = get_event_count(job_id)

            time.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
