import copy
from typing import Any

_BOOTSTRAPPED = False
_INSTALLED_APP_IDS: set[int] = set()


def bootstrap_security_release() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from . import database, main
    from .secret_store import get_credential, migrate_plaintext_model_configs
    from .security_api import router
    from .security_schema import init_security_schema

    original_init_db = database.init_db
    original_resolve_model_config = main.resolve_model_config

    def init_db_with_security() -> None:
        init_security_schema()
        original_init_db()
        init_security_schema()
        migrate_plaintext_model_configs()

        app_id = id(main.app)
        if app_id not in _INSTALLED_APP_IDS:
            main.app.include_router(router)
            _INSTALLED_APP_IDS.add(app_id)

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

    database.init_db = init_db_with_security
    main.resolve_model_config = resolve_model_config_with_credentials
    _BOOTSTRAPPED = True
