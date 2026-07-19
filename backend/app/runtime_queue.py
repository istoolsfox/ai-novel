import json
import os
import socket
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable

from .database import connect, new_id, row_to_dict, rows_to_dicts, utc_now


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _decode(value: Any, fallback: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return fallback


def _after(seconds: int | float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=max(0, seconds))).isoformat()


def _env_int(name: str, default: int, minimum: int = 1, maximum: int = 86_400) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


def lease_seconds() -> int:
    return _env_int("AI_NOVEL_RUNTIME_LEASE_SECONDS", 90, minimum=15, maximum=3600)


def heartbeat_seconds() -> int:
    return min(_env_int("AI_NOVEL_RUNTIME_HEARTBEAT_SECONDS", 10, minimum=1, maximum=300), max(1, lease_seconds() // 3))


def runtime_sync_enabled() -> bool:
    values = (
        os.getenv("AI_NOVEL_RUNTIME_SYNC", ""),
        os.getenv("AI_NOVEL_AUTOPILOT_SYNC", ""),
    )
    return any(value.lower() in {"1", "true", "yes"} for value in values)


def legacy_threads_enabled() -> bool:
    return os.getenv("AI_NOVEL_AUTOPILOT_LEGACY_THREADS", "").lower() in {"1", "true", "yes"}


def append_runtime_event(
    event_type: str,
    message: str,
    *,
    worker_id: str = "",
    task_id: str = "",
    project_id: str = "",
    payload: dict[str, Any] | None = None,
) -> None:
    try:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO runtime_events (
                    id, worker_id, task_id, project_id, event_type, message, payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (new_id(), worker_id, task_id, project_id, event_type, message, _json(payload or {}), utc_now()),
            )
    except sqlite3.OperationalError:
        # Runtime tables may not exist during the first wrapped database initialization.
        return


def register_worker(worker_id: str, worker_type: str = "all", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_workers (
                id, worker_type, status, hostname, pid, started_at, heartbeat_at,
                stopped_at, current_task_type, current_task_id, metadata
            ) VALUES (?, ?, 'active', ?, ?, ?, ?, '', '', '', ?)
            ON CONFLICT(id) DO UPDATE SET
                worker_type=excluded.worker_type,
                status='active',
                hostname=excluded.hostname,
                pid=excluded.pid,
                started_at=excluded.started_at,
                heartbeat_at=excluded.heartbeat_at,
                stopped_at='',
                current_task_type='',
                current_task_id='',
                metadata=excluded.metadata
            """,
            (worker_id, worker_type, socket.gethostname(), os.getpid(), now, now, _json(metadata or {})),
        )
        return row_to_dict(conn.execute("SELECT * FROM runtime_workers WHERE id = ?", (worker_id,)).fetchone()) or {}


def heartbeat_worker(worker_id: str, *, task_type: str = "", task_id: str = "") -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE runtime_workers
            SET status='active', heartbeat_at=?, current_task_type=?, current_task_id=?
            WHERE id=?
            """,
            (utc_now(), task_type, task_id, worker_id),
        )


def stop_worker(worker_id: str) -> None:
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            UPDATE runtime_workers
            SET status='stopped', heartbeat_at=?, stopped_at=?, current_task_type='', current_task_id=''
            WHERE id=?
            """,
            (now, now, worker_id),
        )
    append_runtime_event("worker.stopped", "Worker 已停止。", worker_id=worker_id)


def enqueue_runtime_task(
    task_type: str,
    *,
    project_id: str = "",
    payload: dict[str, Any] | None = None,
    priority: int = 100,
    max_attempts: int = 3,
    idempotency_key: str = "",
    deduplicate_active: bool = False,
) -> dict[str, Any]:
    now = utc_now()
    with connect() as conn:
        if deduplicate_active:
            existing = row_to_dict(
                conn.execute(
                    """
                    SELECT * FROM runtime_tasks
                    WHERE task_type=? AND project_id=? AND status IN ('queued','running')
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (task_type, project_id),
                ).fetchone()
            )
            if existing:
                existing["result"] = _decode(existing.get("result"), {})
                return existing

        task_id = new_id()
        conn.execute(
            """
            INSERT INTO runtime_tasks (
                id, project_id, task_type, status, payload, result, error_message,
                priority, attempts, max_attempts, available_at, claimed_by,
                claimed_at, heartbeat_at, lease_expires_at, idempotency_key,
                created_at, updated_at, completed_at
            ) VALUES (?, ?, ?, 'queued', ?, '{}', '', ?, 0, ?, ?, '', '', '', '', ?, ?, ?, '')
            """,
            (
                task_id,
                project_id,
                task_type,
                _json(payload or {}),
                int(priority),
                max(1, int(max_attempts)),
                now,
                idempotency_key,
                now,
                now,
            ),
        )
        task = row_to_dict(conn.execute("SELECT * FROM runtime_tasks WHERE id=?", (task_id,)).fetchone()) or {}
    append_runtime_event(
        "task.queued",
        f"异步任务已进入队列：{task_type}",
        task_id=task_id,
        project_id=project_id,
        payload={"task_type": task_type},
    )
    task["result"] = _decode(task.get("result"), {})
    return task


def runtime_task(task_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        task = row_to_dict(conn.execute("SELECT * FROM runtime_tasks WHERE id=?", (task_id,)).fetchone())
    if task:
        task["result"] = _decode(task.get("result"), {})
    return task


def latest_runtime_task(project_id: str, task_type: str) -> dict[str, Any] | None:
    with connect() as conn:
        task = row_to_dict(
            conn.execute(
                """
                SELECT * FROM runtime_tasks
                WHERE project_id=? AND task_type=?
                ORDER BY created_at DESC LIMIT 1
                """,
                (project_id, task_type),
            ).fetchone()
        )
    if task:
        task["result"] = _decode(task.get("result"), {})
    return task


def claim_runtime_task(worker_id: str, task_types: Iterable[str] = ("obsidian_export",)) -> dict[str, Any] | None:
    allowed = tuple(dict.fromkeys(str(item) for item in task_types if str(item)))
    if not allowed:
        return None
    placeholders = ",".join("?" for _ in allowed)
    now = utc_now()
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            f"""
            SELECT id FROM runtime_tasks
            WHERE status='queued' AND available_at<=? AND task_type IN ({placeholders})
            ORDER BY priority ASC, created_at ASC LIMIT 1
            """,
            (now, *allowed),
        ).fetchone()
        if not row:
            return None
        task_id = str(row["id"])
        updated = conn.execute(
            """
            UPDATE runtime_tasks
            SET status='running', claimed_by=?, claimed_at=?, heartbeat_at=?,
                lease_expires_at=?, attempts=attempts+1, updated_at=?, error_message=''
            WHERE id=? AND status='queued'
            """,
            (worker_id, now, now, _after(lease_seconds()), now, task_id),
        ).rowcount
        if not updated:
            return None
        task = row_to_dict(conn.execute("SELECT * FROM runtime_tasks WHERE id=?", (task_id,)).fetchone()) or {}
    task["result"] = _decode(task.get("result"), {})
    append_runtime_event(
        "task.claimed",
        f"Worker 已认领任务：{task.get('task_type', '')}",
        worker_id=worker_id,
        task_id=task_id,
        project_id=str(task.get("project_id") or ""),
    )
    return task


def heartbeat_runtime_task(task_id: str, worker_id: str) -> None:
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            UPDATE runtime_tasks
            SET heartbeat_at=?, lease_expires_at=?, updated_at=?
            WHERE id=? AND status='running' AND claimed_by=?
            """,
            (now, _after(lease_seconds()), now, task_id, worker_id),
        )


def complete_runtime_task(task_id: str, worker_id: str, result: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            UPDATE runtime_tasks
            SET status='completed', result=?, error_message='', heartbeat_at=?,
                lease_expires_at='', updated_at=?, completed_at=?
            WHERE id=? AND claimed_by=?
            """,
            (_json(result), now, now, now, task_id, worker_id),
        )
    append_runtime_event("task.completed", "异步任务已完成。", worker_id=worker_id, task_id=task_id)
    return runtime_task(task_id) or {}


def fail_runtime_task(task_id: str, worker_id: str, error_message: str) -> dict[str, Any]:
    now = utc_now()
    with connect() as conn:
        current = row_to_dict(conn.execute("SELECT * FROM runtime_tasks WHERE id=?", (task_id,)).fetchone()) or {}
        attempts = int(current.get("attempts") or 0)
        max_attempts = int(current.get("max_attempts") or 1)
        if attempts < max_attempts:
            delay = min(60, max(1, attempts * 2))
            conn.execute(
                """
                UPDATE runtime_tasks
                SET status='queued', error_message=?, available_at=?, claimed_by='',
                    claimed_at='', heartbeat_at='', lease_expires_at='', updated_at=?
                WHERE id=? AND claimed_by=?
                """,
                (error_message, _after(delay), now, task_id, worker_id),
            )
            event_type = "task.retry_scheduled"
        else:
            conn.execute(
                """
                UPDATE runtime_tasks
                SET status='failed', error_message=?, heartbeat_at=?, lease_expires_at='',
                    updated_at=?, completed_at=?
                WHERE id=? AND claimed_by=?
                """,
                (error_message, now, now, now, task_id, worker_id),
            )
            event_type = "task.failed"
    append_runtime_event(event_type, error_message, worker_id=worker_id, task_id=task_id)
    return runtime_task(task_id) or {}


def claim_generation_job(worker_id: str) -> dict[str, Any] | None:
    now = utc_now()
    try:
        with connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT id FROM generation_jobs
                WHERE status='queued'
                ORDER BY created_at ASC LIMIT 1
                """
            ).fetchone()
            if not row:
                return None
            job_id = str(row["id"])
            updated = conn.execute(
                """
                UPDATE generation_jobs
                SET status='running', worker_id=?, claimed_at=?, heartbeat_at=?,
                    lease_expires_at=?, updated_at=?,
                    started_at=CASE WHEN started_at='' THEN ? ELSE started_at END
                WHERE id=? AND status='queued'
                """,
                (worker_id, now, now, _after(lease_seconds()), now, now, job_id),
            ).rowcount
            if not updated:
                return None
            job = row_to_dict(conn.execute("SELECT * FROM generation_jobs WHERE id=?", (job_id,)).fetchone())
        if job:
            append_runtime_event(
                "autopilot.claimed",
                "Worker 已认领托管任务。",
                worker_id=worker_id,
                task_id=job_id,
                project_id=str(job.get("project_id") or ""),
            )
        return job
    except sqlite3.OperationalError:
        return None


def heartbeat_generation_job(job_id: str, worker_id: str) -> None:
    now = utc_now()
    try:
        with connect() as conn:
            conn.execute(
                """
                UPDATE generation_jobs
                SET heartbeat_at=?, lease_expires_at=?, updated_at=?
                WHERE id=? AND worker_id=? AND status='running'
                """,
                (now, _after(lease_seconds()), now, job_id, worker_id),
            )
    except sqlite3.OperationalError:
        return


def clear_generation_claim(job_id: str, worker_id: str) -> None:
    try:
        with connect() as conn:
            conn.execute(
                """
                UPDATE generation_jobs
                SET worker_id='', claimed_at='', heartbeat_at='', lease_expires_at='', updated_at=?
                WHERE id=? AND worker_id=?
                """,
                (utc_now(), job_id, worker_id),
            )
    except sqlite3.OperationalError:
        return


def abandon_generation_claim(job_id: str, worker_id: str, error_message: str) -> None:
    now = utc_now()
    try:
        with connect() as conn:
            job = row_to_dict(conn.execute("SELECT * FROM generation_jobs WHERE id=?", (job_id,)).fetchone()) or {}
            conn.execute(
                "UPDATE generation_steps SET status='pending', updated_at=? WHERE job_id=? AND status='running'",
                (now, job_id),
            )
            conn.execute(
                """
                UPDATE generation_jobs
                SET status='queued', current_step='', worker_id='', claimed_at='', heartbeat_at='',
                    lease_expires_at='', recovery_count=recovery_count+1, error_message=?, updated_at=?
                WHERE id=? AND worker_id=? AND status='running'
                """,
                (error_message, now, job_id, worker_id),
            )
            if job:
                conn.execute(
                    """
                    INSERT INTO generation_events (id, job_id, project_id, event_type, message, payload, created_at)
                    VALUES (?, ?, ?, 'job.worker_released', ?, ?, ?)
                    """,
                    (new_id(), job_id, job.get("project_id", ""), "Worker 异常退出，任务已重新排队。", _json({"error": error_message}), now),
                )
    except sqlite3.OperationalError:
        return


def recover_stale_generation_jobs() -> int:
    now = utc_now()
    recovered = 0
    try:
        with connect() as conn:
            columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(generation_jobs)").fetchall()}
            if "lease_expires_at" not in columns:
                return 0
            stale = rows_to_dicts(
                conn.execute(
                    """
                    SELECT * FROM generation_jobs
                    WHERE status='running' AND (lease_expires_at='' OR lease_expires_at<?)
                    ORDER BY updated_at
                    """,
                    (now,),
                ).fetchall()
            )
            for job in stale:
                conn.execute(
                    "UPDATE generation_steps SET status='pending', updated_at=? WHERE job_id=? AND status='running'",
                    (now, job["id"]),
                )
                conn.execute(
                    """
                    UPDATE generation_jobs
                    SET status='queued', current_step='', worker_id='', claimed_at='', heartbeat_at='',
                        lease_expires_at='', recovery_count=recovery_count+1, updated_at=?
                    WHERE id=? AND status='running'
                    """,
                    (now, job["id"]),
                )
                conn.execute(
                    """
                    INSERT INTO generation_events (id, job_id, project_id, event_type, message, payload, created_at)
                    VALUES (?, ?, ?, 'job.lease_recovered', 'Worker 心跳过期，任务已恢复到队列。', ?, ?)
                    """,
                    (new_id(), job["id"], job["project_id"], _json({"previous_worker_id": job.get("worker_id", "")}), now),
                )
                recovered += 1
    except sqlite3.OperationalError:
        return 0
    return recovered


def recover_stale_runtime_tasks() -> int:
    now = utc_now()
    recovered = 0
    try:
        with connect() as conn:
            stale = rows_to_dicts(
                conn.execute(
                    """
                    SELECT * FROM runtime_tasks
                    WHERE status='running' AND (lease_expires_at='' OR lease_expires_at<?)
                    ORDER BY updated_at
                    """,
                    (now,),
                ).fetchall()
            )
            for task in stale:
                attempts = int(task.get("attempts") or 0)
                max_attempts = int(task.get("max_attempts") or 1)
                status = "queued" if attempts < max_attempts else "failed"
                completed_at = "" if status == "queued" else now
                conn.execute(
                    """
                    UPDATE runtime_tasks
                    SET status=?, claimed_by='', claimed_at='', heartbeat_at='', lease_expires_at='',
                        available_at=?, updated_at=?, completed_at=?, error_message='Worker 心跳过期，任务已恢复。'
                    WHERE id=? AND status='running'
                    """,
                    (status, now, now, completed_at, task["id"]),
                )
                recovered += 1
                append_runtime_event(
                    "task.lease_recovered" if status == "queued" else "task.lease_failed",
                    "Worker 心跳过期，异步任务已恢复。",
                    task_id=str(task["id"]),
                    project_id=str(task.get("project_id") or ""),
                    payload={"previous_worker_id": task.get("claimed_by", "")},
                )
    except sqlite3.OperationalError:
        return 0
    return recovered


@contextmanager
def heartbeat_pump(callbacks: Iterable[Callable[[], None]], interval: int | None = None):
    stop = threading.Event()
    callback_list = list(callbacks)

    def beat() -> None:
        while not stop.wait(interval or heartbeat_seconds()):
            for callback in callback_list:
                try:
                    callback()
                except Exception:
                    continue

    for callback in callback_list:
        try:
            callback()
        except Exception:
            continue
    thread = threading.Thread(target=beat, daemon=True, name="runtime-heartbeat")
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=2)


def runtime_diagnostics() -> dict[str, Any]:
    now = utc_now()
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=lease_seconds() * 2)).isoformat()
    with connect() as conn:
        workers = rows_to_dicts(
            conn.execute("SELECT * FROM runtime_workers ORDER BY heartbeat_at DESC LIMIT 100").fetchall()
        )
        task_counts = {
            str(row["status"]): int(row["count"])
            for row in conn.execute("SELECT status, COUNT(*) AS count FROM runtime_tasks GROUP BY status").fetchall()
        }
        task_types = {
            str(row["task_type"]): int(row["count"])
            for row in conn.execute(
                "SELECT task_type, COUNT(*) AS count FROM runtime_tasks WHERE status IN ('queued','running') GROUP BY task_type"
            ).fetchall()
        }
        try:
            generation_counts = {
                str(row["status"]): int(row["count"])
                for row in conn.execute("SELECT status, COUNT(*) AS count FROM generation_jobs GROUP BY status").fetchall()
            }
            stale_generation = int(
                conn.execute(
                    "SELECT COUNT(*) FROM generation_jobs WHERE status='running' AND (lease_expires_at='' OR lease_expires_at<?)",
                    (now,),
                ).fetchone()[0]
            )
        except sqlite3.OperationalError:
            generation_counts, stale_generation = {}, 0
        stale_tasks = int(
            conn.execute(
                "SELECT COUNT(*) FROM runtime_tasks WHERE status='running' AND (lease_expires_at='' OR lease_expires_at<?)",
                (now,),
            ).fetchone()[0]
        )
    for worker in workers:
        worker["metadata"] = _decode(worker.get("metadata"), {})
        worker["healthy"] = worker.get("status") == "active" and str(worker.get("heartbeat_at") or "") >= cutoff
    return {
        "workers": workers,
        "active_workers": sum(1 for worker in workers if worker.get("healthy")),
        "runtime_tasks": task_counts,
        "runtime_task_types": task_types,
        "generation_jobs": generation_counts,
        "stale_runtime_tasks": stale_tasks,
        "stale_generation_jobs": stale_generation,
        "lease_seconds": lease_seconds(),
        "heartbeat_seconds": heartbeat_seconds(),
    }
