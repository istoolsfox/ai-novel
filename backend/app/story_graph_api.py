from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .continuity_store import require_chapter, require_project
from .story_graph_store import (
    latest_story_edges,
    list_chapter_progress,
    list_recent_progress,
    list_story_nodes,
    list_story_threads,
    story_graph_context,
    upsert_manual_edge,
    upsert_manual_node,
    upsert_manual_thread,
)

router = APIRouter(prefix="/api/projects/{project_id}/story-graph", tags=["story-graph"])


class StoryThreadIn(BaseModel):
    thread_key: str = ""
    title: str
    thread_type: Literal[
        "main_plot",
        "character_arc",
        "romance",
        "mystery",
        "faction",
        "world_change",
        "foreshadowing",
        "theme",
        "subplot",
    ] = "subplot"
    status: Literal["active", "paused", "blocked", "resolved", "abandoned"] = "active"
    priority: float = Field(default=0.5, ge=0, le=1)
    current_stage: str = ""
    current_goal: str = ""
    next_target: str = ""
    stall_tolerance: int = Field(default=3, ge=1, le=50)


class StoryNodeIn(BaseModel):
    node_key: str = ""
    thread_key: str
    node_type: Literal[
        "event",
        "scene",
        "decision",
        "reveal",
        "conflict",
        "foreshadowing",
        "payoff",
        "turning_point",
        "goal",
        "obstacle",
    ] = "event"
    title: str
    description: str = ""
    status: Literal["planned", "active", "completed", "blocked", "cancelled"] = "planned"
    importance: float = Field(default=0.5, ge=0, le=1)
    planned_chapter: int = Field(default=0, ge=0)
    actual_chapter: int = Field(default=0, ge=0)


class StoryEdgeIn(BaseModel):
    edge_key: str = ""
    source_node_key: str
    target_node_key: str
    relation_type: Literal[
        "causes",
        "depends_on",
        "blocks",
        "reveals",
        "plants",
        "pays_off",
        "conflicts_with",
        "continues",
        "alternative_to",
    ] = "continues"
    status: Literal["active", "inactive", "cancelled"] = "active"
    weight: float = Field(default=1.0, ge=0, le=1)


@router.get("")
def get_story_graph(project_id: str, chapter_number: int | None = None):
    require_project(project_id)
    context = story_graph_context(project_id, current_chapter=chapter_number)
    all_threads = list_story_threads(project_id)
    all_nodes = list_story_nodes(project_id)
    all_edges = latest_story_edges(project_id)
    return {
        **context,
        "all_threads": all_threads,
        "all_nodes": all_nodes,
        "all_edges": all_edges,
        "recent_progress": list_recent_progress(project_id, limit=100),
        "stats": {
            "thread_count": len(all_threads),
            "node_count": len(all_nodes),
            "edge_count": len(all_edges),
            "stalled_thread_count": len(context["stalled_threads"]),
        },
    }


@router.get("/threads")
def get_threads(project_id: str, status: str = ""):
    require_project(project_id)
    return list_story_threads(project_id, status=status)


@router.post("/threads")
def save_thread(project_id: str, payload: StoryThreadIn):
    require_project(project_id)
    return upsert_manual_thread(project_id, payload.model_dump())


@router.get("/nodes")
def get_nodes(project_id: str, thread_key: str = "", status: str = ""):
    require_project(project_id)
    return list_story_nodes(project_id, thread=thread_key, status=status)


@router.post("/nodes")
def save_node(project_id: str, payload: StoryNodeIn):
    require_project(project_id)
    if not any(item["thread_key"] == payload.thread_key for item in list_story_threads(project_id)):
        raise HTTPException(status_code=400, detail="Story thread does not exist")
    return upsert_manual_node(project_id, payload.model_dump())


@router.get("/edges")
def get_edges(project_id: str):
    require_project(project_id)
    return latest_story_edges(project_id)


@router.post("/edges")
def save_edge(project_id: str, payload: StoryEdgeIn):
    require_project(project_id)
    node_keys = {item["node_key"] for item in list_story_nodes(project_id)}
    if payload.source_node_key not in node_keys or payload.target_node_key not in node_keys:
        raise HTTPException(status_code=400, detail="Both story nodes must exist")
    return upsert_manual_edge(project_id, payload.model_dump())


@router.get("/chapters/{chapter_id}/progress")
def get_chapter_story_progress(project_id: str, chapter_id: str):
    require_chapter(project_id, chapter_id)
    return list_chapter_progress(project_id, chapter_id)


@router.get("/focus")
def get_story_focus(project_id: str, chapter_number: int | None = None):
    require_project(project_id)
    context = story_graph_context(project_id, current_chapter=chapter_number)
    return {
        "story_focus": context["story_focus"],
        "stalled_threads": context["stalled_threads"],
    }
