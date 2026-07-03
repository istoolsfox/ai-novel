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
                source_chapter_id TEXT DEFAULT '',
                created_at TEXT NOT NULL,
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

            -- 情感深度增强 v2：情感种子（每章一条，写前生成）
            CREATE TABLE IF NOT EXISTS emotion_seeds (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                core_tension TEXT DEFAULT '',
                scene_temperature TEXT DEFAULT '',
                open_question TEXT DEFAULT '',
                payload TEXT DEFAULT '{}',
                status TEXT DEFAULT 'draft',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );

            -- 情感深度增强 v2：情感考古记录（每章可多条，每次考古一条）
            CREATE TABLE IF NOT EXISTS emotion_archaeology (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                hidden_layer_map TEXT DEFAULT '{}',
                view_mode TEXT DEFAULT 'triple',
                payload TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );

            -- 情感深度增强 v2：跨章情感线索（可回溯加深的线索）
            CREATE TABLE IF NOT EXISTS emotional_leads (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                discovered_in_chapter TEXT NOT NULL,
                lead_content TEXT NOT NULL,
                lead_type TEXT DEFAULT 'subconscious',
                source_chapters_can_deepen TEXT DEFAULT '[]',
                deepened_chapters TEXT DEFAULT '[]',
                status TEXT DEFAULT 'discovered',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );

            -- 情感深度增强 v2：意象生长记录（每意象每章一条）
            CREATE TABLE IF NOT EXISTS image_growth (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                image_name TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                chapter_number INTEGER DEFAULT 0,
                context TEXT DEFAULT '',
                felt_meaning_hint TEXT DEFAULT '',
                is_new INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );

            -- 章节衔接包（每章一条，定稿时生成，供下一章承接）
            CREATE TABLE IF NOT EXISTS chapter_bridges (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                chapter_number INTEGER DEFAULT 0,
                bridge_json TEXT DEFAULT '{}',
                ending_state TEXT DEFAULT '',
                open_hooks TEXT DEFAULT '[]',
                emotional_residue TEXT DEFAULT '[]',
                next_seeds TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS volume_blueprints (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                volume_number INTEGER DEFAULT 1,
                volume_title TEXT DEFAULT '',
                volume_arc TEXT DEFAULT '',
                chapter_range_start INTEGER DEFAULT 1,
                chapter_range_end INTEGER DEFAULT 20,
                blueprint_json TEXT DEFAULT '{}',
                status TEXT DEFAULT 'draft',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS generation_jobs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                volume_blueprint_id TEXT DEFAULT '',
                start_chapter_number INTEGER NOT NULL,
                target_chapter_count INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                current_chapter_number INTEGER DEFAULT 0,
                current_step TEXT DEFAULT '',
                checkpoint_strategy TEXT DEFAULT 'none',
                auto_finalize INTEGER DEFAULT 1,
                params_json TEXT DEFAULT '{}',
                pause_reason TEXT DEFAULT '',
                pause_detail TEXT DEFAULT '',
                error_message TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chapter_generation_steps (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                step_name TEXT NOT NULL,
                step_status TEXT DEFAULT 'pending',
                step_output TEXT DEFAULT '{}',
                started_at TEXT DEFAULT '',
                completed_at TEXT DEFAULT '',
                error_message TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS narrative_memory (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                source_chapter_id TEXT NOT NULL,
                memory_type TEXT DEFAULT '',
                memory_content TEXT DEFAULT '',
                injected_into_seeds TEXT DEFAULT '[]',
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS dialogue_maps (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                subtext_map TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reader_pull_reports (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                chapter_id TEXT NOT NULL,
                hook_strength INTEGER DEFAULT 0,
                emotional_debt TEXT DEFAULT '[]',
                pull_score INTEGER DEFAULT 0,
                report_json TEXT DEFAULT '{}',
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
        # 兼容旧数据库：给 wiki_pages 补 source_chapter_id / created_at 列
        _ensure_column(conn, "wiki_pages", "source_chapter_id", "TEXT DEFAULT ''")
        _ensure_column(conn, "wiki_pages", "created_at", "TEXT DEFAULT ''")
        # 兼容旧数据库：给 characters 补 voice_print 列（v4 情感深度增强）
        _ensure_column(conn, "characters", "voice_print", "TEXT DEFAULT '{}'")


def _ensure_column(conn, table: str, column: str, definition: str) -> None:
    """Add column if not exists (lightweight migration)."""
    cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


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


# ===== 情感深度增强 v2 CRUD =====


def create_emotion_seed(project_id: str, chapter_id: str, seed: dict[str, Any]) -> dict[str, Any]:
    seed_id = new_id()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """INSERT INTO emotion_seeds
               (id, project_id, chapter_id, core_tension, scene_temperature, open_question, payload, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                seed_id, project_id, chapter_id,
                seed.get("core_tension", ""),
                seed.get("scene_temperature", ""),
                seed.get("open_question", ""),
                json.dumps(seed, ensure_ascii=False),
                "draft", now, now,
            ),
        )
    return {"id": seed_id, "project_id": project_id, "chapter_id": chapter_id, **seed}


def get_emotion_seed(project_id: str, chapter_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM emotion_seeds WHERE project_id = ? AND chapter_id = ? ORDER BY updated_at DESC LIMIT 1",
            (project_id, chapter_id),
        ).fetchone()
    return row_to_dict(row)


def create_archaeology(project_id: str, chapter_id: str, hidden_layer_map: dict[str, Any], view_mode: str = "triple") -> dict[str, Any]:
    arch_id = new_id()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """INSERT INTO emotion_archaeology
               (id, project_id, chapter_id, hidden_layer_map, view_mode, payload, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (arch_id, project_id, chapter_id, json.dumps(hidden_layer_map, ensure_ascii=False), view_mode, "{}", now),
        )
    return {"id": arch_id, "project_id": project_id, "chapter_id": chapter_id, "hidden_layer_map": hidden_layer_map, "view_mode": view_mode}


def list_archaeology(project_id: str, chapter_id: str = "") -> list[dict[str, Any]]:
    with connect() as conn:
        if chapter_id:
            rows = conn.execute(
                "SELECT * FROM emotion_archaeology WHERE project_id = ? AND chapter_id = ? ORDER BY created_at DESC",
                (project_id, chapter_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM emotion_archaeology WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
    return rows_to_dicts(rows)


def get_archaeology(project_id: str, archaeology_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM emotion_archaeology WHERE id = ? AND project_id = ?",
            (archaeology_id, project_id),
        ).fetchone()
    return row_to_dict(row)


def create_emotional_lead(project_id: str, discovered_in_chapter: str, lead_content: str, lead_type: str = "subconscious", source_chapters: list[str] | None = None) -> dict[str, Any]:
    lead_id = new_id()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """INSERT INTO emotional_leads
               (id, project_id, discovered_in_chapter, lead_content, lead_type, source_chapters_can_deepen, deepened_chapters, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                lead_id, project_id, discovered_in_chapter, lead_content, lead_type,
                json.dumps(source_chapters or [], ensure_ascii=False),
                "[]", "discovered", now, now,
            ),
        )
    return {"id": lead_id, "project_id": project_id, "discovered_in_chapter": discovered_in_chapter, "lead_content": lead_content, "lead_type": lead_type}


def list_emotional_leads(project_id: str, status: str = "") -> list[dict[str, Any]]:
    with connect() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM emotional_leads WHERE project_id = ? AND status = ? ORDER BY created_at DESC",
                (project_id, status),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM emotional_leads WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
    return rows_to_dicts(rows)


def get_emotional_lead(project_id: str, lead_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM emotional_leads WHERE id = ? AND project_id = ?",
            (lead_id, project_id),
        ).fetchone()
    return row_to_dict(row)


def update_emotional_lead(project_id: str, lead_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    now = utc_now()
    fields = []
    values: list[Any] = []
    for key in ("status", "lead_content", "lead_type"):
        if key in updates:
            fields.append(f"{key} = ?")
            values.append(updates[key])
    if "deepened_chapters" in updates:
        fields.append("deepened_chapters = ?")
        values.append(json.dumps(updates["deepened_chapters"], ensure_ascii=False))
    if not fields:
        return get_emotional_lead(project_id, lead_id)
    fields.append("updated_at = ?")
    values.extend([now, lead_id, project_id])
    with connect() as conn:
        conn.execute(
            f"UPDATE emotional_leads SET {', '.join(fields)} WHERE id = ? AND project_id = ?",
            values,
        )
    return get_emotional_lead(project_id, lead_id)


def create_image_growth(project_id: str, image_name: str, chapter_id: str, chapter_number: int, context: str, felt_meaning_hint: str = "", is_new: bool = True) -> dict[str, Any]:
    img_id = new_id()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """INSERT INTO image_growth
               (id, project_id, image_name, chapter_id, chapter_number, context, felt_meaning_hint, is_new, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (img_id, project_id, image_name, chapter_id, chapter_number, context, felt_meaning_hint, 1 if is_new else 0, now),
        )
    return {"id": img_id, "project_id": project_id, "image_name": image_name, "chapter_id": chapter_id, "chapter_number": chapter_number, "context": context, "felt_meaning_hint": felt_meaning_hint, "is_new": is_new}


def list_image_growth(project_id: str, image_name: str = "") -> list[dict[str, Any]]:
    with connect() as conn:
        if image_name:
            rows = conn.execute(
                "SELECT * FROM image_growth WHERE project_id = ? AND image_name = ? ORDER BY chapter_number ASC, created_at ASC",
                (project_id, image_name),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM image_growth WHERE project_id = ? ORDER BY chapter_number ASC, created_at ASC",
                (project_id,),
            ).fetchall()
    return rows_to_dicts(rows)


# ===== 章节衔接包 ChapterBridge =====


def create_chapter_bridge(project_id: str, chapter_id: str, chapter_number: int, bridge: dict[str, Any]) -> dict[str, Any]:
    bridge_id = new_id()
    now = utc_now()
    ending_state = bridge.get("ending_state", {})
    ending_state_str = ending_state_str = json.dumps(ending_state, ensure_ascii=False) if isinstance(ending_state, dict) else str(ending_state)
    with connect() as conn:
        # 一章只保留一个最新衔接包，先删旧的
        conn.execute(
            "DELETE FROM chapter_bridges WHERE project_id = ? AND chapter_id = ?",
            (project_id, chapter_id),
        )
        conn.execute(
            """INSERT INTO chapter_bridges
               (id, project_id, chapter_id, chapter_number, bridge_json, ending_state, open_hooks, emotional_residue, next_seeds, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                bridge_id, project_id, chapter_id, chapter_number,
                json.dumps(bridge, ensure_ascii=False),
                ending_state_str,
                json.dumps(bridge.get("open_hooks", []), ensure_ascii=False),
                json.dumps(bridge.get("emotional_residue", []), ensure_ascii=False),
                json.dumps(bridge.get("next_chapter_seeds", []), ensure_ascii=False),
                now, now,
            ),
        )
    return {"id": bridge_id, "project_id": project_id, "chapter_id": chapter_id, "chapter_number": chapter_number, **bridge}


def get_chapter_bridge(project_id: str, chapter_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM chapter_bridges WHERE project_id = ? AND chapter_id = ? ORDER BY updated_at DESC LIMIT 1",
            (project_id, chapter_id),
        ).fetchone()
    return row_to_dict(row)


def get_previous_chapter_bridge(project_id: str, before_chapter_number: int) -> dict[str, Any] | None:
    """获取指定章节号之前最近一章的衔接包（用于生成下一章时承接）"""
    with connect() as conn:
        row = conn.execute(
            """SELECT * FROM chapter_bridges
               WHERE project_id = ? AND chapter_number < ?
               ORDER BY chapter_number DESC LIMIT 1""",
            (project_id, before_chapter_number),
        ).fetchone()
    return row_to_dict(row)


def list_chapter_bridges(project_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM chapter_bridges WHERE project_id = ? ORDER BY chapter_number ASC",
            (project_id,),
        ).fetchall()
    return rows_to_dicts(rows)


# ===========================================================================
# Phase 1：蓝图 / 任务 / 步骤 / 叙事记忆 CRUD
# ===========================================================================


# ----- 蓝图 -----
def create_blueprint(project_id: str, blueprint: dict[str, Any]) -> dict[str, Any]:
    blueprint_id = new_id()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """INSERT INTO volume_blueprints
               (id, project_id, volume_number, volume_title, volume_arc,
                chapter_range_start, chapter_range_end, blueprint_json, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                blueprint_id, project_id,
                int(blueprint.get("volume_number", 1)),
                blueprint.get("volume_title", ""),
                blueprint.get("volume_arc", ""),
                int(blueprint.get("chapter_range", {}).get("start", 1)),
                int(blueprint.get("chapter_range", {}).get("end", 20)),
                json.dumps(blueprint, ensure_ascii=False),
                blueprint.get("status", "draft"),
                now, now,
            ),
        )
        return row_to_dict(conn.execute("SELECT * FROM volume_blueprints WHERE id = ?", (blueprint_id,)).fetchone())


def list_blueprints(project_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(
            conn.execute("SELECT * FROM volume_blueprints WHERE project_id = ? ORDER BY volume_number", (project_id,)).fetchall()
        )


def get_blueprint(blueprint_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        return row_to_dict(conn.execute("SELECT * FROM volume_blueprints WHERE id = ?", (blueprint_id,)).fetchone())


def update_blueprint(blueprint_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    now = utc_now()
    with connect() as conn:
        existing = row_to_dict(conn.execute("SELECT * FROM volume_blueprints WHERE id = ?", (blueprint_id,)).fetchone())
        if not existing:
            return None
        # 合并 blueprint_json
        existing_json = existing.get("blueprint_json", "{}")
        if isinstance(existing_json, str):
            try:
                existing_json = json.loads(existing_json)
            except json.JSONDecodeError:
                existing_json = {}
        if isinstance(existing_json, dict):
            existing_json.update(updates)
        conn.execute(
            """UPDATE volume_blueprints
               SET volume_title = ?, volume_arc = ?, chapter_range_start = ?, chapter_range_end = ?,
                   blueprint_json = ?, status = ?, updated_at = ?
               WHERE id = ?""",
            (
                updates.get("volume_title", existing.get("volume_title", "")),
                updates.get("volume_arc", existing.get("volume_arc", "")),
                int(updates.get("chapter_range", {}).get("start", existing.get("chapter_range_start", 1))),
                int(updates.get("chapter_range", {}).get("end", existing.get("chapter_range_end", 20))),
                json.dumps(existing_json, ensure_ascii=False),
                updates.get("status", existing.get("status", "draft")),
                now,
                blueprint_id,
            ),
        )
        return row_to_dict(conn.execute("SELECT * FROM volume_blueprints WHERE id = ?", (blueprint_id,)).fetchone())


def delete_blueprint(blueprint_id: str) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM volume_blueprints WHERE id = ?", (blueprint_id,))
        return cur.rowcount > 0


# ----- 任务 -----
def create_job(project_id: str, job: dict[str, Any]) -> dict[str, Any]:
    job_id = new_id()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """INSERT INTO generation_jobs
               (id, project_id, volume_blueprint_id, start_chapter_number, target_chapter_count,
                status, current_chapter_number, current_step, checkpoint_strategy, auto_finalize,
                params_json, pause_reason, pause_detail, error_message, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'pending', 0, '', ?, ?, ?, '', '', '', ?, ?)""",
            (
                job_id, project_id,
                job.get("volume_blueprint_id", ""),
                int(job.get("start_chapter_number", 1)),
                int(job.get("target_chapter_count", 1)),
                job.get("checkpoint_strategy", "none"),
                int(job.get("auto_finalize", 1)),
                json.dumps(job.get("params", {}), ensure_ascii=False),
                now, now,
            ),
        )
        return row_to_dict(conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job_id,)).fetchone())


def get_job(job_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        return row_to_dict(conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job_id,)).fetchone())


def list_jobs(project_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(
            conn.execute("SELECT * FROM generation_jobs WHERE project_id = ? ORDER BY created_at DESC", (project_id,)).fetchall()
        )


def update_job_status(job_id: str, status: str, **fields: Any) -> dict[str, Any] | None:
    now = utc_now()
    sets = ["status = ?", "updated_at = ?"]
    vals: list[Any] = [status, now]
    for k, v in fields.items():
        sets.append(f"{k} = ?")
        vals.append(v)
    vals.append(job_id)
    with connect() as conn:
        conn.execute(f"UPDATE generation_jobs SET {', '.join(sets)} WHERE id = ?", vals)
        return row_to_dict(conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job_id,)).fetchone())


def get_active_jobs(project_id: str) -> list[dict[str, Any]]:
    """获取运行中/暂停/检查点的任务（用于并发控制）。"""
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM generation_jobs WHERE project_id = ? AND status IN ('running', 'paused', 'checkpoint')",
                (project_id,),
            ).fetchall()
        )


# ----- 步骤 -----
def create_step(job_id: str, project_id: str, chapter_id: str, chapter_number: int, step_name: str) -> dict[str, Any]:
    step_id = new_id()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """INSERT INTO chapter_generation_steps
               (id, job_id, project_id, chapter_id, chapter_number, step_name, step_status, step_output, started_at, completed_at, error_message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'pending', '{}', '', '', '', ?)""",
            (step_id, job_id, project_id, chapter_id, chapter_number, step_name, now),
        )
        return row_to_dict(conn.execute("SELECT * FROM chapter_generation_steps WHERE id = ?", (step_id,)).fetchone())


def update_step(step_id: str, status: str, output: dict[str, Any] | None = None, error: str = "") -> None:
    now = utc_now()
    sets = ["step_status = ?"]
    vals: list[Any] = [status]
    if status == "running":
        sets.append("started_at = ?")
        vals.append(now)
    elif status in ("completed", "failed", "skipped"):
        sets.append("completed_at = ?")
        vals.append(now)
    if output is not None:
        sets.append("step_output = ?")
        vals.append(json.dumps(output, ensure_ascii=False))
    if error:
        sets.append("error_message = ?")
        vals.append(error)
    vals.append(step_id)
    with connect() as conn:
        conn.execute(f"UPDATE chapter_generation_steps SET {', '.join(sets)} WHERE id = ?", vals)


def list_steps(job_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM chapter_generation_steps WHERE job_id = ? ORDER BY created_at, chapter_number",
                (job_id,),
            ).fetchall()
        )


def get_chapter_steps(job_id: str, chapter_number: int) -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM chapter_generation_steps WHERE job_id = ? AND chapter_number = ? ORDER BY created_at",
                (job_id, chapter_number),
            ).fetchall()
        )


# ----- 叙事记忆 -----
def insert_narrative_memory(project_id: str, source_chapter_id: str, memory_type: str, memory_content: str) -> dict[str, Any]:
    memory_id = new_id()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """INSERT INTO narrative_memory (id, project_id, source_chapter_id, memory_type, memory_content, injected_into_seeds, status, created_at)
               VALUES (?, ?, ?, ?, ?, '[]', 'active', ?)""",
            (memory_id, project_id, source_chapter_id, memory_type, memory_content, now),
        )
        return row_to_dict(conn.execute("SELECT * FROM narrative_memory WHERE id = ?", (memory_id,)).fetchone())


def get_active_narrative_memory(project_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM narrative_memory WHERE project_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 10",
                (project_id,),
            ).fetchall()
        )


# ----- 对话地图 -----
def create_dialogue_map(project_id: str, chapter_id: str, subtext_map: dict[str, Any]) -> dict[str, Any]:
    map_id = new_id()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """INSERT INTO dialogue_maps (id, project_id, chapter_id, subtext_map, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (map_id, project_id, chapter_id, json.dumps(subtext_map, ensure_ascii=False), now),
        )
        return row_to_dict(conn.execute("SELECT * FROM dialogue_maps WHERE id = ?", (map_id,)).fetchone())


# ----- 追读力报告 -----
def create_reader_pull_report(project_id: str, chapter_id: str, report: dict[str, Any]) -> dict[str, Any]:
    report_id = new_id()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """INSERT INTO reader_pull_reports
               (id, project_id, chapter_id, hook_strength, emotional_debt, pull_score, report_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report_id, project_id, chapter_id,
                int(report.get("hook_strength", 0)),
                json.dumps(report.get("emotional_debt", []), ensure_ascii=False),
                int(report.get("pull_score", 0)),
                json.dumps(report, ensure_ascii=False),
                now,
            ),
        )
        return row_to_dict(conn.execute("SELECT * FROM reader_pull_reports WHERE id = ?", (report_id,)).fetchone())


def create_chapter_quality_score(project_id: str, chapter_id: str, report: dict[str, Any]) -> dict[str, Any]:
    score_id = new_id()
    now = utc_now()
    total_score = float(report.get("total_score", 0))
    with connect() as conn:
        conn.execute(
            """INSERT INTO chapter_scores (id, project_id, chapter_id, total_score, payload, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (score_id, project_id, chapter_id, total_score, json.dumps(report, ensure_ascii=False), now),
        )
        conn.execute(
            "UPDATE chapters SET quality_score = ?, updated_at = ? WHERE id = ?",
            (total_score, now, chapter_id),
        )
        return row_to_dict(conn.execute("SELECT * FROM chapter_scores WHERE id = ?", (score_id,)).fetchone())


def get_recent_reader_pull_reports(project_id: str, count: int = 3) -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM reader_pull_reports WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                (project_id, count),
            ).fetchall()
        )
