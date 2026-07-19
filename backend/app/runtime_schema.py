import sqlite3

from .database import connect


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except sqlite3.OperationalError:
        return set()


def _add_column(conn: sqlite3.Connection, table: str, definition: str) -> None:
    name = definition.split()[0]
    if name not in _column_names(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def init_runtime_schema() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runtime_workers (
                id TEXT PRIMARY KEY,
                worker_type TEXT NOT NULL DEFAULT 'all',
                status TEXT NOT NULL DEFAULT 'active',
                hostname TEXT DEFAULT '',
                pid INTEGER DEFAULT 0,
                started_at TEXT NOT NULL,
                heartbeat_at TEXT NOT NULL,
                stopped_at TEXT DEFAULT '',
                current_task_type TEXT DEFAULT '',
                current_task_id TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS runtime_tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT DEFAULT '',
                task_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                payload TEXT DEFAULT '{}',
                result TEXT DEFAULT '{}',
                error_message TEXT DEFAULT '',
                priority INTEGER NOT NULL DEFAULT 100,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                available_at TEXT NOT NULL,
                claimed_by TEXT DEFAULT '',
                claimed_at TEXT DEFAULT '',
                heartbeat_at TEXT DEFAULT '',
                lease_expires_at TEXT DEFAULT '',
                idempotency_key TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS runtime_events (
                id TEXT PRIMARY KEY,
                worker_id TEXT DEFAULT '',
                task_id TEXT DEFAULT '',
                project_id TEXT DEFAULT '',
                event_type TEXT NOT NULL,
                message TEXT DEFAULT '',
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_tasks_idempotency
            ON runtime_tasks(idempotency_key)
            WHERE idempotency_key != '';

            CREATE INDEX IF NOT EXISTS idx_runtime_tasks_claim
            ON runtime_tasks(status, task_type, priority, available_at, created_at);

            CREATE INDEX IF NOT EXISTS idx_runtime_workers_heartbeat
            ON runtime_workers(status, heartbeat_at);

            CREATE INDEX IF NOT EXISTS idx_runtime_events_created
            ON runtime_events(created_at);
            """
        )

        if _column_names(conn, "generation_jobs"):
            _add_column(conn, "generation_jobs", "worker_id TEXT DEFAULT ''")
            _add_column(conn, "generation_jobs", "claimed_at TEXT DEFAULT ''")
            _add_column(conn, "generation_jobs", "heartbeat_at TEXT DEFAULT ''")
            _add_column(conn, "generation_jobs", "lease_expires_at TEXT DEFAULT ''")
            _add_column(conn, "generation_jobs", "recovery_count INTEGER DEFAULT 0")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_generation_jobs_runtime_claim "
                "ON generation_jobs(status, lease_expires_at, created_at)"
            )
