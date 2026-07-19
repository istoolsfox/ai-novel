from typing import Any

_COMPILER_PATCHED = False
_CONTRACT_PATCHED = False
_INSTALLED_APP_IDS: set[int] = set()


def patch_memory_compiler() -> None:
    global _COMPILER_PATCHED
    if _COMPILER_PATCHED:
        return

    from . import memory_compiler
    from .story_graph_compiler import (
        wrap_draft_prompt,
        wrap_layered_prompt,
        wrap_normalizer,
        wrap_persist_compiled_memory,
    )
    from .story_graph_store import story_graph_context

    base_memory_context = memory_compiler.memory_context

    def combined_memory_context(project_id: str) -> dict[str, Any]:
        context = base_memory_context(project_id)
        context.update(story_graph_context(project_id))
        return context

    memory_compiler.memory_context = combined_memory_context
    memory_compiler.layered_memory_prompt = wrap_layered_prompt(memory_compiler.layered_memory_prompt)
    memory_compiler.normalize_layered_memory = wrap_normalizer(memory_compiler.normalize_layered_memory)
    memory_compiler.persist_compiled_memory = wrap_persist_compiled_memory(memory_compiler.persist_compiled_memory)
    memory_compiler.enhanced_draft_prompt = wrap_draft_prompt(memory_compiler.enhanced_draft_prompt)
    _COMPILER_PATCHED = True


def patch_contract_runtime() -> None:
    global _CONTRACT_PATCHED
    if _CONTRACT_PATCHED:
        return

    from . import continuity_engine
    from .story_graph_store import story_graph_context

    base_build_contract = continuity_engine.build_chapter_contract

    def build_graph_contract(
        project_id: str,
        chapter_id: str,
        chapter_number: int,
    ) -> dict[str, Any]:
        result = base_build_contract(project_id, chapter_id, chapter_number)
        contract = result.get("structured") if isinstance(result.get("structured"), dict) else {}
        contract.update(story_graph_context(project_id, current_chapter=chapter_number))
        result["structured"] = contract
        result["text"] = continuity_engine.json_text(contract)
        return result

    continuity_engine.build_chapter_contract = build_graph_contract
    _CONTRACT_PATCHED = True


def _prioritize_story_graph_routes(app) -> None:
    """Move explicit story-graph routes before the legacy generic resource route.

    The original compatibility layer used an HTTP middleware to intercept the
    story-graph root path. Installing middleware from the FastAPI lifespan is
    invalid after Starlette has started. The router already exposes the exact
    root endpoint, so deterministic route ordering is sufficient and works in
    TestClient, Uvicorn, Docker, and hot reload without runtime middleware.
    """
    prefix = "/api/projects/{project_id}/story-graph"
    routes = list(app.router.routes)
    graph_routes = [route for route in routes if str(getattr(route, "path", "")).startswith(prefix)]
    if not graph_routes:
        return
    remaining = [route for route in routes if route not in graph_routes]
    app.router.routes[:] = graph_routes + remaining


def install_story_graph_api() -> None:
    from . import main
    from .story_graph_api import router

    app_id = id(main.app)
    if app_id not in _INSTALLED_APP_IDS:
        main.app.include_router(router)
        _INSTALLED_APP_IDS.add(app_id)
    _prioritize_story_graph_routes(main.app)
