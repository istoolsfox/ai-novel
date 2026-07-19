import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .backup_scheduler import (
    get_backup_schedule,
    trigger_backup_schedule,
    update_backup_schedule,
)
from .backup_service import (
    backup_directory,
    create_database_backup,
    get_database_backup,
    list_database_backups,
    remove_database_backup,
    restore_database_backup,
)
from .database import connect, database_path, rows_to_dicts, utc_now
from .migration_service import migration_status
from .runtime_queue import runtime_diagnostics, runtime_sync_enabled, runtime_task
from .runtime_recovery import recover_all_stale_work

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


class BackupCreateIn(BaseModel):
    note: str = Field(default="", max_length=500)


class BackupRestoreIn(BaseModel):
    confirmation: str


class BackupScheduleIn(BaseModel):
    enabled: bool = False
    interval_hours: int = Field(default=24, ge=1, le=24 * 30)
    retention_count: int = Field(default=7, ge=1, le=100)


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
    schedule = get_backup_schedule()
    schema = migration_status()
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
    if schedule.get("enabled") and not diagnostics.get("active_workers"):
        warnings.append("自动备份已启用，但没有健康的 Worker。")
    if schedule.get("last_error"):
        warnings.append("最近一次自动备份失败。")
    if schema.get("drift") or schema.get("unknown_versions"):
        warnings.append("数据库迁移历史存在校验和漂移或未知版本，升级已被阻止。")
    elif schema.get("pending"):
        warnings.append("数据库存在待执行迁移，请在启动 Worker 前完成升级。")
    status = "ok" if database.get("ok") and storage.get("ok") and not warnings else "degraded"
    return {
        "status": status,
        "database": database,
        "storage": storage,
        "runtime": diagnostics,
        "backup_schedule": schedule,
        "migrations": schema,
        "warnings": warnings,
        "checked_at": utc_now(),
    }


@router.get("/diagnostics")
def get_runtime_diagnostics() -> dict[str, Any]:
    return {
        **runtime_diagnostics(),
        "backup_schedule": get_backup_schedule(),
        "migrations": migration_status(),
    }


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
def list_runtime_events(
    limit: int = 100,
    event_type: str = "",
    worker_id: str = "",
    task_id: str = "",
) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 500))
    clauses: list[str] = []
    values: list[Any] = []
    for column, value in (("event_type", event_type), ("worker_id", worker_id), ("task_id", task_id)):
        if value:
            clauses.append(f"{column}=?")
            values.append(value)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        events = rows_to_dicts(
            conn.execute(
                f"SELECT * FROM runtime_events{where} ORDER BY created_at DESC LIMIT ?",
                (*values, safe_limit),
            ).fetchall()
        )
    for event in events:
        event["payload"] = _decode(event.get("payload"))
    return events


@router.post("/recover")
def recover_runtime_leases() -> dict[str, Any]:
    return {"status": "completed", "recovered": recover_all_stale_work(), "recovered_at": utc_now()}


@router.get("/backup-schedule")
def backup_schedule() -> dict[str, Any]:
    return get_backup_schedule()


@router.put("/backup-schedule")
def configure_backup_schedule(payload: BackupScheduleIn) -> dict[str, Any]:
    return update_backup_schedule(
        enabled=payload.enabled,
        interval_hours=payload.interval_hours,
        retention_count=payload.retention_count,
    )


@router.post("/backup-schedule/run-now")
def run_backup_schedule_now() -> dict[str, Any]:
    return trigger_backup_schedule()


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
