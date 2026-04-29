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
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for key in ("payload", "input_snapshot"):
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
