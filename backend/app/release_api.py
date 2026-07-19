import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .release_service import (
    complete_setup,
    release_info,
    release_readiness,
    reset_setup,
    setup_state,
    update_setup_state,
)

router = APIRouter(tags=["release"])


class SetupUpdateIn(BaseModel):
    setup_step: str = Field(default="welcome", max_length=50)
    payload: dict[str, Any] = Field(default_factory=dict)


class SetupCompleteIn(BaseModel):
    confirmation: str = ""
    acknowledge_without_model: bool = False


class SetupResetIn(BaseModel):
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
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/api/release/info")
def get_release_info() -> dict[str, Any]:
    return release_info()


@router.get("/api/release/readiness")
def get_release_readiness() -> dict[str, Any]:
    return release_readiness()


@router.get("/api/setup/state")
def get_setup_state() -> dict[str, Any]:
    return setup_state()


@router.put("/api/setup/state")
def save_setup_state(payload: SetupUpdateIn) -> dict[str, Any]:
    return update_setup_state(setup_step=payload.setup_step, payload=payload.payload)


@router.post("/api/setup/complete")
def finish_setup(
    payload: SetupCompleteIn,
    authorization: str = Header(default=""),
    x_ai_novel_admin_token: str = Header(default=""),
) -> dict[str, Any]:
    _require_admin(authorization, x_ai_novel_admin_token)
    return _call(
        complete_setup,
        confirmation=payload.confirmation,
        acknowledge_without_model=payload.acknowledge_without_model,
    )


@router.post("/api/setup/reset")
def restart_setup(
    payload: SetupResetIn,
    authorization: str = Header(default=""),
    x_ai_novel_admin_token: str = Header(default=""),
) -> dict[str, Any]:
    _require_admin(authorization, x_ai_novel_admin_token)
    return _call(reset_setup, confirmation=payload.confirmation)
