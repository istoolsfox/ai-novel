from typing import Any

from .database import connect, row_to_dict, rows_to_dicts
from .obsidian_render import latest_by, parse_json


def _table_exists(conn, table: str) -> bool:
    return bool(
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
    )


def _rows(conn, table: str, project_id: str, order_by: str = "created_at") -> list[dict[str, Any]]:
    if not _table_exists(conn, table):
        return []
    columns = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    order = order_by if order_by in columns else "rowid"
    return rows_to_dicts(
        conn.execute(
            f"SELECT * FROM {table} WHERE project_id = ? ORDER BY {order}",
            (project_id,),
        ).fetchall()
    )


def _worldline(project_id: str) -> dict[str, Any]:
    try:
        from .worldline_store import resolve_worldline, worldline_detail

        line = resolve_worldline(project_id)
        return worldline_detail(project_id, str(line["id"]))
    except (ImportError, ValueError, KeyError):
        return {
            "id": "",
            "project_id": project_id,
            "name": "主世界线",
            "description": "",
            "fork_chapter_number": 0,
            "is_primary": True,
            "is_active": True,
            "status": "active",
        }


def collect_obsidian_data(project_id: str, *, include_drafts: bool = True) -> dict[str, Any]:
    with connect() as conn:
        project = row_to_dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())
        if not project:
            raise ValueError("Project not found")
        chapter_sql = "SELECT * FROM chapters WHERE project_id = ?"
        params: list[Any] = [project_id]
        if not include_drafts:
            chapter_sql += " AND status = 'final'"
        chapter_sql += " ORDER BY chapter_number"
        chapters = rows_to_dicts(conn.execute(chapter_sql, tuple(params)).fetchall())
        data = {
            "project": project,
            "chapters": chapters,
            "character_profiles": _rows(conn, "characters", project_id),
            "character_states": _rows(conn, "character_states", project_id, "chapter_number"),
            "character_knowledge": _rows(conn, "character_knowledge", project_id, "source_chapter_number"),
            "relationship_states": _rows(conn, "relationship_states", project_id, "source_chapter_number"),
            "generic_relationships": _rows(conn, "character_relationships", project_id),
            "story_items": _rows(conn, "story_items", project_id, "source_chapter_number"),
            "item_ownership": _rows(conn, "item_ownership", project_id, "source_chapter_number"),
            "narrative_debts": _rows(conn, "narrative_debts", project_id, "source_chapter_number"),
            "foreshadowing_states": _rows(conn, "foreshadowing_states", project_id, "source_chapter_number"),
            "story_threads": _rows(conn, "story_threads", project_id, "priority"),
            "story_nodes": _rows(conn, "story_nodes", project_id, "planned_chapter"),
            "story_edges": _rows(conn, "story_edges", project_id, "source_chapter_number"),
            "chapter_story_progress": _rows(conn, "chapter_story_progress", project_id, "chapter_number"),
            "timeline_events": _rows(conn, "timeline_events", project_id),
            "chapter_bridges": _rows(conn, "chapter_bridges", project_id, "chapter_number"),
            "impact_runs": _rows(conn, "impact_runs", project_id, "chapter_number"),
            "impact_targets": _rows(conn, "impact_targets", project_id, "impact_score"),
            "impact_observations": _rows(conn, "impact_observations", project_id, "chapter_number"),
            "rolling_plan_items": _rows(conn, "rolling_plan_items", project_id, "chapter_number"),
        }

    data["worldline"] = _worldline(project_id)
    data["latest_character_states"] = latest_by(
        data["character_states"], ("character_key",), "chapter_number"
    )
    data["latest_character_knowledge"] = latest_by(
        data["character_knowledge"], ("character_key", "fact_key"), "source_chapter_number"
    )
    data["latest_relationship_states"] = latest_by(
        data["relationship_states"],
        ("source_character_key", "target_character_key", "relation_type"),
        "source_chapter_number",
    )
    data["latest_items"] = latest_by(data["story_items"], ("item_key",), "source_chapter_number")
    data["latest_ownership"] = latest_by(data["item_ownership"], ("item_key",), "source_chapter_number")
    data["latest_debts"] = latest_by(data["narrative_debts"], ("debt_key",), "source_chapter_number")
    data["latest_foreshadowings"] = latest_by(
        data["foreshadowing_states"], ("foreshadowing_key",), "source_chapter_number"
    )
    for bridge in data["chapter_bridges"]:
        bridge["payload"] = parse_json(bridge.get("payload"), {})
    for row in data["chapter_story_progress"]:
        row["source_node_keys"] = parse_json(row.get("source_node_keys"), [])
    for row in data["rolling_plan_items"]:
        for field in ("secondary_thread_keys", "target_node_keys", "must_address", "avoid"):
            row[field] = parse_json(row.get(field), [])
    for row in data["impact_targets"]:
        row["path"] = parse_json(row.get("path"), [])
    return data
