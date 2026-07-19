from pathlib import Path
from typing import Any

from .worldline_clone_core import (
    _copy_chapters,
    _copy_generic_tables,
    _copy_project,
    _copy_versions_and_scores,
)
from .worldline_clone_planning import (
    _copy_planning,
    _copy_wiki,
    _manifest,
    _write_project_files,
)
from .worldline_clone_state import (
    _copy_continuity,
    _copy_impact,
    _copy_layered_memory,
    _copy_story_graph,
)


def clone_project_at_fork(
    conn,
    source_project_id: str,
    target_project_id: str,
    target_root: Path,
    fork_chapter_number: int,
) -> tuple[dict[str, Any], str]:
    id_map = {source_project_id: target_project_id}
    _copy_project(conn, source_project_id, target_project_id, target_root)
    _copy_generic_tables(conn, source_project_id, target_project_id, fork_chapter_number, id_map)
    chapters = _copy_chapters(conn, source_project_id, target_project_id, fork_chapter_number, id_map)
    _copy_versions_and_scores(conn, source_project_id, target_project_id, chapters, id_map)
    _copy_continuity(conn, source_project_id, target_project_id, fork_chapter_number, id_map)
    _copy_layered_memory(conn, source_project_id, target_project_id, fork_chapter_number, id_map)
    _copy_story_graph(conn, source_project_id, target_project_id, fork_chapter_number, id_map)
    _copy_impact(conn, source_project_id, target_project_id, fork_chapter_number, id_map)
    _copy_planning(conn, source_project_id, target_project_id, fork_chapter_number, id_map)
    _copy_wiki(conn, source_project_id, target_project_id, fork_chapter_number, id_map)
    return _manifest(conn, target_project_id, fork_chapter_number)


def write_project_files(project_id: str) -> None:
    _write_project_files(project_id)
