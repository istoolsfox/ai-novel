import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .backup_service import (
    backup_directory,
    create_database_backup,
    get_database_backup,
    list_database_backups,
    remove_database_backup,
    restore_database_backup,
)
from .database import connect, database_path, row_to_dict, rows_to_dicts, utc_now
from .runtime_queue import runtime_diagnostics, runtime_sync_enabled, runtime_task
from .runtime_recovery import recover_all_stale_work

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


class BackupCreateIn(BaseModel):
    note: str = Field(default="", max_length=500)


class BackupRestoreIn(BaseModel):
    confirmation: str


def _call(operation, *args, **kwargs):
    try:
        return operation(*args, **kwargs)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 409
        raise HTTPException(status_code=status, detail=message) from exc


def _decode(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _storage_check() -> dict[str, Any]:
    target = database_path().parent
    target.mkdir(parents=True, exist_ok=True)
    probe = target / f".runtime-health-{os.getpid()}.tmp"
    try:
        probe.write_text(utc_now(), encoding="utf-8")
        probe.unlink(missing_ok=True)
        return {"ok": True, "path": str(target)}
    except OSError as exc:
        probe.unlink(missing_ok=True)
        return {"ok": False, "path": str(target), "error": str(exc)}


def _database_check() -> dict[str, Any]:
    try:
        with connect() as conn:
            conn.execute("SELECT 1").fetchone()
            quick_check = str(conn.execute("PRAGMA quick_check").fetchone()[0])
        return {"ok": quick_check.lower() == "ok", "quick_check": quick_check, "path": str(database_path())}
    except (sqlite3.Error, RuntimeError) as exc:
        return {"ok": False, "quick_check": "failed", "path": str(database_path()), "error": str(exc)}


@router.get("/health")
def runtime_health() -> dict[str, Any]:
    database = _database_check()
    storage = _storage_check()
    diagnostics = runtime_diagnostics()
    queued_work = (
        int(diagnostics.get("generation_jobs", {}).get("queued", 0))
        + int(diagnostics.get("generation_jobs", {}).get("running", 0))
        + int(diagnostics.get("runtime_tasks", {}).get("queued", 0))
        + int(diagnostics.get("runtime_tasks", {}).get("running", 0))
    )
    warnings: list[str] = []
    if queued_work and not diagnostics.get("active_workers") and not runtime_sync_enabled():
        warnings.append("队列中存在任务，但没有健康的独立 Worker。")
    if diagnostics.get("stale_generation_jobs") or diagnostics.get("stale_runtime_tasks"):
        warnings.append("检测到租约已过期的运行任务，可执行恢复。")
    status = "ok" if database.get("ok") and storage.get("ok") and not warnings else "degraded"
    return {
        "status": status,
        "database": database,
        "storage": storage,
        "runtime": diagnostics,
        "warnings": warnings,
        "checked_at": utc_now(),
    }


@router.get("/diagnostics")
def get_runtime_diagnostics() -> dict[str, Any]:
    return runtime_diagnostics()


@router.get("/workers")
def list_runtime_workers() -> list[dict[str, Any]]:
    return list(runtime_diagnostics().get("workers") or [])


@router.get("/tasks")
def list_runtime_tasks(limit: int = 100, status: str = "") -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 500))
    with connect() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM runtime_tasks WHERE status=? ORDER BY created_at DESC LIMIT ?",
                (status, safe_limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM runtime_tasks ORDER BY created_at DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
    tasks = rows_to_dicts(rows)
    for task in tasks:
        task["result"] = _decode(task.get("result"))
    return tasks


@router.get("/tasks/{task_id}")
def get_runtime_task(task_id: str) -> dict[str, Any]:
    task = runtime_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Runtime task not found")
    return task


@router.get("/events")
def list_runtime_events(limit: int = 100) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 500))
    with connect() as conn:
        events = rows_to_dicts(
            conn.execute("SELECT * FROM runtime_events ORDER BY created_at DESC LIMIT ?", (safe_limit,)).fetchall()
        )
    return events


@router.post("/recover")
def recover_runtime_leases() -> dict[str, Any]:
    return {"status": "completed", "recovered": recover_all_stale_work(), "recovered_at": utc_now()}


@router.get("/backups")
def list_backups() -> list[dict[str, Any]]:
    return list_database_backups()


@router.post("/backups")
def create_backup(payload: BackupCreateIn) -> dict[str, Any]:
    return _call(create_database_backup, note=payload.note)


@router.get("/backups/{backup_id}")
def get_backup(backup_id: str, verify: bool = False) -> dict[str, Any]:
    return _call(get_database_backup, backup_id, verify=verify)


@router.get("/backups/{backup_id}/download")
def download_backup(backup_id: str):
    backup = _call(get_database_backup, backup_id, verify=True)
    path = Path(str(backup.get("file_path") or "")).resolve()
    try:
        path.relative_to(backup_directory())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid backup path") from exc
    return FileResponse(path, media_type="application/vnd.sqlite3", filename=path.name)


@router.post("/backups/{backup_id}/restore")
def restore_backup(backup_id: str, payload: BackupRestoreIn) -> dict[str, Any]:
    return _call(restore_database_backup, backup_id, confirmation=payload.confirmation)


@router.delete("/backups/{backup_id}")
def delete_backup(backup_id: str) -> dict[str, Any]:
    return _call(remove_database_backup, backup_id)
