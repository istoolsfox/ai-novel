from typing import Any

LEGACY_GENERIC_PROJECT_PATHS = {
    "/api/projects/{project_id}/{resource}",
    "/api/projects/{project_id}/{resource}/{record_id}",
}


def has_route(app: Any, path: str, method: str | None = None) -> bool:
    expected_method = method.upper() if method else ""
    for route in getattr(app.router, "routes", []):
        if str(getattr(route, "path", "")) != path:
            continue
        methods = {str(item).upper() for item in (getattr(route, "methods", set()) or set())}
        if not expected_method or expected_method in methods:
            return True
    return False


def include_router_once(app: Any, router: Any, *, marker_path: str, marker_method: str = "GET") -> bool:
    """Include a router only when its real marker route is absent.

    Object IDs are not stable uniqueness tokens across repeated importlib reloads;
    Python can reuse an ID after an old FastAPI app is collected. Inspecting the
    actual route table prevents both skipped installation and duplicate routes.
    """
    if has_route(app, marker_path, marker_method):
        return False
    app.include_router(router)
    return True


def prioritize_prefix(app: Any, prefix: str) -> None:
    routes = list(getattr(app.router, "routes", []))
    preferred = [route for route in routes if str(getattr(route, "path", "")).startswith(prefix)]
    if not preferred:
        return
    remaining = [route for route in routes if route not in preferred]
    app.router.routes[:] = preferred + remaining


def move_legacy_generic_project_routes_last(app: Any) -> None:
    """Keep explicit project APIs ahead of the original generic CRUD fallback.

    The generic compatibility routes intentionally accept arbitrary resource
    names and therefore shadow exact endpoints such as `/story-graph` and
    `/worldlines` when they appear first. A final ordering pass after every
    module has installed its router makes behavior independent of bootstrap,
    hot-reload, and import order.
    """
    routes = list(getattr(app.router, "routes", []))
    generic = [route for route in routes if str(getattr(route, "path", "")) in LEGACY_GENERIC_PROJECT_PATHS]
    if not generic:
        return
    explicit = [route for route in routes if route not in generic]
    app.router.routes[:] = explicit + generic
