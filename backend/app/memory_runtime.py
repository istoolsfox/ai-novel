from typing import Any

_PATCHED = False


def patch_continuity_runtime() -> None:
    global _PATCHED
    if _PATCHED:
        return

    from . import continuity_engine
    from .memory_compiler import compile_chapter_memory, enhanced_draft_prompt, persist_compiled_memory
    from .memory_store import memory_context

    base_build_contract = continuity_engine.build_chapter_contract

    def build_layered_contract(
        project_id: str,
        chapter_id: str,
        chapter_number: int,
    ) -> dict[str, Any]:
        result = base_build_contract(project_id, chapter_id, chapter_number)
        contract = result.get("structured") if isinstance(result.get("structured"), dict) else {}
        contract.update(memory_context(project_id))
        result["structured"] = contract
        result["text"] = continuity_engine.json_text(contract)
        return result

    base_apply = continuity_engine.continuity_apply_step_result

    def apply_layered_result(conn, job_id: str, step: dict[str, Any], result: dict[str, Any]) -> None:
        if str(step.get("workflow") or "") == "compile_chapter_memory":
            memory = result.get("structured") if isinstance(result.get("structured"), dict) else {}
            persist_compiled_memory(
                conn,
                step,
                memory,
                model=str(result.get("model") or ""),
            )
            return
        base_apply(conn, job_id, step, result)

    continuity_engine.build_chapter_contract = build_layered_contract
    continuity_engine._compile_memory = compile_chapter_memory
    continuity_engine.draft_prompt = enhanced_draft_prompt
    continuity_engine.continuity_apply_step_result = apply_layered_result
    continuity_engine.autopilot._apply_step_result = apply_layered_result
    _PATCHED = True


def install_memory_api() -> None:
    from . import main
    from .memory_api import router
    from .router_install import include_router_once, prioritize_prefix

    include_router_once(
        main.app,
        router,
        marker_path="/api/projects/{project_id}/memory/facts",
        marker_method="GET",
    )
    prioritize_prefix(main.app, "/api/projects/{project_id}/memory")
