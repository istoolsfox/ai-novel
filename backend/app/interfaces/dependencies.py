"""接口层 · 依赖注入。

共享的辅助函数放这里，供多个路由模块复用。
"""
from typing import Any

from fastapi import HTTPException

from ..infrastructure.database import connect, row_to_dict
from ..infrastructure.storage import require_project


def require_chapter(project_id: str, chapter_id: str) -> dict[str, Any]:
    """校验章节存在并返回。不存在抛 404。"""
    require_project(project_id)
    with connect() as conn:
        chapter = row_to_dict(
            conn.execute(
                "SELECT * FROM chapters WHERE id = ? AND project_id = ?",
                (chapter_id, project_id),
            ).fetchone()
        )
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found in project")
    return chapter
