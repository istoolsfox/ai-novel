from .database import connect


def init_obsidian_schema() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS obsidian_exports (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL UNIQUE,
                worldline_id TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'completed',
                vault_path TEXT NOT NULL,
                archive_path TEXT DEFAULT '',
                content_hash TEXT NOT NULL,
                manifest TEXT DEFAULT '{}',
                file_count INTEGER DEFAULT 0,
                created_count INTEGER DEFAULT 0,
                updated_count INTEGER DEFAULT 0,
                unchanged_count INTEGER DEFAULT 0,
                deleted_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS obsidian_export_files (
                id TEXT PRIMARY KEY,
                export_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                size_bytes INTEGER DEFAULT 0,
                source_type TEXT DEFAULT '',
                source_key TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(export_id, relative_path)
            );

            CREATE INDEX IF NOT EXISTS idx_obsidian_export_files_project_path
            ON obsidian_export_files(project_id, relative_path);
            """
        )


def init_obsidian_cleanup_triggers() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TRIGGER IF NOT EXISTS cleanup_project_obsidian_export
            AFTER DELETE ON projects
            BEGIN
                DELETE FROM obsidian_export_files
                WHERE export_id IN (
                    SELECT id FROM obsidian_exports WHERE project_id = OLD.id
                );
                DELETE FROM obsidian_exports WHERE project_id = OLD.id;
            END;
            """
        )
