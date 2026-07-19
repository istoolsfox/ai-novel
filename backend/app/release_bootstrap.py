_BOOTSTRAPPED = False
_INSTALLED_APP_IDS: set[int] = set()


def bootstrap_release_candidate() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from . import database, main
    from .release_migration import register_release_migration
    from .release_service import setup_state

    register_release_migration()
    original_init_db = database.init_db

    def init_db_with_release() -> None:
        original_init_db()
        # Synchronize installed semantic version after migration 4 exists.
        setup_state()
        from .release_api import router

        app_id = id(main.app)
        if app_id not in _INSTALLED_APP_IDS:
            main.app.include_router(router)
            _INSTALLED_APP_IDS.add(app_id)

    database.init_db = init_db_with_release
    main.init_db = init_db_with_release
    _BOOTSTRAPPED = True
