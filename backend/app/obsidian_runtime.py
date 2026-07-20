_INSTALLED_APP_IDS: set[int] = set()


def _prioritize_obsidian_routes(app) -> None:
    prefix = "/api/projects/{project_id}/obsidian"
    routes = list(app.router.routes)
    obsidian_routes = [route for route in routes if str(getattr(route, "path", "")).startswith(prefix)]
    if not obsidian_routes:
        return
    remaining = [route for route in routes if route not in obsidian_routes]
    app.router.routes[:] = obsidian_routes + remaining


def install_obsidian_api() -> None:
    from . import main
    from .obsidian_api import router

    app_id = id(main.app)
    if app_id not in _INSTALLED_APP_IDS:
        main.app.include_router(router)
        _INSTALLED_APP_IDS.add(app_id)
    _prioritize_obsidian_routes(main.app)
