"""接口层 · wiki 路由。

wiki 页面 CRUD、搜索、历史版本、lint、章节记忆重建。
"""
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...domain.models import WikiWriteIn
from ...infrastructure.database import connect, rows_to_dicts
from ...infrastructure.storage import require_project, safe_wiki_path
from ...application.memory_service import append_wiki_page, upsert_wiki_page
from ...application.wiki_rebuild_service import rebuild_all_chapter_wiki

router = APIRouter(prefix="/api/projects/{project_id}/wiki", tags=["wiki"])


class WikiRebuildIn(BaseModel):
    include_drafts: bool = False


@router.post("/write")
def wiki_write(project_id: str, payload: WikiWriteIn) -> dict[str, Any]:
    require_project(project_id)
    return upsert_wiki_page(project_id, payload.path, payload.content, payload.source_chapter_id)


@router.post("/append")
def wiki_append(project_id: str, payload: WikiWriteIn) -> dict[str, Any]:
    require_project(project_id)
    return append_wiki_page(project_id, payload.path, payload.content, payload.source_chapter_id)


@router.get("/read")
def wiki_read(project_id: str, path: str) -> dict[str, str]:
    require_project(project_id)
    target = safe_wiki_path(project_id, path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Wiki page not found")
    return {"path": path, "content": target.read_text(encoding="utf-8")}


@router.get("/search")
def wiki_search(project_id: str, q: str = "") -> list[dict[str, Any]]:
    require_project(project_id)
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM wiki_pages
            WHERE project_id = ? AND (path LIKE ? OR content LIKE ?)
            ORDER BY updated_at DESC
            """,
            (project_id, f"%{q}%", f"%{q}%"),
        ).fetchall()
        return rows_to_dicts(rows)


@router.get("/count")
def wiki_count(project_id: str) -> dict[str, int]:
    require_project(project_id)
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM wiki_pages WHERE project_id = ?", (project_id,)).fetchone()[0]
    return {"count": int(count)}


@router.post("/rebuild-chapter-memory")
def wiki_rebuild_chapter_memory(project_id: str, payload: WikiRebuildIn | None = None) -> dict[str, Any]:
    require_project(project_id)
    return rebuild_all_chapter_wiki(project_id, include_drafts=bool(payload and payload.include_drafts))


@router.get("/revisions")
def wiki_revisions(project_id: str, path: str) -> list[dict[str, Any]]:
    require_project(project_id)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM wiki_page_revisions WHERE project_id = ? AND path = ? ORDER BY created_at DESC",
                (project_id, path),
            ).fetchall()
        )


@router.get("/lint")
def wiki_lint(project_id: str) -> dict[str, Any]:
    require_project(project_id)
    with connect() as conn:
        pages = rows_to_dicts(conn.execute("SELECT * FROM wiki_pages WHERE project_id = ?", (project_id,)).fetchall())
    joined = " ".join(p.get("content") or "" for p in pages)
    orphan_pages = [page["path"] for page in pages if page["path"] != "index.md" and page["path"] not in joined]
    memory_warnings = []
    paths = {page.get("path") for page in pages}
    if "chapters/index.md" not in paths:
        memory_warnings.append("缺少章节全文索引 chapters/index.md")
    if "bridges/index.md" not in paths:
        memory_warnings.append("缺少章节衔接包索引 bridges/index.md")
    return {"orphan_pages": orphan_pages, "page_count": len(pages), "warnings": memory_warnings}
