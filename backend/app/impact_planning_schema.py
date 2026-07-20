from .database import connect


def init_impact_planning_schema() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS impact_events (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                subject_type TEXT NOT NULL,
                subject_key TEXT NOT NULL,
                change_type TEXT DEFAULT '',
                magnitude REAL DEFAULT 0,
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(
                    project_id, chapter_id, event_type,
                    subject_type, subject_key, change_type
                )
            );

            CREATE TABLE IF NOT EXISTS impact_runs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                root_event_count INTEGER DEFAULT 0,
                max_depth INTEGER DEFAULT 3,
                threshold REAL DEFAULT 0.15,
                status TEXT DEFAULT 'completed',
                summary TEXT DEFAULT '',
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, chapter_id)
            );

            CREATE TABLE IF NOT EXISTS impact_targets (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_key TEXT NOT NULL,
                impact_score REAL DEFAULT 0,
                depth INTEGER DEFAULT 0,
                path TEXT DEFAULT '[]',
                reason TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(run_id, target_type, target_key)
            );

            CREATE TABLE IF NOT EXISTS impact_observations (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                observation_type TEXT NOT NULL,
                severity TEXT DEFAULT 'medium',
                subject_type TEXT DEFAULT '',
                subject_key TEXT DEFAULT '',
                message TEXT DEFAULT '',
                recommended_action TEXT DEFAULT '',
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rolling_plan_snapshots (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                source_chapter_id TEXT NOT NULL,
                source_chapter_number INTEGER NOT NULL,
                source_impact_run_id TEXT DEFAULT '',
                window_start INTEGER NOT NULL,
                window_end INTEGER NOT NULL,
                revision INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, source_chapter_id)
            );

            CREATE TABLE IF NOT EXISTS rolling_plan_items (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                status TEXT DEFAULT 'planned',
                locked INTEGER DEFAULT 0,
                primary_thread_key TEXT DEFAULT '',
                secondary_thread_keys TEXT DEFAULT '[]',
                target_node_keys TEXT DEFAULT '[]',
                goal TEXT DEFAULT '',
                must_address TEXT DEFAULT '[]',
                avoid TEXT DEFAULT '[]',
                risk_score REAL DEFAULT 0,
                source_snapshot_id TEXT NOT NULL,
                source_impact_run_id TEXT DEFAULT '',
                revision INTEGER DEFAULT 1,
                rationale TEXT DEFAULT '',
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, chapter_number)
            );

            CREATE TABLE IF NOT EXISTS rolling_plan_item_revisions (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                snapshot_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                action TEXT NOT NULL,
                previous_payload TEXT DEFAULT '{}',
                new_payload TEXT DEFAULT '{}',
                reason TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_impact_events_project_chapter
            ON impact_events(project_id, chapter_number, subject_type, subject_key);

            CREATE INDEX IF NOT EXISTS idx_impact_targets_run_score
            ON impact_targets(run_id, impact_score DESC);

            CREATE INDEX IF NOT EXISTS idx_impact_observations_project_chapter
            ON impact_observations(project_id, chapter_number, severity);

            CREATE INDEX IF NOT EXISTS idx_rolling_plan_items_project_chapter
            ON rolling_plan_items(project_id, chapter_number, status);

            CREATE INDEX IF NOT EXISTS idx_rolling_plan_revisions_project_chapter
            ON rolling_plan_item_revisions(project_id, chapter_number, revision);
            """
        )


def init_impact_planning_cleanup_triggers() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TRIGGER IF NOT EXISTS cleanup_chapter_impact_planning
            AFTER DELETE ON chapters
            BEGIN
                DELETE FROM impact_events WHERE chapter_id = OLD.id;
                DELETE FROM impact_observations WHERE chapter_id = OLD.id;
                DELETE FROM impact_targets
                WHERE run_id IN (SELECT id FROM impact_runs WHERE chapter_id = OLD.id);
                DELETE FROM impact_runs WHERE chapter_id = OLD.id;
                DELETE FROM rolling_plan_item_revisions
                WHERE snapshot_id IN (
                    SELECT id FROM rolling_plan_snapshots WHERE source_chapter_id = OLD.id
                );
                DELETE FROM rolling_plan_items
                WHERE source_snapshot_id IN (
                    SELECT id FROM rolling_plan_snapshots WHERE source_chapter_id = OLD.id
                );
                DELETE FROM rolling_plan_snapshots WHERE source_chapter_id = OLD.id;
            END;

            CREATE TRIGGER IF NOT EXISTS cleanup_project_impact_planning
            AFTER DELETE ON projects
            BEGIN
                DELETE FROM impact_events WHERE project_id = OLD.id;
                DELETE FROM impact_targets WHERE project_id = OLD.id;
                DELETE FROM impact_observations WHERE project_id = OLD.id;
                DELETE FROM impact_runs WHERE project_id = OLD.id;
                DELETE FROM rolling_plan_item_revisions WHERE project_id = OLD.id;
                DELETE FROM rolling_plan_items WHERE project_id = OLD.id;
                DELETE FROM rolling_plan_snapshots WHERE project_id = OLD.id;
            END;
            """
        )
