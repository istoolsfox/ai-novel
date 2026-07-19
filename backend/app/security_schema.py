import sqlite3

from .database import connect


def init_security_schema() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS encrypted_credentials (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                provider TEXT NOT NULL DEFAULT '',
                encrypted_secret TEXT NOT NULL,
                key_fingerprint TEXT NOT NULL,
                secret_hint TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_used_at TEXT DEFAULT '',
                rotated_at TEXT DEFAULT '',
                UNIQUE(project_id, name)
            );

            CREATE TABLE IF NOT EXISTS security_events (
                id TEXT PRIMARY KEY,
                project_id TEXT DEFAULT '',
                credential_id TEXT DEFAULT '',
                event_type TEXT NOT NULL,
                message TEXT DEFAULT '',
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_encrypted_credentials_project
            ON encrypted_credentials(project_id, status, updated_at);

            CREATE INDEX IF NOT EXISTS idx_security_events_created
            ON security_events(created_at);
            """
        )


def security_schema_ready() -> bool:
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='encrypted_credentials'"
            ).fetchone()
        return bool(row)
    except sqlite3.Error:
        return False
