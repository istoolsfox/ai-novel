from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .worldline_store import (
    activate_worldline,
    archive_worldline,
    compare_worldlines,
    create_worldline,
    list_worldlines,
    promote_worldline,
    worldline_detail,
)

router = APIRouter(prefix="/api/projects/{project_id}/worldlines", tags=["worldlines"])


class ForkWorldlineIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    fork_chapter_number: int = Field(default=0, ge=0)
    description: str = Field(default="", max_length=500)


def _call(operation, *args, **kwargs):
    try:
        return operation(*args, **kwargs)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() or "不存在" in message else 409
        raise HTTPException(status_code=status, detail=message) from exc


@router.get("")
def get_worldlines(project_id: str) -> dict[str, Any]:
    return _call(list_worldlines, project_id)


@router.post("/fork")
def fork_worldline(project_id: str, payload: ForkWorldlineIn) -> dict[str, Any]:
    return _call(
        create_worldline,
        project_id,
        name=payload.name,
        fork_chapter_number=payload.fork_chapter_number,
        description=payload.description,
    )


@router.get("/compare/{left_worldline_id}/{right_worldline_id}")
def compare_two_worldlines(
    project_id: str,
    left_worldline_id: str,
    right_worldline_id: str,
) -> dict[str, Any]:
    return _call(compare_worldlines, project_id, left_worldline_id, right_worldline_id)


@router.get("/{worldline_id}")
def get_worldline(project_id: str, worldline_id: str) -> dict[str, Any]:
    return _call(worldline_detail, project_id, worldline_id)


@router.post("/{worldline_id}/activate")
def activate(project_id: str, worldline_id: str) -> dict[str, Any]:
    return _call(activate_worldline, project_id, worldline_id)


@router.post("/{worldline_id}/promote")
def promote(project_id: str, worldline_id: str) -> dict[str, Any]:
    return _call(promote_worldline, project_id, worldline_id)


@router.post("/{worldline_id}/archive")
def archive(project_id: str, worldline_id: str) -> dict[str, Any]:
    return _call(archive_worldline, project_id, worldline_id)
