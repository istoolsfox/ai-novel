from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .continuity_store import require_chapter, require_project
from .database import connect
from .impact_engine import (
    analyze_story_impact,
    impact_run_detail,
    latest_impact_run,
    list_impact_runs,
    persist_impact_analysis,
)
from .rolling_planner import (
    build_rolling_plan_proposal,
    get_plan_item,
    list_current_plan,
    list_plan_history,
    persist_rolling_plan,
    update_plan_lock,
)

impact_router = APIRouter(prefix="/api/projects/{project_id}/impact", tags=["impact"])
planning_router = APIRouter(prefix="/api/projects/{project_id}/planning", tags=["planning"])
router = APIRouter()
router.include_router(impact_router)
router.include_router(planning_router)


class ImpactEventIn(BaseModel):
    event_type: str = "manual.change"
    subject_type: str = "node"
    subject_key: str
    change_type: str = "changed"
    magnitude: float = Field(default=0.7, ge=0, le=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class ImpactAnalyzeIn(BaseModel):
    chapter_id: str
    chapter_number: int = Field(ge=0)
    max_depth: int = Field(default=3, ge=1, le=5)
    threshold: float = Field(default=0.15, ge=0.05, le=0.8)
    events: list[ImpactEventIn] = Field(default_factory=list)


class PlanningReconcileIn(BaseModel):
    source_chapter_id: str
    source_chapter_number: int = Field(ge=0)
    window_size: int = Field(default=5, ge=3, le=10)


class PlanLockIn(BaseModel):
    locked: bool = True


@impact_router.get("/runs")
def get_impact_runs(project_id: str, limit: int = 50) -> list[dict[str, Any]]:
    require_project(project_id)
    return list_impact_runs(project_id, limit)


@impact_router.get("/runs/{run_id}")
def get_impact_run(project_id: str, run_id: str) -> dict[str, Any]:
    require_project(project_id)
    detail = impact_run_detail(project_id, run_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Impact run not found")
    return detail


@impact_router.get("/chapters/{chapter_id}")
def get_chapter_impact(project_id: str, chapter_id: str) -> dict[str, Any]:
    require_chapter(project_id, chapter_id)
    run = latest_impact_run(project_id, chapter_id)
    if not run:
        raise HTTPException(status_code=404, detail="Chapter impact run not found")
    detail = impact_run_detail(project_id, str(run["id"]))
    if not detail:
        raise HTTPException(status_code=404, detail="Chapter impact run not found")
    return detail


@impact_router.post("/analyze")
def run_impact_analysis(project_id: str, payload: ImpactAnalyzeIn) -> dict[str, Any]:
    require_project(project_id)
    require_chapter(project_id, payload.chapter_id)
    analysis = analyze_story_impact(
        project_id,
        payload.chapter_id,
        payload.chapter_number,
        max_depth=payload.max_depth,
        threshold=payload.threshold,
        extra_events=[item.model_dump() for item in payload.events],
    )
    with connect() as conn:
        run_id = persist_impact_analysis(conn, analysis)
    detail = impact_run_detail(project_id, run_id)
    return detail or {"run_id": run_id, "analysis": analysis}


@planning_router.get("/current")
def get_current_plan(
    project_id: str,
    start_chapter: int = 0,
    end_chapter: int = 0,
) -> list[dict[str, Any]]:
    require_project(project_id)
    return list_current_plan(
        project_id,
        start_chapter=start_chapter,
        end_chapter=end_chapter,
    )


@planning_router.get("/history")
def get_plan_history(project_id: str, chapter_number: int = 0) -> list[dict[str, Any]]:
    require_project(project_id)
    return list_plan_history(project_id, chapter_number)


@planning_router.get("/chapters/{chapter_number}")
def get_chapter_plan(project_id: str, chapter_number: int) -> dict[str, Any]:
    require_project(project_id)
    item = get_plan_item(project_id, chapter_number)
    if not item:
        raise HTTPException(status_code=404, detail="Rolling plan item not found")
    return item


@planning_router.post("/chapters/{chapter_number}/lock")
def set_chapter_plan_lock(
    project_id: str,
    chapter_number: int,
    payload: PlanLockIn,
) -> dict[str, Any]:
    require_project(project_id)
    item = update_plan_lock(project_id, chapter_number, payload.locked)
    if not item:
        raise HTTPException(status_code=404, detail="Rolling plan item not found")
    return item


@planning_router.post("/reconcile")
def reconcile_plan(project_id: str, payload: PlanningReconcileIn) -> dict[str, Any]:
    require_project(project_id)
    require_chapter(project_id, payload.source_chapter_id)
    proposal = build_rolling_plan_proposal(
        project_id,
        payload.source_chapter_id,
        payload.source_chapter_number,
        window_size=payload.window_size,
    )
    with connect() as conn:
        snapshot_id = persist_rolling_plan(conn, proposal)
    return {
        "snapshot_id": snapshot_id,
        "proposal": proposal,
        "items": list_current_plan(
            project_id,
            start_chapter=int(proposal.get("window_start") or 0),
            end_chapter=int(proposal.get("window_end") or 0),
        ),
    }
