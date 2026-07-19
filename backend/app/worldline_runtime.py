def install_worldline_api() -> None:
    from . import main
    from .router_install import include_router_once, prioritize_prefix
    from .worldline_api import router

    include_router_once(
        main.app,
        router,
        marker_path="/api/projects/{project_id}/worldlines",
        marker_method="GET",
    )
    # The explicit worldline router must precede the legacy generic resource route.
    prioritize_prefix(main.app, "/api/projects/{project_id}/worldlines")
