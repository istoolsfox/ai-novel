"""接口层 · 章节路由。

章节 CRUD、版本管理、定稿。
"""
from typing import Any

from fastapi import APIRouter, HTTPException

from ...domain.models import ChapterIn, VersionIn
from ...infrastructure.database import connect, new_id, row_to_dict, rows_to_dicts, utc_now
from ...infrastructure.storage import project_root, require_project
from ..dependencies import require_chapter
from ...application.memory_service import (
    auto_generate_bridge,
    rebuild_volume_memory,
    sync_chapter_memory_to_wiki,
    volume_name_for_chapter,
    write_chapter_snapshot,
)

router = APIRouter(prefix="/api/projects/{project_id}/chapters", tags=["chapters"])


@router.post("")
def create_chapter(project_id: str, payload: ChapterIn) -> dict[str, Any]:
    require_project(project_id)
    chapter_id = new_id()
    now = utc_now()
    word_count = len(payload.draft)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO chapters (
                id, project_id, outline_id, chapter_number, title, brief, draft,
                summary, word_count, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chapter_id,
                project_id,
                payload.outline_id,
                payload.chapter_number,
                payload.title,
                payload.brief,
                payload.draft,
                payload.summary,
                word_count,
                payload.status,
                now,
                now,
            ),
        )
        chapter = row_to_dict(conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone())
    write_chapter_snapshot(project_id, chapter)
    return chapter


@router.get("")
def list_chapters(project_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM chapters WHERE project_id = ? ORDER BY chapter_number",
                (project_id,),
            ).fetchall()
        )


@router.get("/{chapter_id}")
def get_chapter(project_id: str, chapter_id: str) -> dict[str, Any]:
    return require_chapter(project_id, chapter_id)


@router.patch("/{chapter_id}")
def update_chapter(project_id: str, chapter_id: str, payload: ChapterIn) -> dict[str, Any]:
    require_chapter(project_id, chapter_id)
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            UPDATE chapters
            SET outline_id = ?, chapter_number = ?, title = ?, brief = ?, draft = ?,
                summary = ?, word_count = ?, status = ?, updated_at = ?
            WHERE id = ? AND project_id = ?
            """,
            (
                payload.outline_id,
                payload.chapter_number,
                payload.title,
                payload.brief,
                payload.draft,
                payload.summary,
                len(payload.draft),
                payload.status,
                now,
                chapter_id,
                project_id,
            ),
        )
        chapter = row_to_dict(conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone())
    write_chapter_snapshot(project_id, chapter)
    return chapter


@router.delete("/{chapter_id}")
def delete_chapter(project_id: str, chapter_id: str) -> dict[str, bool]:
    chapter = require_chapter(project_id, chapter_id)
    with connect() as conn:
        conn.execute("DELETE FROM chapter_versions WHERE project_id = ? AND chapter_id = ?", (project_id, chapter_id))
        conn.execute("DELETE FROM chapters WHERE id = ? AND project_id = ?", (chapter_id, project_id))
    try:
        snapshot = project_root(project_id) / "manuscript" / f"chapter-{int(chapter['chapter_number']):03}.md"
        if snapshot.exists():
            snapshot.unlink()
    except (OSError, TypeError, ValueError):
        pass
    return {"ok": True}


@router.post("/{chapter_id}/versions")
def create_chapter_version(project_id: str, chapter_id: str, payload: VersionIn) -> dict[str, Any]:
    require_chapter(project_id, chapter_id)
    version_id = new_id()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO chapter_versions (id, project_id, chapter_id, label, content, model, context_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (version_id, project_id, chapter_id, payload.label, payload.content, payload.model, payload.context_summary, now),
        )
        return row_to_dict(conn.execute("SELECT * FROM chapter_versions WHERE id = ?", (version_id,)).fetchone())


@router.get("/{chapter_id}/versions")
def list_chapter_versions(project_id: str, chapter_id: str) -> list[dict[str, Any]]:
    require_chapter(project_id, chapter_id)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM chapter_versions WHERE project_id = ? AND chapter_id = ? ORDER BY created_at DESC",
                (project_id, chapter_id),
            ).fetchall()
        )


@router.post("/{chapter_id}/versions/{version_id}/select")
def select_chapter_version(project_id: str, chapter_id: str, version_id: str) -> dict[str, Any]:
    require_chapter(project_id, chapter_id)
    with connect() as conn:
        version = row_to_dict(
            conn.execute(
                "SELECT * FROM chapter_versions WHERE id = ? AND project_id = ? AND chapter_id = ?",
                (version_id, project_id, chapter_id),
            ).fetchone()
        )
        if not version:
            raise HTTPException(status_code=404, detail="Version not found in chapter")
        conn.execute(
            """
            UPDATE chapters
            SET draft = ?, selected_version_id = ?, word_count = ?, updated_at = ?
            WHERE id = ? AND project_id = ?
            """,
            (version["content"], version_id, len(version["content"]), utc_now(), chapter_id, project_id),
        )
        chapter = row_to_dict(conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone())
    write_chapter_snapshot(project_id, chapter)
    return chapter


@router.post("/{chapter_id}/finalize")
def finalize_chapter(project_id: str, chapter_id: str) -> dict[str, Any]:
    chapter = require_chapter(project_id, chapter_id)
    summary = chapter["summary"] or chapter["brief"] or f"第 {chapter['chapter_number']} 章定稿：{chapter['draft'][:80]}"
    now = utc_now()
    with connect() as conn:
        conn.execute(
            "UPDATE chapters SET status = 'final', summary = ?, updated_at = ? WHERE id = ? AND project_id = ?",
            (summary, now, chapter_id, project_id),
        )
        memory_id = new_id()
        conn.execute(
            """
            INSERT INTO memory_items (id, project_id, title, category, content, payload, status, created_at, updated_at)
            VALUES (?, ?, ?, 'chapter_summary', ?, '{}', 'approved', ?, ?)
            """,
            (memory_id, project_id, f"第 {chapter['chapter_number']} 章摘要", summary, now, now),
        )
        updated = row_to_dict(conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone())
    sync_chapter_memory_to_wiki(project_id, updated)
    rebuild_volume_memory(project_id, volume_name_for_chapter(updated))
    # 自动生成章节衔接包（定稿后，供下一章承接）
    try:
        auto_generate_bridge(project_id, updated)
    except Exception:
        pass  # 衔接包生成失败不阻断定稿
    return updated
