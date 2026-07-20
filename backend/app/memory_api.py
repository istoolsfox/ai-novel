from typing import Any

from fastapi import APIRouter, Query

from .continuity_store import require_project
from .memory_store import (
    latest_foreshadowings,
    latest_item_ownership,
    latest_narrative_debts,
    latest_relationship_states,
    latest_story_facts,
    list_memory_compilations,
    memory_context,
)

router = APIRouter(prefix="/api/projects/{project_id}/memory", tags=["memory"])


@router.get("/context")
def get_memory_context(project_id: str) -> dict[str, Any]:
    require_project(project_id)
    return memory_context(project_id)


@router.get("/compilations")
def get_memory_compilations(project_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    return list_memory_compilations(project_id)


@router.get("/facts")
def get_story_facts(project_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    return latest_story_facts(project_id)


@router.get("/relationships")
def get_relationship_states(project_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    return latest_relationship_states(project_id)


@router.get("/items")
def get_item_ownership(project_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    return latest_item_ownership(project_id)


@router.get("/debts")
def get_narrative_debts(
    project_id: str,
    open_only: bool = Query(default=False),
) -> list[dict[str, Any]]:
    require_project(project_id)
    return latest_narrative_debts(project_id, open_only=open_only)


@router.get("/foreshadowings")
def get_foreshadowings(
    project_id: str,
    active_only: bool = Query(default=False),
) -> list[dict[str, Any]]:
    require_project(project_id)
    return latest_foreshadowings(project_id, active_only=active_only)
