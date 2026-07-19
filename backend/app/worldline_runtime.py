from urllib.parse import unquote

_INSTALLED_APP_IDS: set[int] = set()
_MIDDLEWARE_APP_IDS: set[int] = set()


def _prioritize_worldline_routes(app) -> None:
    prefix = "/api/projects/{project_id}/worldlines"
    routes = list(app.router.routes)
    worldline_routes = [route for route in routes if str(getattr(route, "path", "")).startswith(prefix)]
    if not worldline_routes:
        return
    remaining = [route for route in routes if route not in worldline_routes]
    app.router.routes[:] = worldline_routes + remaining


def _install_worldline_root_middleware(app) -> None:
    app_id = id(app)
    if app_id in _MIDDLEWARE_APP_IDS:
        return

    from fastapi import HTTPException
    from fastapi.responses import JSONResponse

    prefix = "/api/projects/"
    suffix = "/worldlines"

    @app.middleware("http")
    async def worldline_root_middleware(request, call_next):
        path = request.url.path.rstrip("/")
        if request.method == "GET" and path.startswith(prefix) and path.endswith(suffix):
            project_part = path[len(prefix) : -len(suffix)].strip("/")
            if project_part and "/" not in project_part:
                try:
                    from .worldline_store import list_worldlines

                    payload = list_worldlines(unquote(project_part))
                except HTTPException as exc:
                    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
                except ValueError as exc:
                    return JSONResponse(status_code=404, content={"detail": str(exc)})
                return JSONResponse(status_code=200, content=payload)
        return await call_next(request)

    _MIDDLEWARE_APP_IDS.add(app_id)


def install_worldline_api() -> None:
    from . import main
    from .worldline_api import router

    app_id = id(main.app)
    if app_id not in _INSTALLED_APP_IDS:
        main.app.include_router(router)
        _INSTALLED_APP_IDS.add(app_id)
    _prioritize_worldline_routes(main.app)
    _install_worldline_root_middleware(main.app)
