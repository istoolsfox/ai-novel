import json
import sqlite3

from .database import connect, new_id, rows_to_dicts, utc_now
from .runtime_queue import recover_stale_generation_jobs


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
                conn.execute(
                    """
                    INSERT INTO runtime_events (
                        id, worker_id, task_id, project_id, event_type, message, payload, created_at
                    ) VALUES (?, '', ?, ?, ?, 'Worker 心跳过期，异步任务已恢复。', ?, ?)
                    """,
                    (
                        new_id(),
                        task["id"],
                        task.get("project_id", ""),
                        "task.lease_recovered" if status == "queued" else "task.lease_failed",
                        json.dumps({"previous_worker_id": task.get("claimed_by", "")}, ensure_ascii=False),
                        now,
                    ),
                )
                recovered += 1
    except sqlite3.OperationalError:
        return 0
    return recovered


def recover_all_stale_work() -> dict[str, int]:
    return {
        "generation_jobs": recover_stale_generation_jobs(),
        "runtime_tasks": recover_stale_runtime_tasks(),
    }
