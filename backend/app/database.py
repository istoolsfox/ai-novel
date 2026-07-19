import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid4().hex


def database_path() -> Path:
    url = os.environ.get("AI_NOVEL_DATABASE_URL", "sqlite:///backend/app.db")
    if not url.startswith("sqlite:///"):
        raise RuntimeError("Only sqlite:/// database URLs are supported in the local MVP")
    return Path(url.removeprefix("sqlite:///")).resolve()


@contextmanager
def connect():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for key in ("payload", "input_snapshot", "output_snapshot"):
        if key in data and isinstance(data[key], str) and data[key]:
            try:
                data[key] = json.loads(data[key])
            except json.JSONDecodeError:
                pass
    return data


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [row_to_dict(row) for row in rows if row is not None]


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                topic TEXT DEFAULT '',
                genre TEXT DEFAULT '',
                audience TEXT DEFAULT '',
                tone TEXT DEFAULT '',
                target_chapter_count INTEGER DEFAULT 0,
                target_words_per_chapter INTEGER DEFAULT 0,
                logline TEXT DEFAULT '',
                synopsis TEXT DEFAULT '',
                global_summary TEXT DEFAULT '',
                status TEXT DEFAULT 'draft',
                privacy_mode INTEGER DEFAULT 1,
                project_root_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chapters (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                outline_id TEXT DEFAULT '',
                chapter_number INTEGER DEFAULT 1,
                title TEXT DEFAULT '',
                brief TEXT DEFAULT '',
                draft TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                word_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'draft',
                selected_version_id TEXT DEFAULT '',
                quality_score REAL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS chapter_versions (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                label TEXT DEFAULT '',
                content TEXT DEFAULT '',
                model TEXT DEFAULT '',
                context_summary TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(chapter_id) REFERENCES chapters(id)
            );

            CREATE TABLE IF NOT EXISTS chapter_scores (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                total_score REAL DEFAULT 0,
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS wiki_pages (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                path TEXT NOT NULL,
                title TEXT DEFAULT '',
                content TEXT DEFAULT '',
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, path)
            );

            CREATE TABLE IF NOT EXISTS wiki_page_revisions (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                path TEXT NOT NULL,
                content TEXT DEFAULT '',
                source_chapter_id TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ai_runs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                workflow TEXT NOT NULL,
                input_snapshot TEXT DEFAULT '{}',
                output_text TEXT DEFAULT '',
                model TEXT DEFAULT '',
                status TEXT DEFAULT 'success',
                error_message TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS generation_jobs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'full_autopilot',
                status TEXT NOT NULL DEFAULT 'queued',
                start_chapter INTEGER NOT NULL,
                end_chapter INTEGER NOT NULL,
                current_chapter INTEGER NOT NULL,
                current_step TEXT DEFAULT '',
                total_steps INTEGER NOT NULL DEFAULT 0,
                completed_steps INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 2,
                error_message TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT DEFAULT '',
                paused_at TEXT DEFAULT '',
                completed_at TEXT DEFAULT '',
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS generation_steps (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                step_order INTEGER NOT NULL,
                workflow TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempt_count INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 2,
                input_snapshot TEXT DEFAULT '{}',
                output_snapshot TEXT DEFAULT '{}',
                error_message TEXT DEFAULT '',
                started_at TEXT DEFAULT '',
                completed_at TEXT DEFAULT '',
                idempotency_key TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(job_id, idempotency_key),
                FOREIGN KEY(job_id) REFERENCES generation_jobs(id),
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(chapter_id) REFERENCES chapters(id)
            );

            CREATE TABLE IF NOT EXISTS generation_events (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT DEFAULT '',
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES generation_jobs(id),
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS chapter_contracts (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                previous_bridge_id TEXT DEFAULT '',
                payload TEXT DEFAULT '{}',
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, chapter_id),
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(chapter_id) REFERENCES chapters(id)
            );

            CREATE TABLE IF NOT EXISTS chapter_bridges (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                payload TEXT DEFAULT '{}',
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, chapter_id),
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(chapter_id) REFERENCES chapters(id)
            );

            CREATE TABLE IF NOT EXISTS continuity_checks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                stage TEXT NOT NULL DEFAULT 'initial',
                status TEXT NOT NULL DEFAULT 'warning',
                score REAL NOT NULL DEFAULT 0,
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(chapter_id) REFERENCES chapters(id)
            );

            CREATE TABLE IF NOT EXISTS character_states (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                character_key TEXT NOT NULL,
                character_id TEXT DEFAULT '',
                character_name TEXT DEFAULT '',
                chapter_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                location TEXT DEFAULT '',
                physical_state TEXT DEFAULT '',
                emotional_state TEXT DEFAULT '',
                current_goal TEXT DEFAULT '',
                alive_status TEXT DEFAULT 'alive',
                visibility_status TEXT DEFAULT 'public',
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, character_key, chapter_id),
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(chapter_id) REFERENCES chapters(id)
            );

            CREATE TABLE IF NOT EXISTS character_knowledge (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                character_key TEXT NOT NULL,
                character_id TEXT DEFAULT '',
                character_name TEXT DEFAULT '',
                fact_key TEXT NOT NULL,
                fact_text TEXT DEFAULT '',
                knowledge_status TEXT DEFAULT 'unknown',
                confidence REAL DEFAULT 0,
                source_chapter_id TEXT NOT NULL,
                source_chapter_number INTEGER NOT NULL,
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, character_key, fact_key, source_chapter_id),
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(source_chapter_id) REFERENCES chapters(id)
            );

            CREATE INDEX IF NOT EXISTS idx_generation_jobs_project_status
            ON generation_jobs(project_id, status, created_at);

            CREATE INDEX IF NOT EXISTS idx_generation_steps_job_status
            ON generation_steps(job_id, status, step_order);

            CREATE INDEX IF NOT EXISTS idx_generation_events_job_created
            ON generation_events(job_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_chapter_bridges_project_number
            ON chapter_bridges(project_id, chapter_number, status);

            CREATE INDEX IF NOT EXISTS idx_continuity_checks_chapter_stage
            ON continuity_checks(project_id, chapter_id, stage, created_at);

            CREATE INDEX IF NOT EXISTS idx_character_states_project_character
            ON character_states(project_id, character_key, chapter_number);

            CREATE INDEX IF NOT EXISTS idx_character_knowledge_project_character
            ON character_knowledge(project_id, character_key, fact_key, source_chapter_number);

            CREATE TRIGGER IF NOT EXISTS cleanup_chapter_continuity
            AFTER DELETE ON chapters
            BEGIN
                DELETE FROM chapter_contracts WHERE chapter_id = OLD.id;
                DELETE FROM chapter_bridges WHERE chapter_id = OLD.id;
                DELETE FROM continuity_checks WHERE chapter_id = OLD.id;
                DELETE FROM character_states WHERE chapter_id = OLD.id;
                DELETE FROM character_knowledge WHERE source_chapter_id = OLD.id;
            END;

            CREATE TRIGGER IF NOT EXISTS cleanup_project_continuity
            AFTER DELETE ON projects
            BEGIN
                DELETE FROM chapter_contracts WHERE project_id = OLD.id;
                DELETE FROM chapter_bridges WHERE project_id = OLD.id;
                DELETE FROM continuity_checks WHERE project_id = OLD.id;
                DELETE FROM character_states WHERE project_id = OLD.id;
                DELETE FROM character_knowledge WHERE project_id = OLD.id;
            END;
            """
        )

        for table in GENERIC_TABLES.values():
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    title TEXT DEFAULT '',
                    category TEXT DEFAULT '',
                    content TEXT DEFAULT '',
                    payload TEXT DEFAULT '{{}}',
                    status TEXT DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    from .continuity_engine import install_continuity

    install_continuity()


GENERIC_TABLES = {
    "model-configs": "model_configs",
    "model-task-routes": "model_task_routes",
    "character-profiles": "characters",
    "characters": "characters",
    "character-relationships": "character_relationships",
    "world-settings": "world_settings",
    "outlines": "outlines",
    "memory-items": "memory_items",
    "timeline-events": "timeline_events",
    "foreshadowings": "foreshadowings",
    "style-profiles": "style_profiles",
    "taboo-rules": "taboo_rules",
    "knowledge-documents": "knowledge_documents",
    "prompt-templates": "prompt_templates",
}
