"""接口层 · 认证路由。

本地 MVP 的 mock OAuth，后续可接入真实 Provider。
"""
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 本地 MVP 会话存储（进程级，重启丢失）
_AUTH_SESSION: dict[str, Any] | None = None
_OAUTH_PROVIDERS = {"openai", "github", "google", "custom"}


def _auth_status_payload() -> dict[str, Any]:
    if _AUTH_SESSION:
        return {
            "mode": "cloud",
            "authenticated": True,
            "user": _AUTH_SESSION,
            "sync_enabled": False,
            "message": "已登录。小说项目仍默认保存在本机，未主动同步不会上传正文。",
        }
    return {
        "mode": "local",
        "authenticated": False,
        "user": None,
        "sync_enabled": False,
        "message": "本地模式：无需登录即可完整使用项目、章节、记忆、导出和本地 API 配置。",
    }


def _normalize_oauth_provider(provider: str) -> str:
    normalized = provider.lower()
    if normalized not in _OAUTH_PROVIDERS:
        raise HTTPException(status_code=404, detail="Unsupported OAuth provider")
    return normalized


@router.get("/status")
def auth_status() -> dict[str, Any]:
    return _auth_status_payload()


@router.get("/oauth/{provider}/start")
def oauth_start(provider: str) -> dict[str, Any]:
    normalized = _normalize_oauth_provider(provider)
    return {
        "provider": normalized,
        "requires_redirect": False,
        "authorization_url": f"/api/auth/oauth/{normalized}/callback?code=mock-code",
        "state": "local-mvp-mock-state",
        "message": "本地 MVP 暂不跳转第三方授权；后续可在这里接入真实 OAuth Provider。",
        "available_providers": sorted(_OAUTH_PROVIDERS),
    }


@router.get("/oauth/{provider}/callback")
def oauth_callback(provider: str, code: str = "", state: str = "") -> dict[str, Any]:
    global _AUTH_SESSION
    normalized = _normalize_oauth_provider(provider)
    _AUTH_SESSION = {
        "id": f"mock-{normalized}-user",
        "provider": normalized,
        "name": "本地 OAuth 预览用户",
        "email": f"writer@{normalized}.local",
        "avatar_url": "",
    }
    return _auth_status_payload() | {"oauth_code_received": bool(code), "state": state}


@router.post("/logout")
def auth_logout() -> dict[str, Any]:
    global _AUTH_SESSION
    _AUTH_SESSION = None
    return _auth_status_payload()
