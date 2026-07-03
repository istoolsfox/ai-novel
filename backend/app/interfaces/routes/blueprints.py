"""Routes: blueprint CRUD + auto-generation."""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ...application.blueprint_service import (
    approve_blueprint,
    create_project_blueprint,
    delete_project_blueprint,
    get_project_blueprint,
    list_project_blueprints,
    update_project_blueprint,
)
from ...infrastructure.database import connect, row_to_dict
from ...infrastructure.storage import require_project
from ...workflows.blueprint_generator import generate_blueprint

router = APIRouter(prefix="/api/projects/{project_id}/blueprints", tags=["blueprints"])


class BlueprintIn(BaseModel):
    volume_number: int = 1
    volume_title: str = ""
    volume_arc: str = ""
    chapter_range: dict[str, int] = {"start": 1, "end": 20}
    emotional_climate: dict[str, Any] = {}
    key_foreshadowings: list[dict[str, Any]] = []
    character_arcs: list[dict[str, Any]] = []
    recurring_motifs: list[str] = []
    taboo_list: list[str] = []
    generation_params: dict[str, Any] = {}


class AutoGenerateIn(BaseModel):
    volume_number: int = 1


@router.post("")
def create_blueprint_route(project_id: str, payload: BlueprintIn) -> dict[str, Any]:
    require_project(project_id)
    return create_project_blueprint(project_id, payload.model_dump())


@router.post("/auto-generate")
def auto_generate_blueprint_route(project_id: str, payload: AutoGenerateIn) -> dict[str, Any]:
    """AI-generate a complete blueprint for the given volume number."""
    require_project(project_id)
    with connect() as conn:
        project = row_to_dict(
            conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        )
    if not project:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found")

    blueprint_data = generate_blueprint(
        project_id=project_id,
        volume_number=payload.volume_number,
        project_data=project,
    )
    return create_project_blueprint(project_id, blueprint_data)


@router.get("")
def list_blueprints_route(project_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    return list_project_blueprints(project_id)


@router.get("/{blueprint_id}")
def get_blueprint_route(project_id: str, blueprint_id: str) -> dict[str, Any]:
    require_project(project_id)
    return get_project_blueprint(project_id, blueprint_id)


@router.patch("/{blueprint_id}")
def update_blueprint_route(project_id: str, blueprint_id: str, payload: BlueprintIn) -> dict[str, Any]:
    require_project(project_id)
    return update_project_blueprint(project_id, blueprint_id, payload.model_dump())


@router.delete("/{blueprint_id}")
def delete_blueprint_route(project_id: str, blueprint_id: str) -> dict[str, bool]:
    require_project(project_id)
    return delete_project_blueprint(project_id, blueprint_id)


@router.post("/{blueprint_id}/approve")
def approve_blueprint_route(project_id: str, blueprint_id: str) -> dict[str, Any]:
    require_project(project_id)
    return approve_blueprint(project_id, blueprint_id)
