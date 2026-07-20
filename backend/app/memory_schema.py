from .database import connect


def init_memory_schema() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS memory_compilations (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                model TEXT DEFAULT '',
                content_hash TEXT NOT NULL,
                payload TEXT DEFAULT '{}',
                status TEXT DEFAULT 'committed',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, chapter_id)
            );

            CREATE TABLE IF NOT EXISTS story_facts (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                fact_key TEXT NOT NULL,
                fact_text TEXT DEFAULT '',
                fact_status TEXT DEFAULT 'confirmed',
                confidence REAL DEFAULT 0,
                source_chapter_id TEXT NOT NULL,
                source_chapter_number INTEGER NOT NULL,
                compilation_id TEXT NOT NULL,
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, fact_key, source_chapter_id)
            );

            CREATE TABLE IF NOT EXISTS relationship_states (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                source_character_key TEXT NOT NULL,
                source_character_id TEXT DEFAULT '',
                source_character_name TEXT DEFAULT '',
                target_character_key TEXT NOT NULL,
                target_character_id TEXT DEFAULT '',
                target_character_name TEXT DEFAULT '',
                relation_type TEXT NOT NULL,
                value REAL DEFAULT 0,
                status TEXT DEFAULT 'active',
                reason TEXT DEFAULT '',
                source_chapter_id TEXT NOT NULL,
                source_chapter_number INTEGER NOT NULL,
                compilation_id TEXT NOT NULL,
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(
                    project_id, source_character_key, target_character_key,
                    relation_type, source_chapter_id
                )
            );

            CREATE TABLE IF NOT EXISTS story_items (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                item_key TEXT NOT NULL,
                item_name TEXT DEFAULT '',
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                source_chapter_id TEXT NOT NULL,
                source_chapter_number INTEGER NOT NULL,
                compilation_id TEXT NOT NULL,
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, item_key, source_chapter_id)
            );

            CREATE TABLE IF NOT EXISTS item_ownership (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                item_key TEXT NOT NULL,
                item_name TEXT DEFAULT '',
                owner_type TEXT DEFAULT 'unknown',
                owner_key TEXT DEFAULT '',
                owner_name TEXT DEFAULT '',
                location TEXT DEFAULT '',
                status TEXT DEFAULT 'held',
                source_chapter_id TEXT NOT NULL,
                source_chapter_number INTEGER NOT NULL,
                compilation_id TEXT NOT NULL,
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, item_key, source_chapter_id)
            );

            CREATE TABLE IF NOT EXISTS narrative_debts (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                debt_key TEXT NOT NULL,
                debt_type TEXT DEFAULT 'open_question',
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'open',
                priority REAL DEFAULT 0,
                deadline_chapter INTEGER DEFAULT 0,
                source_chapter_id TEXT NOT NULL,
                source_chapter_number INTEGER NOT NULL,
                compilation_id TEXT NOT NULL,
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, debt_key, source_chapter_id)
            );

            CREATE TABLE IF NOT EXISTS foreshadowing_states (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                foreshadowing_key TEXT NOT NULL,
                title TEXT DEFAULT '',
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'planted',
                setup_chapter INTEGER DEFAULT 0,
                payoff_chapter INTEGER DEFAULT 0,
                priority REAL DEFAULT 0,
                source_chapter_id TEXT NOT NULL,
                source_chapter_number INTEGER NOT NULL,
                compilation_id TEXT NOT NULL,
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, foreshadowing_key, source_chapter_id)
            );

            CREATE INDEX IF NOT EXISTS idx_memory_compilations_project_chapter
            ON memory_compilations(project_id, chapter_number);

            CREATE INDEX IF NOT EXISTS idx_story_facts_project_key
            ON story_facts(project_id, fact_key, source_chapter_number);

            CREATE INDEX IF NOT EXISTS idx_relationship_states_project_pair
            ON relationship_states(
                project_id, source_character_key, target_character_key,
                relation_type, source_chapter_number
            );

            CREATE INDEX IF NOT EXISTS idx_item_ownership_project_item
            ON item_ownership(project_id, item_key, source_chapter_number);

            CREATE INDEX IF NOT EXISTS idx_narrative_debts_project_key
            ON narrative_debts(project_id, debt_key, source_chapter_number);

            CREATE INDEX IF NOT EXISTS idx_foreshadowing_states_project_key
            ON foreshadowing_states(project_id, foreshadowing_key, source_chapter_number);
            """
        )


def init_memory_cleanup_triggers() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TRIGGER IF NOT EXISTS cleanup_chapter_layered_memory
            AFTER DELETE ON chapters
            BEGIN
                DELETE FROM memory_compilations WHERE chapter_id = OLD.id;
                DELETE FROM story_facts WHERE source_chapter_id = OLD.id;
                DELETE FROM relationship_states WHERE source_chapter_id = OLD.id;
                DELETE FROM story_items WHERE source_chapter_id = OLD.id;
                DELETE FROM item_ownership WHERE source_chapter_id = OLD.id;
                DELETE FROM narrative_debts WHERE source_chapter_id = OLD.id;
                DELETE FROM foreshadowing_states WHERE source_chapter_id = OLD.id;
            END;

            CREATE TRIGGER IF NOT EXISTS cleanup_project_layered_memory
            AFTER DELETE ON projects
            BEGIN
                DELETE FROM memory_compilations WHERE project_id = OLD.id;
                DELETE FROM story_facts WHERE project_id = OLD.id;
                DELETE FROM relationship_states WHERE project_id = OLD.id;
                DELETE FROM story_items WHERE project_id = OLD.id;
                DELETE FROM item_ownership WHERE project_id = OLD.id;
                DELETE FROM narrative_debts WHERE project_id = OLD.id;
                DELETE FROM foreshadowing_states WHERE project_id = OLD.id;
            END;
            """
        )
