from typing import Any

_COMPILER_PATCHED = False
_CONTRACT_PATCHED = False


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


def install_story_graph_api() -> None:
    from . import main
    from .router_install import include_router_once, prioritize_prefix
    from .story_graph_api import router

    include_router_once(
        main.app,
        router,
        marker_path="/api/projects/{project_id}/story-graph",
        marker_method="GET",
    )
    # Explicit graph routes must precede the legacy generic resource endpoint.
    prioritize_prefix(main.app, "/api/projects/{project_id}/story-graph")
