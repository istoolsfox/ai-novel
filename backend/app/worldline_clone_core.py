import json
import re
from pathlib import Path
from typing import Any

from .database import new_id, row_to_dict, rows_to_dicts, utc_now

STATIC_GENERIC_TABLES = (
    "model_configs",
    "model_task_routes",
    "characters",
    "character_relationships",
    "world_settings",
    "outlines",
    "style_profiles",
    "taboo_rules",
    "knowledge_documents",
    "prompt_templates",
)
DERIVED_GENERIC_TABLES = ("memory_items", "timeline_events", "foreshadowings")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _decode(value: Any) -> Any:
    if not isinstance(value, str) or not value:
        return value
    stripped = value.lstrip()
    if not stripped.startswith(("{", "[")):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _rewrite(value: Any, id_map: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _rewrite(item, id_map) for key, item in value.items()}
    if isinstance(value, list):
        return [_rewrite(item, id_map) for item in value]
    if isinstance(value, str):
        return id_map.get(value, value)
    return value


def _table_exists(conn, table: str) -> bool:
    return bool(
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
    )


def _columns(conn, table: str) -> list[str]:
    return [str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _insert_copy(
    conn,
    table: str,
    row: dict[str, Any],
    id_map: dict[str, str],
    *,
    overrides: dict[str, Any] | None = None,
    map_identity: bool = True,
) -> str:
    columns = _columns(conn, table)
    data = {key: row.get(key) for key in columns if key in row}
    old_id = str(data.get("id") or "")
    if "id" in columns:
        data["id"] = new_id()
    for key, value in list(data.items()):
        decoded = _decode(value)
        rewritten = _rewrite(decoded, id_map)
        data[key] = _json(rewritten) if decoded is not value and isinstance(rewritten, (dict, list)) else rewritten
    for key, value in (overrides or {}).items():
        if key in columns:
            data[key] = value
    names = list(data)
    placeholders = ", ".join("?" for _ in names)
    conn.execute(
        f"INSERT INTO {table} ({', '.join(names)}) VALUES ({placeholders})",
        tuple(data[name] for name in names),
    )
    new_identity = str(data.get("id") or "")
    if map_identity and old_id and new_identity:
        id_map[old_id] = new_identity
    return new_identity


def _number(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _row_mentions_future(row: dict[str, Any], fork_chapter: int) -> bool:
    candidates: list[int] = []
    for key in (
        "chapter_number",
        "source_chapter_number",
        "setup_chapter",
        "payoff_chapter",
        "deadline_chapter",
        "planned_chapter",
        "actual_chapter",
    ):
        if key in row:
            candidates.append(_number(row.get(key)))
    payload = _decode(row.get("payload"))
    if isinstance(payload, dict):
        for key in (
            "chapter_number",
            "source_chapter_number",
            "setup_chapter",
            "payoff_chapter",
            "deadline_chapter",
            "planned_chapter",
            "actual_chapter",
        ):
            if key in payload:
                candidates.append(_number(payload.get(key)))
    text = "\n".join(str(row.get(key) or "") for key in ("title", "content", "description"))
    candidates.extend(int(match) for match in re.findall(r"第\s*(\d+)\s*章", text))
    return any(number > fork_chapter for number in candidates if number > 0)


def _copy_project(conn, source_project_id: str, target_project_id: str, target_root: Path) -> dict[str, Any]:
    source = row_to_dict(conn.execute("SELECT * FROM projects WHERE id = ?", (source_project_id,)).fetchone())
    if not source:
        raise ValueError("Source project not found")
    now = utc_now()
    conn.execute(
        """
        INSERT INTO projects (
            id, title, topic, genre, audience, tone, target_chapter_count,
            target_words_per_chapter, logline, synopsis, global_summary, status,
            privacy_mode, project_root_path, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            target_project_id,
            source.get("title", ""),
            source.get("topic", ""),
            source.get("genre", ""),
            source.get("audience", ""),
            source.get("tone", ""),
            source.get("target_chapter_count", 0),
            source.get("target_words_per_chapter", 0),
            source.get("logline", ""),
            source.get("synopsis", ""),
            source.get("global_summary", ""),
            source.get("status", "draft"),
            source.get("privacy_mode", 1),
            str(target_root),
            now,
            now,
        ),
    )
    return source


def _copy_generic_tables(conn, source_project_id: str, target_project_id: str, fork_chapter: int, id_map: dict[str, str]) -> None:
    for table in STATIC_GENERIC_TABLES + DERIVED_GENERIC_TABLES:
        if not _table_exists(conn, table):
            continue
        rows = rows_to_dicts(
            conn.execute(
                f"SELECT * FROM {table} WHERE project_id = ? ORDER BY created_at",
                (source_project_id,),
            ).fetchall()
        )
        for row in rows:
            if table in DERIVED_GENERIC_TABLES and _row_mentions_future(row, fork_chapter):
                continue
            _insert_copy(conn, table, row, id_map, overrides={"project_id": target_project_id})


def _copy_chapters(conn, source_project_id: str, target_project_id: str, fork_chapter: int, id_map: dict[str, str]) -> list[dict[str, Any]]:
    chapters = rows_to_dicts(
        conn.execute(
            "SELECT * FROM chapters WHERE project_id = ? AND chapter_number <= ? ORDER BY chapter_number",
            (source_project_id, fork_chapter),
        ).fetchall()
    )
    for chapter in chapters:
        old_selected = str(chapter.get("selected_version_id") or "")
        new_chapter_id = _insert_copy(
            conn,
            "chapters",
            chapter,
            id_map,
            overrides={"project_id": target_project_id, "selected_version_id": ""},
        )
        chapter["_new_id"] = new_chapter_id
        chapter["_old_selected_version_id"] = old_selected
    return chapters


def _copy_versions_and_scores(conn, source_project_id: str, target_project_id: str, chapters: list[dict[str, Any]], id_map: dict[str, str]) -> None:
    chapter_ids = [str(chapter.get("id") or "") for chapter in chapters]
    if not chapter_ids:
        return
    placeholders = ",".join("?" for _ in chapter_ids)
    for table in ("chapter_versions", "chapter_scores"):
        rows = rows_to_dicts(
            conn.execute(
                f"SELECT * FROM {table} WHERE project_id = ? AND chapter_id IN ({placeholders}) ORDER BY created_at",
                (source_project_id, *chapter_ids),
            ).fetchall()
        )
        for row in rows:
            _insert_copy(conn, table, row, id_map, overrides={"project_id": target_project_id})
    for chapter in chapters:
        selected = id_map.get(str(chapter.get("_old_selected_version_id") or ""), "")
        if selected:
            conn.execute(
                "UPDATE chapters SET selected_version_id = ? WHERE id = ?",
                (selected, chapter["_new_id"]),
            )


def _copy_history_table(
    conn,
    table: str,
    source_project_id: str,
    target_project_id: str,
    fork_chapter: int,
    id_map: dict[str, str],
    *,
    chapter_number_column: str,
    chapter_id_column: str = "",
) -> None:
    if not _table_exists(conn, table):
        return
    rows = rows_to_dicts(
        conn.execute(f"SELECT * FROM {table} WHERE project_id = ?", (source_project_id,)).fetchall()
    )
    for row in rows:
        chapter_number = _number(row.get(chapter_number_column))
        if chapter_number > fork_chapter:
            continue
        if chapter_id_column:
            raw_id = str(row.get(chapter_id_column) or "")
            if chapter_number > 0 and raw_id and raw_id not in id_map:
                continue
        _insert_copy(conn, table, row, id_map, overrides={"project_id": target_project_id})
