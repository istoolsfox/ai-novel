from __future__ import annotations

from typing import Any

from ..infrastructure.database import connect, row_to_dict, rows_to_dicts
from .memory_service import (
    auto_generate_bridge,
    rebuild_bridge_index,
    rebuild_chapter_index,
    rebuild_volume_memory,
    sync_bridge_to_wiki,
    sync_chapter_full_to_wiki,
    volume_name_for_chapter,
    write_chapter_snapshot,
)


def rebuild_all_chapter_wiki(project_id: str, include_drafts: bool = False) -> dict[str, Any]:
    with connect() as conn:
        if include_drafts:
            rows = conn.execute(
                "SELECT * FROM chapters WHERE project_id = ? ORDER BY chapter_number",
                (project_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM chapters WHERE project_id = ? AND status = 'final' ORDER BY chapter_number",
                (project_id,),
            ).fetchall()
        chapters = rows_to_dicts(rows)

    synced_chapters = 0
    synced_bridges = 0
    errors: list[dict[str, Any]] = []
    for chapter in chapters:
        try:
            bridge = auto_generate_bridge(project_id, chapter) if chapter.get("draft") else None
            sync_chapter_full_to_wiki(project_id, chapter, bridge)
            write_chapter_snapshot(project_id, chapter)
            synced_chapters += 1
            if bridge:
                sync_bridge_to_wiki(project_id, chapter, bridge)
                synced_bridges += 1
        except Exception as exc:
            errors.append({
                "chapter_id": chapter.get("id", ""),
                "chapter_number": chapter.get("chapter_number", 0),
                "error": str(exc),
            })

    rebuild_chapter_index(project_id)
    rebuild_bridge_index(project_id)
    volume_page = rebuild_volume_memory(project_id, volume_name_for_chapter(chapters[0] if chapters else None))
    with connect() as conn:
        wiki_count = row_to_dict(
            conn.execute("SELECT COUNT(*) AS count FROM wiki_pages WHERE project_id = ?", (project_id,)).fetchone()
        ) or {"count": 0}
    return {
        "synced_chapters": synced_chapters,
        "synced_bridges": synced_bridges,
        "errors": errors,
        "wiki_page_count": int(wiki_count.get("count") or 0),
        "volume_memory_path": volume_page.get("path") if isinstance(volume_page, dict) else "关键记忆.md",
    }
