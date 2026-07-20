import os

_BOOTSTRAPPED = False
_INSTALLED_APP_IDS: set[int] = set()


def bootstrap_migrations_upgrade() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from . import database, main
    from .key_rotation import init_key_rotation_schema
    from .migration_service import auto_apply_migrations, init_migration_schema
    from .migration_api import router

    original_init_db = database.init_db

    def init_db_with_migrations() -> None:
        original_init_db()
        init_migration_schema()
        init_key_rotation_schema()

        # Existing tests create many isolated databases and explicitly exercise
        # migration behavior. Avoid creating an upgrade snapshot for every
        # unrelated test while keeping production startup hands-free.
        default_auto = "0" if os.getenv("PYTEST_CURRENT_TEST") else "1"
        enabled = os.getenv("AI_NOVEL_AUTO_MIGRATE", default_auto).lower() not in {"0", "false", "no"}
        if enabled:
            auto_apply_migrations()

        app_id = id(main.app)
        if app_id not in _INSTALLED_APP_IDS:
            main.app.include_router(router)
            _INSTALLED_APP_IDS.add(app_id)

    database.init_db = init_db_with_migrations
    main.init_db = init_db_with_migrations
    _BOOTSTRAPPED = True
