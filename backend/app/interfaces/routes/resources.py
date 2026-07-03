"""接口层 · 通用资源路由。

通用的结构化记录 CRUD（角色档案/关系/大纲/时间线/伏笔/雷点/知识库/风格等）。
这些资源共享 generic_* 表结构，通过 resource 参数路由到对应表。
"""
import json
from typing import Any

from fastapi import APIRouter, HTTPException

from ...domain.models import GenericIn
from ...infrastructure.database import connect, new_id, row_to_dict, rows_to_dicts, utc_now
from ...infrastructure.storage import require_project
from ...application.memory_service import (
    delete_record_from_wiki,
    sync_record_to_wiki,
    table_for_resource,
)

# 注意：这个路由的 prefix 需要精确匹配，避免和 wiki/chapters 等冲突
# 注册顺序：必须在 wiki/chapters/ai 等具体路由之后注册
router = APIRouter(prefix="/api/projects/{project_id}", tags=["resources"])


@router.get("/{resource}")
def list_generic(project_id: str, resource: str) -> list[dict[str, Any]]:
    require_project(project_id)
    table = table_for_resource(resource)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(f"SELECT * FROM {table} WHERE project_id = ? ORDER BY created_at DESC", (project_id,)).fetchall()
        )


@router.post("/{resource}")
def create_generic(project_id: str, resource: str, payload: GenericIn) -> dict[str, Any]:
    require_project(project_id)
    table = table_for_resource(resource)
    record_id = new_id()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            f"""
            INSERT INTO {table} (id, project_id, title, category, content, payload, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                project_id,
                payload.title,
                payload.category,
                payload.content,
                json.dumps(payload.payload, ensure_ascii=False),
                payload.status,
                now,
                now,
            ),
        )
        record = row_to_dict(conn.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,)).fetchone())
    sync_record_to_wiki(project_id, resource, record)
    return record


@router.patch("/{resource}/{record_id}")
def update_generic(project_id: str, resource: str, record_id: str, payload: GenericIn) -> dict[str, Any]:
    require_project(project_id)
    table = table_for_resource(resource)
    now = utc_now()
    with connect() as conn:
        existing = conn.execute(f"SELECT * FROM {table} WHERE id = ? AND project_id = ?", (record_id, project_id)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Record not found")
        conn.execute(
            f"""
            UPDATE {table}
            SET title = ?, category = ?, content = ?, payload = ?, status = ?, updated_at = ?
            WHERE id = ? AND project_id = ?
            """,
            (
                payload.title,
                payload.category,
                payload.content,
                json.dumps(payload.payload, ensure_ascii=False),
                payload.status,
                now,
                record_id,
                project_id,
            ),
        )
        record = row_to_dict(conn.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,)).fetchone())
    sync_record_to_wiki(project_id, resource, record)
    return record


@router.delete("/{resource}/{record_id}")
def delete_generic(project_id: str, resource: str, record_id: str) -> dict[str, bool]:
    require_project(project_id)
    table = table_for_resource(resource)
    with connect() as conn:
        record = row_to_dict(
            conn.execute(f"SELECT * FROM {table} WHERE id = ? AND project_id = ?", (record_id, project_id)).fetchone()
        )
        if not record:
            raise HTTPException(status_code=404, detail="Record not found in project")
        conn.execute(f"DELETE FROM {table} WHERE id = ? AND project_id = ?", (record_id, project_id))
    delete_record_from_wiki(project_id, resource, record)
    return {"ok": True}
