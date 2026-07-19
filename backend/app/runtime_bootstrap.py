_BOOTSTRAPPED = False


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

        from .backup_scheduler import init_backup_schedule_schema
        from . import main
        from .router_install import include_router_once
        from .runtime_api import router

        init_backup_schedule_schema()
        include_router_once(main.app, router, marker_path="/api/runtime/health", marker_method="GET")

    database.init_db = init_db_with_runtime
    _BOOTSTRAPPED = True
