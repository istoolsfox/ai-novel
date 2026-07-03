"""接口层 · 情感深度查询路由。

情感种子、考古记录、情感线索、意象生长、章节衔接包的查询接口。
"""
from typing import Any

from fastapi import APIRouter, HTTPException

from ...infrastructure.database import (
    get_archaeology,
    get_chapter_bridge,
    get_emotion_seed,
    get_emotional_lead,
    list_archaeology,
    list_chapter_bridges,
    list_emotional_leads,
    list_image_growth,
    update_emotional_lead,
)
from ...infrastructure.storage import require_project
from ..dependencies import require_chapter

router = APIRouter(prefix="/api/projects/{project_id}", tags=["emotion"])


# ===== 情感种子 =====
@router.get("/chapters/{chapter_id}/emotion-seed")
def get_chapter_emotion_seed(project_id: str, chapter_id: str) -> dict[str, Any]:
    require_project(project_id)
    require_chapter(project_id, chapter_id)
    seed = get_emotion_seed(project_id, chapter_id)
    return seed or {}


# ===== 情感考古 =====
@router.get("/chapters/{chapter_id}/archaeology")
def list_chapter_archaeology(project_id: str, chapter_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    require_chapter(project_id, chapter_id)
    return list_archaeology(project_id, chapter_id)


@router.get("/chapters/{chapter_id}/archaeology/{archaeology_id}")
def get_chapter_archaeology(project_id: str, chapter_id: str, archaeology_id: str) -> dict[str, Any]:
    require_project(project_id)
    require_chapter(project_id, chapter_id)
    arch = get_archaeology(project_id, archaeology_id)
    if not arch or arch.get("chapter_id") != chapter_id:
        raise HTTPException(status_code=404, detail="Archaeology record not found")
    return arch


# ===== 情感线索 =====
@router.get("/emotional-leads")
def list_project_emotional_leads(project_id: str, status: str = "") -> list[dict[str, Any]]:
    require_project(project_id)
    return list_emotional_leads(project_id, status)


@router.get("/emotional-leads/{lead_id}")
def get_project_emotional_lead(project_id: str, lead_id: str) -> dict[str, Any]:
    require_project(project_id)
    lead = get_emotional_lead(project_id, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Emotional lead not found")
    return lead


@router.patch("/emotional-leads/{lead_id}")
def update_project_emotional_lead(project_id: str, lead_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    require_project(project_id)
    lead = update_emotional_lead(project_id, lead_id, payload)
    if not lead:
        raise HTTPException(status_code=404, detail="Emotional lead not found")
    return lead


# ===== 意象生长 =====
@router.get("/image-growth")
def list_project_image_growth(project_id: str, image_name: str = "") -> list[dict[str, Any]]:
    require_project(project_id)
    return list_image_growth(project_id, image_name)


@router.get("/image-growth/{image_name}")
def get_project_image_growth(project_id: str, image_name: str) -> list[dict[str, Any]]:
    require_project(project_id)
    return list_image_growth(project_id, image_name)


# ===== 章节衔接包 =====
@router.get("/chapters/{chapter_id}/bridge")
def get_chapter_bridge_api(project_id: str, chapter_id: str) -> dict[str, Any]:
    require_project(project_id)
    require_chapter(project_id, chapter_id)
    bridge = get_chapter_bridge(project_id, chapter_id)
    return bridge or {}


@router.get("/bridges")
def list_project_bridges(project_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    return list_chapter_bridges(project_id)
