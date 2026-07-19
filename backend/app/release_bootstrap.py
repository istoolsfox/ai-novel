_BOOTSTRAPPED = False


def bootstrap_release_candidate() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from . import database, main
    from .release_migration import register_release_migration
    from .release_service import setup_state
    from .router_install import include_router_once

    register_release_migration()
    original_init_db = database.init_db

    def init_db_with_release() -> None:
        original_init_db()
        # Synchronize installed semantic version after migration 4 exists.
        setup_state()
        from .release_api import router

        include_router_once(main.app, router, marker_path="/api/release/info", marker_method="GET")

    database.init_db = init_db_with_release
    main.init_db = init_db_with_release
    _BOOTSTRAPPED = True
