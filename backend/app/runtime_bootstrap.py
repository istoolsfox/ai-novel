_BOOTSTRAPPED = False
_INSTALLED_APP_IDS: set[int] = set()


def bootstrap_runtime_reliability() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from . import database
    from .runtime_autopilot import install_external_autopilot_runtime
    from .runtime_schema import init_runtime_schema

    install_external_autopilot_runtime()
    original_init_db = database.init_db

    def init_db_with_runtime() -> None:
        # Create runtime-owned tables before the legacy bootstrap chain invokes recovery.
        init_runtime_schema()
        original_init_db()
        # Existing databases receive generation job lease columns after base tables exist.
        init_runtime_schema()

        from . import main
        from .runtime_api import router

        app_id = id(main.app)
        if app_id not in _INSTALLED_APP_IDS:
            main.app.include_router(router)
            _INSTALLED_APP_IDS.add(app_id)

    database.init_db = init_db_with_runtime
    _BOOTSTRAPPED = True
