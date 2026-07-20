from typing import Any

from .database import rows_to_dicts
from .worldline_clone_core import _copy_history_table, _insert_copy, _number, _table_exists


def _copy_continuity(conn, source_project_id: str, target_project_id: str, fork_chapter: int, id_map: dict[str, str]) -> None:
    for table, number_column, id_column in (
        ("chapter_bridges", "chapter_number", "chapter_id"),
        ("chapter_contracts", "chapter_number", "chapter_id"),
        ("continuity_checks", "chapter_number", "chapter_id"),
        ("character_states", "chapter_number", "chapter_id"),
        ("character_knowledge", "source_chapter_number", "source_chapter_id"),
    ):
        _copy_history_table(
            conn,
            table,
            source_project_id,
            target_project_id,
            fork_chapter,
            id_map,
            chapter_number_column=number_column,
            chapter_id_column=id_column,
        )


def _copy_layered_memory(conn, source_project_id: str, target_project_id: str, fork_chapter: int, id_map: dict[str, str]) -> None:
    _copy_history_table(
        conn,
        "memory_compilations",
        source_project_id,
        target_project_id,
        fork_chapter,
        id_map,
        chapter_number_column="chapter_number",
        chapter_id_column="chapter_id",
    )
    for table in (
        "story_facts",
        "relationship_states",
        "story_items",
        "item_ownership",
        "narrative_debts",
        "foreshadowing_states",
    ):
        _copy_history_table(
            conn,
            table,
            source_project_id,
            target_project_id,
            fork_chapter,
            id_map,
            chapter_number_column="source_chapter_number",
            chapter_id_column="source_chapter_id",
        )


def _copy_story_graph(conn, source_project_id: str, target_project_id: str, fork_chapter: int, id_map: dict[str, str]) -> None:
    _copy_history_table(
        conn,
        "story_graph_compilations",
        source_project_id,
        target_project_id,
        fork_chapter,
        id_map,
        chapter_number_column="chapter_number",
        chapter_id_column="chapter_id",
    )
    for table, number_column, id_column in (
        ("story_thread_states", "source_chapter_number", "source_chapter_id"),
        ("story_node_states", "source_chapter_number", "source_chapter_id"),
        ("story_edges", "source_chapter_number", "source_chapter_id"),
        ("chapter_story_progress", "chapter_number", "chapter_id"),
    ):
        _copy_history_table(
            conn,
            table,
            source_project_id,
            target_project_id,
            fork_chapter,
            id_map,
            chapter_number_column=number_column,
            chapter_id_column=id_column,
        )
    from .story_graph_store import refresh_story_node_cache, refresh_story_thread_cache

    refresh_story_thread_cache(conn, target_project_id)
    refresh_story_node_cache(conn, target_project_id)


def _copy_impact(conn, source_project_id: str, target_project_id: str, fork_chapter: int, id_map: dict[str, str]) -> None:
    _copy_history_table(
        conn,
        "impact_runs",
        source_project_id,
        target_project_id,
        fork_chapter,
        id_map,
        chapter_number_column="chapter_number",
        chapter_id_column="chapter_id",
    )
    _copy_history_table(
        conn,
        "impact_events",
        source_project_id,
        target_project_id,
        fork_chapter,
        id_map,
        chapter_number_column="chapter_number",
        chapter_id_column="chapter_id",
    )
    for table in ("impact_targets", "impact_observations"):
        if not _table_exists(conn, table):
            continue
        rows = rows_to_dicts(
            conn.execute(f"SELECT * FROM {table} WHERE project_id = ?", (source_project_id,)).fetchall()
        )
        for row in rows:
            raw_run_id = str(row.get("run_id") or "")
            if raw_run_id not in id_map:
                continue
            if table == "impact_observations" and _number(row.get("chapter_number")) > fork_chapter:
                continue
            _insert_copy(conn, table, row, id_map, overrides={"project_id": target_project_id})
