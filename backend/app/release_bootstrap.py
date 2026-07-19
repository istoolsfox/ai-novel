_BOOTSTRAPPED = False


def bootstrap_release_candidate() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from . import database, main
    from .release_migration import register_release_migration
    from .release_service import setup_state
    from .router_install import include_router_once, move_legacy_generic_project_routes_last

    register_release_migration()
    original_init_db = database.init_db

    def install_release_route_table() -> None:
        # Explicitly install every modular API after the complete wrapper chain.
        # Each installer is signature-idempotent, so this is safe on startup,
        # TestClient re-entry, and importlib hot reload.
        from .impact_planning_runtime import install_impact_planning_api
        from .memory_runtime import install_memory_api
        from .migration_api import router as migration_router
        from .obsidian_runtime import install_obsidian_api
        from .release_api import router as release_router
        from .runtime_api import router as runtime_router
        from .security_api import router as security_router
        from .story_graph_runtime import install_story_graph_api
        from .worldline_runtime import install_worldline_api

        install_memory_api()
        install_story_graph_api()
        install_impact_planning_api()
        install_worldline_api()
        install_obsidian_api()
        include_router_once(main.app, runtime_router, marker_path="/api/runtime/health", marker_method="GET")
        include_router_once(main.app, security_router, marker_path="/api/security/status", marker_method="GET")
        include_router_once(main.app, migration_router, marker_path="/api/migrations/status", marker_method="GET")
        include_router_once(main.app, release_router, marker_path="/api/release/info", marker_method="GET")
        move_legacy_generic_project_routes_last(main.app)

    def init_db_with_release() -> None:
        original_init_db()
        # Synchronize installed semantic version after migration 4 exists.
        setup_state()
        install_release_route_table()

    database.init_db = init_db_with_release
    main.init_db = init_db_with_release
    _BOOTSTRAPPED = True
