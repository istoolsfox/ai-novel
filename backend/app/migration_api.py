import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .key_rotation import key_rotation_history, restore_previous_master_key, rotate_master_key
from .migration_service import (
    apply_pending_migrations,
    migration_plan,
    migration_runs,
    migration_status,
    rollback_upgrade,
)

router = APIRouter(tags=["migrations"])


class MigrationApplyIn(BaseModel):
    confirmation: str = ""


class MigrationRollbackIn(BaseModel):
    confirmation: str = ""


class MasterKeyRotateIn(BaseModel):
    confirmation: str = ""
    new_master_key: str = Field(default="", max_length=500)


class MasterKeyRestoreIn(BaseModel):
    confirmation: str = ""


def _require_admin(authorization: str = Header(default=""), x_ai_novel_admin_token: str = Header(default="")) -> None:
    expected = os.getenv("AI_NOVEL_ADMIN_TOKEN", "").strip()
    if not expected:
        return
    bearer = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
    if x_ai_novel_admin_token != expected and bearer != expected:
        raise HTTPException(status_code=401, detail="Valid AI_NOVEL_ADMIN_TOKEN required")


def _call(operation, *args, **kwargs):
    try:
        return operation(*args, **kwargs)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 409
        raise HTTPException(status_code=status, detail=message) from exc


@router.get("/api/migrations/status")
def get_migration_status() -> dict[str, Any]:
    return migration_status()


@router.get("/api/migrations/plan")
def get_migration_plan() -> dict[str, Any]:
    return migration_plan()


@router.get("/api/migrations/runs")
def get_migration_runs(limit: int = 100) -> list[dict[str, Any]]:
    return migration_runs(limit)


@router.post("/api/migrations/apply")
def apply_migrations(
    payload: MigrationApplyIn,
    authorization: str = Header(default=""),
    x_ai_novel_admin_token: str = Header(default=""),
) -> dict[str, Any]:
    _require_admin(authorization, x_ai_novel_admin_token)
    return _call(apply_pending_migrations, confirmation=payload.confirmation)


@router.post("/api/migrations/rollback/{backup_id}")
def rollback_migrations(
    backup_id: str,
    payload: MigrationRollbackIn,
    authorization: str = Header(default=""),
    x_ai_novel_admin_token: str = Header(default=""),
) -> dict[str, Any]:
    _require_admin(authorization, x_ai_novel_admin_token)
    return _call(rollback_upgrade, backup_id, confirmation=payload.confirmation)


@router.get("/api/security/master-key/rotations")
def list_master_key_rotations(limit: int = 100) -> list[dict[str, Any]]:
    return key_rotation_history(limit)


@router.post("/api/security/master-key/rotate")
def rotate_security_master_key(
    payload: MasterKeyRotateIn,
    authorization: str = Header(default=""),
    x_ai_novel_admin_token: str = Header(default=""),
) -> dict[str, Any]:
    _require_admin(authorization, x_ai_novel_admin_token)
    return _call(
        rotate_master_key,
        confirmation=payload.confirmation,
        new_master_key=payload.new_master_key,
    )


@router.post("/api/security/master-key/rotations/{rotation_id}/restore")
def restore_security_master_key(
    rotation_id: str,
    payload: MasterKeyRestoreIn,
    authorization: str = Header(default=""),
    x_ai_novel_admin_token: str = Header(default=""),
) -> dict[str, Any]:
    _require_admin(authorization, x_ai_novel_admin_token)
    return _call(
        restore_previous_master_key,
        rotation_id,
        confirmation=payload.confirmation,
    )
