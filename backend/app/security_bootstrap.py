import copy
from typing import Any

_BOOTSTRAPPED = False


def bootstrap_security_release() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from . import database, main
    from .secret_store import (
        create_credential,
        delete_credential,
        get_credential,
        migrate_plaintext_model_configs,
        update_credential,
    )
    from .security_api import router
    from .security_schema import init_security_schema

    original_init_db = database.init_db
    original_resolve_model_config = main.resolve_model_config
    original_create_generic = main.create_generic
    original_update_generic = main.update_generic
    original_delete_generic = main.delete_generic

    def resolve_model_config_with_credentials(project_id: str, workflow: str) -> dict[str, Any] | None:
        config = original_resolve_model_config(project_id, workflow)
        if not config:
            return config
        resolved = copy.deepcopy(config)
        payload = resolved.get("payload") if isinstance(resolved.get("payload"), dict) else {}
        credential_id = str(payload.get("credential_id") or "").strip()
        if credential_id:
            credential = get_credential(project_id, credential_id, include_secret=True)
            if credential.get("status") != "active":
                raise ValueError("Selected credential is disabled")
            payload["api_key"] = credential["secret"]
            payload["credential_hint"] = credential.get("secret_hint", "")
            resolved["payload"] = payload
        return resolved

    def _existing_model_payload(project_id: str, record_id: str) -> dict[str, Any]:
        if not record_id:
            return {}
        from .database import connect, row_to_dict

        with connect() as conn:
            row = row_to_dict(
                conn.execute(
                    "SELECT payload FROM model_configs WHERE project_id=? AND id=?",
                    (project_id, record_id),
                ).fetchone()
            )
        payload = row.get("payload") if isinstance(row, dict) else {}
        return payload if isinstance(payload, dict) else {}

    def _secure_model_payload(project_id: str, incoming: Any, record_id: str = "") -> Any:
        data = incoming.model_dump() if hasattr(incoming, "model_dump") else dict(incoming)
        payload = dict(data.get("payload") or {})
        api_key = str(payload.pop("api_key", "") or "").strip()
        existing_payload = _existing_model_payload(project_id, record_id)
        credential_id = str(payload.get("credential_id") or existing_payload.get("credential_id") or "").strip()
        name = str(data.get("title") or payload.get("model_name") or "模型") + " credential"
        provider = str(payload.get("provider") or data.get("category") or "OpenAI")

        if api_key:
            if credential_id:
                credential = update_credential(
                    project_id,
                    credential_id,
                    name=name,
                    provider=provider,
                    secret=api_key,
                    metadata={"model_config_id": record_id} if record_id else {},
                )
            else:
                try:
                    credential = create_credential(
                        project_id,
                        name=name,
                        provider=provider,
                        secret=api_key,
                        metadata={"model_config_id": record_id} if record_id else {},
                    )
                except ValueError:
                    from .secret_store import list_credentials

                    existing = next((item for item in list_credentials(project_id) if item.get("name") == name), None)
                    if not existing:
                        raise
                    credential = update_credential(project_id, existing["id"], provider=provider, secret=api_key)
            credential_id = str(credential["id"])
            payload["credential_hint"] = credential.get("secret_hint", "")
        elif credential_id:
            credential = get_credential(project_id, credential_id)
            payload["credential_hint"] = credential.get("secret_hint", "")

        payload["credential_id"] = credential_id
        payload["api_key"] = ""
        data["payload"] = payload
        return main.GenericIn(**data)

    def secure_create_generic(project_id: str, resource: str, payload: Any):
        secured = _secure_model_payload(project_id, payload) if resource == "model-configs" else payload
        return original_create_generic(project_id, resource, secured)

    def secure_update_generic(project_id: str, resource: str, record_id: str, payload: Any):
        secured = _secure_model_payload(project_id, payload, record_id) if resource == "model-configs" else payload
        return original_update_generic(project_id, resource, record_id, secured)

    def secure_delete_generic(project_id: str, resource: str, record_id: str):
        existing_payload = _existing_model_payload(project_id, record_id) if resource == "model-configs" else {}
        result = original_delete_generic(project_id, resource, record_id)
        credential_id = str(existing_payload.get("credential_id") or "")
        if credential_id:
            try:
                from .database import connect

                with connect() as conn:
                    remaining = int(
                        conn.execute(
                            "SELECT COUNT(*) FROM model_configs WHERE project_id=? AND payload LIKE ?",
                            (project_id, f'%"credential_id": "{credential_id}"%'),
                        ).fetchone()[0]
                    )
                if not remaining:
                    delete_credential(project_id, credential_id)
            except ValueError:
                pass
        return result

    def install_model_route_security() -> None:
        # Re-apply wrappers to the actual generic routes on every app init. This
        # is idempotent and avoids Python object-ID reuse across hot reloads.
        for route in main.app.routes:
            path = getattr(route, "path", "")
            methods = getattr(route, "methods", set()) or set()
            if path == "/api/projects/{project_id}/{resource}" and "POST" in methods:
                route.endpoint = secure_create_generic
                route.dependant.call = secure_create_generic
            elif path == "/api/projects/{project_id}/{resource}/{record_id}" and "PATCH" in methods:
                route.endpoint = secure_update_generic
                route.dependant.call = secure_update_generic
            elif path == "/api/projects/{project_id}/{resource}/{record_id}" and "DELETE" in methods:
                route.endpoint = secure_delete_generic
                route.dependant.call = secure_delete_generic

    def init_db_with_security() -> None:
        init_security_schema()
        original_init_db()
        init_security_schema()
        migrate_plaintext_model_configs()

        from .router_install import include_router_once

        main.resolve_model_config = resolve_model_config_with_credentials
        install_model_route_security()
        include_router_once(main.app, router, marker_path="/api/security/status", marker_method="GET")

    database.init_db = init_db_with_security
    main.init_db = init_db_with_security
    main.resolve_model_config = resolve_model_config_with_credentials
    install_model_route_security()
    _BOOTSTRAPPED = True
