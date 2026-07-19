from typing import Any

_PATCHED = False
_INSTALLED_APP_IDS: set[int] = set()


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

    app_id = id(main.app)
    if app_id in _INSTALLED_APP_IDS:
        return
    main.app.include_router(router)
    _INSTALLED_APP_IDS.add(app_id)
