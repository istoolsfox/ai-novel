def install_obsidian_api() -> None:
    from . import main
    from .obsidian_api import router
    from .router_install import include_router_once, prioritize_prefix

    include_router_once(
        main.app,
        router,
        marker_path="/api/projects/{project_id}/obsidian/status",
        marker_method="GET",
    )
    prioritize_prefix(main.app, "/api/projects/{project_id}/obsidian")
