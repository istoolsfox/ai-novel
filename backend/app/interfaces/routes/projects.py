"""接口层 · 项目路由。

项目 CRUD：创建/列表/查询/更新/删除。
"""
import os
from typing import Any

from fastapi import APIRouter, HTTPException

from ...domain.models import DeleteProjectIn, ProjectIn
from ...infrastructure.database import connect, new_id, row_to_dict, rows_to_dicts, utc_now
from ...infrastructure.storage import ensure_project_dirs, require_project

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("")
def create_project(payload: ProjectIn) -> dict[str, Any]:
    project_id = new_id()
    root = ensure_project_dirs(project_id)
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO projects (
                id, title, topic, genre, audience, tone, target_chapter_count,
                target_words_per_chapter, logline, synopsis, global_summary, status,
                privacy_mode, project_root_path, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?)
            """,
            (
                project_id,
                payload.title,
                payload.topic,
                payload.genre,
                payload.audience,
                payload.tone,
                payload.target_chapter_count,
                payload.target_words_per_chapter,
                payload.logline,
                payload.synopsis,
                payload.global_summary,
                int(payload.privacy_mode),
                str(root),
                now,
                now,
            ),
        )
        project = row_to_dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())
    return project


@router.get("")
def list_projects() -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall())


@router.get("/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    return require_project(project_id)


@router.patch("/{project_id}")
def update_project(project_id: str, payload: ProjectIn) -> dict[str, Any]:
    require_project(project_id)
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            UPDATE projects
            SET title = ?, topic = ?, genre = ?, audience = ?, tone = ?,
                target_chapter_count = ?, target_words_per_chapter = ?,
                logline = ?, synopsis = ?, global_summary = ?, privacy_mode = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                payload.title,
                payload.topic,
                payload.genre,
                payload.audience,
                payload.tone,
                payload.target_chapter_count,
                payload.target_words_per_chapter,
                payload.logline,
                payload.synopsis,
                payload.global_summary,
                int(payload.privacy_mode),
                now,
                project_id,
            ),
        )
        return row_to_dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())


@router.delete("/{project_id}")
def delete_project(project_id: str, payload: DeleteProjectIn) -> dict[str, bool]:
    project = require_project(project_id)
    expected_password = os.getenv("AI_NOVEL_DELETE_PASSWORD") or project["title"]
    if payload.password != expected_password:
        raise HTTPException(status_code=403, detail="Delete password is incorrect")
    with connect() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    return {"ok": True}
