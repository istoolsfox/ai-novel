import sqlite3


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def apply_release_state_migration(conn: sqlite3.Connection) -> None:
    columns = _columns(conn, "application_state")
    if "setup_payload" not in columns:
        conn.execute("ALTER TABLE application_state ADD COLUMN setup_payload TEXT DEFAULT '{}'")
    if "completed_at" not in columns:
        conn.execute("ALTER TABLE application_state ADD COLUMN completed_at TEXT DEFAULT ''")
    if "last_readiness_at" not in columns:
        conn.execute("ALTER TABLE application_state ADD COLUMN last_readiness_at TEXT DEFAULT ''")
    conn.execute(
        """
        INSERT INTO application_metadata (key, value, updated_at)
        VALUES ('release_candidate_schema', 'v1', datetime('now'))
        ON CONFLICT(key) DO UPDATE SET value='v1', updated_at=datetime('now')
        """
    )


def register_release_migration() -> None:
    from . import migration_service

    if any(item.version == 4 for item in migration_service.MIGRATIONS):
        return
    migration = migration_service.Migration(
        4,
        "release_candidate_setup_state",
        "Extend application state with first-run payload, completion timestamp, and readiness timestamp.",
        apply_release_state_migration,
    )
    migration_service.MIGRATIONS = migration_service.MIGRATIONS + (migration,)
    migration_service.LATEST_SCHEMA_VERSION = 4
