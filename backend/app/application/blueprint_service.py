"""Application: blueprint service.

Use cases for volume blueprints: CRUD + approve.
"""
from typing import Any

from fastapi import HTTPException

from ..infrastructure.database import (
    create_blueprint,
    delete_blueprint,
    get_blueprint,
    list_blueprints,
    update_blueprint,
)


def create_project_blueprint(project_id: str, blueprint: dict[str, Any]) -> dict[str, Any]:
    return create_blueprint(project_id, blueprint)


def list_project_blueprints(project_id: str) -> list[dict[str, Any]]:
    return list_blueprints(project_id)


def get_project_blueprint(project_id: str, blueprint_id: str) -> dict[str, Any]:
    bp = get_blueprint(blueprint_id)
    if not bp or bp["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return bp


def update_project_blueprint(project_id: str, blueprint_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    get_project_blueprint(project_id, blueprint_id)  # validate ownership
    result = update_blueprint(blueprint_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return result


def delete_project_blueprint(project_id: str, blueprint_id: str) -> dict[str, bool]:
    get_project_blueprint(project_id, blueprint_id)  # validate ownership
    ok = delete_blueprint(blueprint_id)
    return {"ok": ok}


def approve_blueprint(project_id: str, blueprint_id: str) -> dict[str, Any]:
    """Approve a blueprint (status -> active)."""
    return update_project_blueprint(project_id, blueprint_id, {"status": "active"})
