from .database import connect


def init_story_graph_schema() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS story_graph_compilations (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                payload TEXT DEFAULT '{}',
                status TEXT DEFAULT 'committed',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, chapter_id)
            );

            CREATE TABLE IF NOT EXISTS story_threads (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                thread_key TEXT NOT NULL,
                title TEXT DEFAULT '',
                thread_type TEXT DEFAULT 'subplot',
                status TEXT DEFAULT 'active',
                priority REAL DEFAULT 0,
                current_stage TEXT DEFAULT '',
                current_goal TEXT DEFAULT '',
                next_target TEXT DEFAULT '',
                stall_tolerance INTEGER DEFAULT 3,
                first_chapter INTEGER DEFAULT 0,
                last_progress_chapter INTEGER DEFAULT 0,
                last_source_chapter_id TEXT DEFAULT '',
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, thread_key)
            );

            CREATE TABLE IF NOT EXISTS story_thread_states (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                thread_key TEXT NOT NULL,
                title TEXT DEFAULT '',
                thread_type TEXT DEFAULT 'subplot',
                status TEXT DEFAULT 'active',
                priority REAL DEFAULT 0,
                current_stage TEXT DEFAULT '',
                current_goal TEXT DEFAULT '',
                next_target TEXT DEFAULT '',
                stall_tolerance INTEGER DEFAULT 3,
                source_chapter_id TEXT NOT NULL,
                source_chapter_number INTEGER NOT NULL,
                compilation_id TEXT NOT NULL,
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, thread_key, source_chapter_id)
            );

            CREATE TABLE IF NOT EXISTS story_nodes (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                node_key TEXT NOT NULL,
                thread_key TEXT NOT NULL,
                node_type TEXT DEFAULT 'event',
                title TEXT DEFAULT '',
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'planned',
                importance REAL DEFAULT 0,
                planned_chapter INTEGER DEFAULT 0,
                actual_chapter INTEGER DEFAULT 0,
                first_source_chapter_id TEXT DEFAULT '',
                last_source_chapter_id TEXT DEFAULT '',
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, node_key)
            );

            CREATE TABLE IF NOT EXISTS story_node_states (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                node_key TEXT NOT NULL,
                thread_key TEXT NOT NULL,
                node_type TEXT DEFAULT 'event',
                title TEXT DEFAULT '',
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'planned',
                importance REAL DEFAULT 0,
                planned_chapter INTEGER DEFAULT 0,
                actual_chapter INTEGER DEFAULT 0,
                source_chapter_id TEXT NOT NULL,
                source_chapter_number INTEGER NOT NULL,
                compilation_id TEXT NOT NULL,
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, node_key, source_chapter_id)
            );

            CREATE TABLE IF NOT EXISTS story_edges (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                edge_key TEXT NOT NULL,
                source_node_key TEXT NOT NULL,
                target_node_key TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                weight REAL DEFAULT 1,
                source_chapter_id TEXT NOT NULL,
                source_chapter_number INTEGER NOT NULL,
                compilation_id TEXT NOT NULL,
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, edge_key, source_chapter_id)
            );

            CREATE TABLE IF NOT EXISTS chapter_story_progress (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                thread_key TEXT NOT NULL,
                progress_type TEXT DEFAULT 'advanced',
                progress_summary TEXT DEFAULT '',
                before_stage TEXT DEFAULT '',
                after_stage TEXT DEFAULT '',
                progress_score REAL DEFAULT 0,
                source_node_keys TEXT DEFAULT '[]',
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, chapter_id, thread_key)
            );

            CREATE INDEX IF NOT EXISTS idx_story_threads_project_status
            ON story_threads(project_id, status, priority);

            CREATE INDEX IF NOT EXISTS idx_story_thread_states_project_key
            ON story_thread_states(project_id, thread_key, source_chapter_number);

            CREATE INDEX IF NOT EXISTS idx_story_nodes_project_thread
            ON story_nodes(project_id, thread_key, status, importance);

            CREATE INDEX IF NOT EXISTS idx_story_node_states_project_key
            ON story_node_states(project_id, node_key, source_chapter_number);

            CREATE INDEX IF NOT EXISTS idx_story_edges_project_source
            ON story_edges(project_id, source_node_key, target_node_key, source_chapter_number);

            CREATE INDEX IF NOT EXISTS idx_chapter_story_progress_project_chapter
            ON chapter_story_progress(project_id, chapter_number, thread_key);
            """
        )


def init_story_graph_cleanup_triggers() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TRIGGER IF NOT EXISTS cleanup_chapter_story_graph
            AFTER DELETE ON chapters
            BEGIN
                DELETE FROM story_graph_compilations WHERE chapter_id = OLD.id;
                DELETE FROM story_thread_states WHERE source_chapter_id = OLD.id;
                DELETE FROM story_node_states WHERE source_chapter_id = OLD.id;
                DELETE FROM story_edges WHERE source_chapter_id = OLD.id;
                DELETE FROM chapter_story_progress WHERE chapter_id = OLD.id;
            END;

            CREATE TRIGGER IF NOT EXISTS cleanup_project_story_graph
            AFTER DELETE ON projects
            BEGIN
                DELETE FROM story_graph_compilations WHERE project_id = OLD.id;
                DELETE FROM story_threads WHERE project_id = OLD.id;
                DELETE FROM story_thread_states WHERE project_id = OLD.id;
                DELETE FROM story_nodes WHERE project_id = OLD.id;
                DELETE FROM story_node_states WHERE project_id = OLD.id;
                DELETE FROM story_edges WHERE project_id = OLD.id;
                DELETE FROM chapter_story_progress WHERE project_id = OLD.id;
            END;
            """
        )
