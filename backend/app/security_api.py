import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .secret_store import (
    create_credential,
    delete_credential,
    get_credential,
    list_credentials,
    migrate_plaintext_model_configs,
    security_events,
    security_status,
    update_credential,
)
from .storage import require_project

router = APIRouter(prefix="/api/security", tags=["security"])


class CredentialCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    provider: str = Field(default="OpenAI", max_length=80)
    secret: str = Field(min_length=1, max_length=20_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CredentialUpdateIn(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    provider: str | None = Field(default=None, max_length=80)
    secret: str | None = Field(default=None, max_length=20_000)
    metadata: dict[str, Any] | None = None
    status: str | None = None


class CredentialTestIn(BaseModel):
    base_url: str = "https://api.openai.com/v1"
    model_name: str
    temperature: float = 0.1
    max_tokens: int = 16


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


@router.get("/status")
def get_security_status() -> dict[str, Any]:
    return security_status()


@router.get("/events")
def get_security_events(project_id: str = "", limit: int = 100) -> list[dict[str, Any]]:
    return security_events(project_id, limit)


@router.post("/migrate-plaintext-model-configs")
def migrate_legacy_credentials(
    authorization: str = Header(default=""),
    x_ai_novel_admin_token: str = Header(default=""),
) -> dict[str, int]:
    _require_admin(authorization, x_ai_novel_admin_token)
    return migrate_plaintext_model_configs()


@router.get("/projects/{project_id}/credentials")
def credentials(project_id: str) -> list[dict[str, Any]]:
    require_project(project_id)
    return list_credentials(project_id)


@router.post("/projects/{project_id}/credentials")
def create_project_credential(
    project_id: str,
    payload: CredentialCreateIn,
    authorization: str = Header(default=""),
    x_ai_novel_admin_token: str = Header(default=""),
) -> dict[str, Any]:
    _require_admin(authorization, x_ai_novel_admin_token)
    require_project(project_id)
    return _call(
        create_credential,
        project_id,
        name=payload.name,
        provider=payload.provider,
        secret=payload.secret,
        metadata=payload.metadata,
    )


@router.patch("/projects/{project_id}/credentials/{credential_id}")
def update_project_credential(
    project_id: str,
    credential_id: str,
    payload: CredentialUpdateIn,
    authorization: str = Header(default=""),
    x_ai_novel_admin_token: str = Header(default=""),
) -> dict[str, Any]:
    _require_admin(authorization, x_ai_novel_admin_token)
    require_project(project_id)
    return _call(
        update_credential,
        project_id,
        credential_id,
        name=payload.name,
        provider=payload.provider,
        secret=payload.secret,
        metadata=payload.metadata,
        status=payload.status,
    )


@router.delete("/projects/{project_id}/credentials/{credential_id}")
def delete_project_credential(
    project_id: str,
    credential_id: str,
    authorization: str = Header(default=""),
    x_ai_novel_admin_token: str = Header(default=""),
) -> dict[str, Any]:
    _require_admin(authorization, x_ai_novel_admin_token)
    require_project(project_id)
    return _call(delete_credential, project_id, credential_id)


@router.post("/projects/{project_id}/credentials/{credential_id}/test")
def test_project_credential(
    project_id: str,
    credential_id: str,
    payload: CredentialTestIn,
    authorization: str = Header(default=""),
    x_ai_novel_admin_token: str = Header(default=""),
) -> dict[str, Any]:
    _require_admin(authorization, x_ai_novel_admin_token)
    require_project(project_id)
    credential = _call(get_credential, project_id, credential_id, include_secret=True)
    from . import main

    return main.test_model_connection(
        project_id,
        main.ModelConnectionTestIn(
            provider=str(credential.get("provider") or "OpenAI"),
            api_key=str(credential.get("secret") or ""),
            base_url=payload.base_url,
            model_name=payload.model_name,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        ),
    )
