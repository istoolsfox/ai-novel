import sqlite3

from . import autopilot
from .database import connect
from .runtime_queue import (
    append_runtime_event,
    legacy_threads_enabled,
    recover_stale_generation_jobs,
    runtime_sync_enabled,
)

_INSTALLED = False
_ORIGINAL_WAKE_JOB = autopilot._wake_job


def _external_wake_job(job_id: str) -> None:
    if autopilot._worker_disabled():
        return
    if runtime_sync_enabled() or legacy_threads_enabled():
        _ORIGINAL_WAKE_JOB(job_id)
        return
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT project_id FROM generation_jobs WHERE id=? AND status='queued'",
                (job_id,),
            ).fetchone()
        if row:
            append_runtime_event(
                "autopilot.queued",
                "托管任务等待独立 Worker 认领。",
                task_id=job_id,
                project_id=str(row["project_id"]),
            )
    except sqlite3.OperationalError:
        return


def _recover_for_runtime() -> None:
    recover_stale_generation_jobs()
    if not runtime_sync_enabled():
        return
    try:
        with connect() as conn:
            queued = [
                str(row["id"])
                for row in conn.execute(
                    "SELECT id FROM generation_jobs WHERE status='queued' ORDER BY created_at"
                ).fetchall()
            ]
    except sqlite3.OperationalError:
        return
    for job_id in queued:
        _ORIGINAL_WAKE_JOB(job_id)


def install_external_autopilot_runtime() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    autopilot._wake_job = _external_wake_job
    autopilot.recover_interrupted_jobs = _recover_for_runtime
    _INSTALLED = True
