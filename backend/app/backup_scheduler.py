from datetime import datetime, timedelta, timezone
from typing import Any

from .backup_service import create_database_backup, list_database_backups, remove_database_backup
from .database import connect, row_to_dict, utc_now
from .runtime_queue import append_runtime_event, lease_seconds


SCHEDULE_ID = "default"


def _after_seconds(seconds: int | float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=max(0, seconds))).isoformat()


def _after_hours(hours: int | float) -> str:
    return _after_seconds(float(hours) * 3600)


def init_backup_schedule_schema() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runtime_backup_schedules (
                id TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0,
                interval_hours INTEGER NOT NULL DEFAULT 24,
                retention_count INTEGER NOT NULL DEFAULT 7,
                next_run_at TEXT DEFAULT '',
                last_run_at TEXT DEFAULT '',
                last_backup_id TEXT DEFAULT '',
                last_error TEXT DEFAULT '',
                claimed_by TEXT DEFAULT '',
                lease_expires_at TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        now = utc_now()
        conn.execute(
            """
            INSERT INTO runtime_backup_schedules (
                id, enabled, interval_hours, retention_count, next_run_at,
                last_run_at, last_backup_id, last_error, claimed_by,
                lease_expires_at, created_at, updated_at
            ) VALUES (?, 0, 24, 7, '', '', '', '', '', '', ?, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (SCHEDULE_ID, now, now),
        )


def _schedule_payload(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {}
    return {
        **row,
        "enabled": bool(row.get("enabled")),
        "interval_hours": int(row.get("interval_hours") or 24),
        "retention_count": int(row.get("retention_count") or 7),
    }


def get_backup_schedule() -> dict[str, Any]:
    init_backup_schedule_schema()
    with connect() as conn:
        row = row_to_dict(
            conn.execute("SELECT * FROM runtime_backup_schedules WHERE id=?", (SCHEDULE_ID,)).fetchone()
        )
    return _schedule_payload(row)


def update_backup_schedule(*, enabled: bool, interval_hours: int, retention_count: int) -> dict[str, Any]:
    init_backup_schedule_schema()
    interval = max(1, min(int(interval_hours), 24 * 30))
    retention = max(1, min(int(retention_count), 100))
    now = utc_now()
    with connect() as conn:
        current = row_to_dict(
            conn.execute("SELECT * FROM runtime_backup_schedules WHERE id=?", (SCHEDULE_ID,)).fetchone()
        ) or {}
        next_run = str(current.get("next_run_at") or "")
        if enabled and (not current.get("enabled") or not next_run):
            next_run = _after_hours(interval)
        if not enabled:
            next_run = ""
        conn.execute(
            """
            UPDATE runtime_backup_schedules
            SET enabled=?, interval_hours=?, retention_count=?, next_run_at=?,
                claimed_by='', lease_expires_at='', updated_at=?
            WHERE id=?
            """,
            (int(enabled), interval, retention, next_run, now, SCHEDULE_ID),
        )
    append_runtime_event(
        "backup.schedule_updated",
        "自动备份计划已更新。",
        payload={"enabled": enabled, "interval_hours": interval, "retention_count": retention},
    )
    return get_backup_schedule()


def trigger_backup_schedule() -> dict[str, Any]:
    init_backup_schedule_schema()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            UPDATE runtime_backup_schedules
            SET enabled=1, next_run_at=?, claimed_by='', lease_expires_at='', updated_at=?
            WHERE id=?
            """,
            (now, now, SCHEDULE_ID),
        )
    append_runtime_event("backup.schedule_triggered", "已请求 Worker 立即执行计划备份。")
    return get_backup_schedule()


def _prune_scheduled_backups(retention_count: int) -> list[str]:
    scheduled = [backup for backup in list_database_backups() if backup.get("kind") == "scheduled"]
    deleted: list[str] = []
    for backup in scheduled[max(1, retention_count):]:
        backup_id = str(backup.get("id") or "")
        if backup_id:
            remove_database_backup(backup_id)
            deleted.append(backup_id)
    return deleted


def _claim_due_schedule(worker_id: str) -> dict[str, Any] | None:
    init_backup_schedule_schema()
    now = utc_now()
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = row_to_dict(
            conn.execute("SELECT * FROM runtime_backup_schedules WHERE id=?", (SCHEDULE_ID,)).fetchone()
        ) or {}
        if not row.get("enabled"):
            return None
        next_run_at = str(row.get("next_run_at") or "")
        lease_expires_at = str(row.get("lease_expires_at") or "")
        has_live_claim = bool(row.get("claimed_by") and lease_expires_at and lease_expires_at > now)
        if has_live_claim:
            return None
        # A stale claim may be recovered immediately even though the previous claimant
        # already advanced next_run_at. Unclaimed schedules must actually be due.
        if not row.get("claimed_by") and next_run_at and next_run_at > now:
            return None
        interval = int(row.get("interval_hours") or 24)
        updated = conn.execute(
            """
            UPDATE runtime_backup_schedules
            SET claimed_by=?, lease_expires_at=?, next_run_at=?, updated_at=?
            WHERE id=? AND enabled=1
            """,
            (worker_id, _after_seconds(lease_seconds()), _after_hours(interval), now, SCHEDULE_ID),
        ).rowcount
        if not updated:
            return None
        return _schedule_payload(
            row_to_dict(
                conn.execute("SELECT * FROM runtime_backup_schedules WHERE id=?", (SCHEDULE_ID,)).fetchone()
            )
        )


def run_due_backup_schedule(worker_id: str) -> dict[str, Any] | None:
    schedule = _claim_due_schedule(worker_id)
    if not schedule:
        return None
    interval = int(schedule.get("interval_hours") or 24)
    retention = int(schedule.get("retention_count") or 7)
    try:
        backup = create_database_backup(note="Automatic scheduled backup", backup_kind="scheduled")
        deleted = _prune_scheduled_backups(retention)
        now = utc_now()
        with connect() as conn:
            conn.execute(
                """
                UPDATE runtime_backup_schedules
                SET last_run_at=?, last_backup_id=?, last_error='', next_run_at=?,
                    claimed_by='', lease_expires_at='', updated_at=?
                WHERE id=? AND claimed_by=?
                """,
                (now, backup["id"], _after_hours(interval), now, SCHEDULE_ID, worker_id),
            )
        append_runtime_event(
            "backup.scheduled_completed",
            "自动数据库备份已完成。",
            worker_id=worker_id,
            payload={"backup_id": backup["id"], "pruned_backup_ids": deleted},
        )
        return {"status": "completed", "backup": backup, "pruned_backup_ids": deleted}
    except Exception as exc:
        error = str(exc)
        now = utc_now()
        with connect() as conn:
            conn.execute(
                """
                UPDATE runtime_backup_schedules
                SET last_error=?, next_run_at=?, claimed_by='', lease_expires_at='', updated_at=?
                WHERE id=? AND claimed_by=?
                """,
                (error, _after_seconds(min(interval * 3600, 3600)), now, SCHEDULE_ID, worker_id),
            )
        append_runtime_event(
            "backup.scheduled_failed",
            "自动数据库备份失败。",
            worker_id=worker_id,
            payload={"error": error},
        )
        return {"status": "failed", "error": error}
