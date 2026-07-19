from typing import Any

from fastapi import APIRouter, HTTPException

from .continuity_store import (
    latest_character_knowledge,
    latest_character_states,
    latest_contract,
    require_chapter,
    require_project,
)
from .database import connect, row_to_dict, rows_to_dicts

router = APIRouter(prefix="/api/projects/{project_id}/continuity", tags=["continuity"])


@router.get("/chapters/{chapter_id}/contract")
def get_chapter_contract(project_id: str, chapter_id: str) -> dict[str, Any]:
    require_chapter(project_id, chapter_id)
    contract = latest_contract(project_id, chapter_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Chapter contract not found")
    return contract


@router.get("/chapters/{chapter_id}/bridge")
def get_chapter_bridge(project_id: str, chapter_id: str) -> dict[str, Any]:
    require_chapter(project_id, chapter_id)
    with connect() as conn:
        bridge = row_to_dict(
            conn.execute(
                "SELECT * FROM chapter_bridges WHERE project_id = ? AND chapter_id = ?",
                (project_id, chapter_id),
            ).fetchone()
        )
    if not bridge:
        raise HTTPException(status_code=404, detail="Chapter bridge not found")
    return bridge


@router.get("/chapters/{chapter_id}/checks")
def list_chapter_checks(project_id: str, chapter_id: str) -> list[dict[str, Any]]:
    require_chapter(project_id, chapter_id)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                """
                SELECT * FROM continuity_checks
                WHERE project_id = ? AND chapter_id = ?
                ORDER BY created_at DESC
                """,
                (project_id, chapter_id),
            ).fetchall()
        )


@router.get("/character-states")
def list_character_states(project_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    return latest_character_states(project_id)


@router.get("/character-knowledge")
def list_character_knowledge(project_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    return latest_character_knowledge(project_id)
