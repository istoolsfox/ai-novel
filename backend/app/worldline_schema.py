from .database import connect


def init_worldline_schema() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS worldline_roots (
                root_project_id TEXT PRIMARY KEY,
                primary_worldline_id TEXT NOT NULL,
                active_worldline_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS worldlines (
                id TEXT PRIMARY KEY,
                root_project_id TEXT NOT NULL,
                project_id TEXT NOT NULL UNIQUE,
                parent_worldline_id TEXT DEFAULT '',
                parent_project_id TEXT DEFAULT '',
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                fork_chapter_number INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                is_primary INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS worldline_snapshots (
                id TEXT PRIMARY KEY,
                worldline_id TEXT NOT NULL,
                source_worldline_id TEXT DEFAULT '',
                source_project_id TEXT DEFAULT '',
                fork_chapter_number INTEGER DEFAULT 0,
                manifest_hash TEXT NOT NULL,
                manifest TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(worldline_id)
            );

            CREATE TABLE IF NOT EXISTS worldline_events (
                id TEXT PRIMARY KEY,
                root_project_id TEXT NOT NULL,
                worldline_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source_worldline_id TEXT DEFAULT '',
                target_worldline_id TEXT DEFAULT '',
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_worldlines_root_status
            ON worldlines(root_project_id, status, created_at);

            CREATE INDEX IF NOT EXISTS idx_worldline_events_root_created
            ON worldline_events(root_project_id, created_at);
            """
        )


def init_worldline_cleanup_triggers() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TRIGGER IF NOT EXISTS cleanup_deleted_worldline_project
            AFTER DELETE ON projects
            BEGIN
                UPDATE worldline_roots
                SET active_worldline_id = primary_worldline_id,
                    updated_at = CURRENT_TIMESTAMP
                WHERE active_worldline_id IN (
                    SELECT id FROM worldlines WHERE project_id = OLD.id
                );
                DELETE FROM worldline_snapshots
                WHERE worldline_id IN (
                    SELECT id FROM worldlines WHERE project_id = OLD.id
                );
                DELETE FROM worldline_events
                WHERE worldline_id IN (
                    SELECT id FROM worldlines WHERE project_id = OLD.id
                );
                DELETE FROM worldlines WHERE project_id = OLD.id;
                DELETE FROM worldline_roots WHERE root_project_id = OLD.id;
            END;
            """
        )
