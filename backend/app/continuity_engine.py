from typing import Any

from . import autopilot
from .continuity_prompts import (
    blocking_issues,
    check_prompt,
    draft_chunks,
    draft_prompt,
    memory_prompt,
    normalize_check,
    normalize_memory,
    repair_prompt,
)
from .continuity_store import (
    fallback_previous_state,
    insert_check,
    json_text,
    latest_bridge_before,
    latest_character_knowledge,
    latest_character_states,
    latest_check,
    latest_contract,
    persist_bridge_and_memory,
    persist_check,
    persist_contract,
    require_chapter,
)
from .database import connect, new_id, row_to_dict, utc_now

CONTINUITY_STEPS = (
    "generate_chapter_brief",
    "build_chapter_contract",
    "generate_chapter_draft",
    "check_chapter_continuity",
    "repair_chapter_continuity",
    "recheck_chapter_continuity",
    "compile_chapter_memory",
    "finalize_chapter",
)

_INSTALLED_APP_IDS: set[int] = set()
_BASE_EXECUTOR = autopilot._default_step_executor
_BASE_APPLY_STEP_RESULT = autopilot._apply_step_result


def build_chapter_contract(project_id: str, chapter_id: str, chapter_number: int) -> dict[str, Any]:
    chapter = require_chapter(project_id, chapter_id)
    bridge_row = latest_bridge_before(project_id, chapter_number)
    bridge = bridge_row.get("payload") if bridge_row and isinstance(bridge_row.get("payload"), dict) else None
    if not bridge:
        bridge = fallback_previous_state(project_id, chapter_number)

    knowledge_by_character: dict[str, list[dict[str, Any]]] = {}
    for item in latest_character_knowledge(project_id):
        knowledge_by_character.setdefault(str(item.get("character_key") or "unknown"), []).append(
            {
                "fact_key": item.get("fact_key", ""),
                "fact_text": item.get("fact_text", ""),
                "knowledge_status": item.get("knowledge_status", "unknown"),
                "confidence": item.get("confidence", 0),
            }
        )

    constraints = []
    for state in latest_character_states(project_id):
        key = str(state.get("character_key") or "unknown")
        constraints.append(
            {
                "character_id": state.get("character_id", ""),
                "character_name": state.get("character_name", ""),
                "location": state.get("location", ""),
                "physical_state": state.get("physical_state", ""),
                "emotional_state": state.get("emotional_state", ""),
                "current_goal": state.get("current_goal", ""),
                "alive_status": state.get("alive_status", "alive"),
                "knowledge_boundaries": knowledge_by_character.get(key, []),
            }
        )

    ending_state = bridge.get("ending_state") if isinstance(bridge, dict) else {}
    contract = {
        "chapter_number": chapter_number,
        "chapter_id": chapter_id,
        "chapter_goal": chapter.get("brief") or f"推进第 {chapter_number} 章并承接上一章结果。",
        "must_continue_from": ending_state or {},
        "character_constraints": constraints,
        "open_actions": list(bridge.get("open_actions") or []) if isinstance(bridge, dict) else [],
        "open_hooks": list(bridge.get("open_hooks") or []) if isinstance(bridge, dict) else [],
        "emotional_residue": list(bridge.get("emotional_residue") or []) if isinstance(bridge, dict) else [],
        "forbidden_repetition": list(bridge.get("forbidden_repetition") or []) if isinstance(bridge, dict) else [],
        "next_chapter_seeds": list(bridge.get("next_chapter_seeds") or []) if isinstance(bridge, dict) else [],
        "source_bridge_id": bridge_row.get("id", "") if bridge_row else "",
        "priority_rule": "已定稿正文和上一章衔接包高于旧大纲；人物知识边界不得越界。",
    }
    return {
        "workflow": "build_chapter_contract",
        "model": "system",
        "status": "success",
        "text": json_text(contract),
        "structured": contract,
    }


def _run_check(project_id: str, chapter_id: str, chapter_number: int, *, recheck: bool) -> dict[str, Any]:
    from . import main

    chapter = require_chapter(project_id, chapter_id)
    contract_row = latest_contract(project_id, chapter_id)
    contract = contract_row.get("payload") if contract_row and isinstance(contract_row.get("payload"), dict) else {}
    bridge_row = latest_bridge_before(project_id, chapter_number)
    bridge = bridge_row.get("payload") if bridge_row and isinstance(bridge_row.get("payload"), dict) else {}
    draft = str(chapter.get("draft") or "")
    output = main.run_ai_workflow(
        project_id,
        "check_consistency",
        main.AiWorkflowIn(
            chapter_id=chapter_id,
            prompt=check_prompt(contract, bridge, draft, recheck=recheck),
            payload={
                "contract": contract,
                "previous_bridge": bridge,
                "draft_chunks": draft_chunks(draft),
                "stage": "recheck" if recheck else "initial",
            },
        ),
    )
    normalized = normalize_check(output, stage="recheck" if recheck else "initial")
    return {
        "workflow": "recheck_chapter_continuity" if recheck else "check_chapter_continuity",
        "model": output.get("model", ""),
        "status": "success",
        "text": json_text(normalized),
        "structured": normalized,
    }


def _compile_memory(project_id: str, chapter_id: str) -> dict[str, Any]:
    from . import main

    chapter = require_chapter(project_id, chapter_id)
    contract_row = latest_contract(project_id, chapter_id)
    contract = contract_row.get("payload") if contract_row and isinstance(contract_row.get("payload"), dict) else {}
    draft = str(chapter.get("draft") or "")
    output = main.run_ai_workflow(
        project_id,
        "extract_memory",
        main.AiWorkflowIn(
            chapter_id=chapter_id,
            prompt=memory_prompt(contract, draft),
            payload={"contract": contract, "draft_chunks": draft_chunks(draft)},
        ),
    )
    memory = normalize_memory(output, chapter)
    return {
        "workflow": "compile_chapter_memory",
        "model": output.get("model", ""),
        "status": "success",
        "text": json_text(memory),
        "structured": memory,
    }


def _repair_step_output(project_id: str, chapter_id: str) -> dict[str, Any]:
    from . import main

    chapter = require_chapter(project_id, chapter_id)
    check_row = latest_check(project_id, chapter_id, "initial")
    check = check_row.get("payload") if check_row and isinstance(check_row.get("payload"), dict) else {}
    blocking = blocking_issues(check)
    if not blocking:
        return {
            "workflow": "repair_chapter_continuity",
            "model": "system",
            "status": "skipped",
            "text": str(chapter.get("draft") or ""),
            "structured": {"changed": False, "reason": "initial_check_passed"},
        }
    contract_row = latest_contract(project_id, chapter_id)
    contract = contract_row.get("payload") if contract_row and isinstance(contract_row.get("payload"), dict) else {}
    output = main.run_ai_workflow(
        project_id,
        "revise_selection",
        main.AiWorkflowIn(
            chapter_id=chapter_id,
            prompt=repair_prompt(check, contract),
            current_draft=str(chapter.get("draft") or ""),
        ),
    )
    return {
        "workflow": "repair_chapter_continuity",
        "model": output.get("model", ""),
        "status": output.get("status", "success"),
        "text": output.get("text", ""),
        "structured": {"changed": True, "issues_repaired": blocking},
    }


def _recheck_step_output(project_id: str, chapter_id: str, chapter_number: int) -> dict[str, Any]:
    initial = latest_check(project_id, chapter_id, "initial")
    with connect() as conn:
        repair_step = row_to_dict(
            conn.execute(
                """
                SELECT * FROM generation_steps
                WHERE chapter_id = ? AND workflow = 'repair_chapter_continuity'
                ORDER BY created_at DESC LIMIT 1
                """,
                (chapter_id,),
            ).fetchone()
        )
    repair_output = repair_step.get("output_snapshot") if repair_step and isinstance(repair_step.get("output_snapshot"), dict) else {}
    repair_data = repair_output.get("structured") if isinstance(repair_output.get("structured"), dict) else {}
    initial_data = initial.get("payload") if initial and isinstance(initial.get("payload"), dict) else {}
    if initial and not blocking_issues(initial_data) and not repair_data.get("changed"):
        reused = dict(initial_data)
        reused["stage"] = "recheck"
        reused["reused_initial_check"] = True
        return {
            "workflow": "recheck_chapter_continuity",
            "model": "system",
            "status": "success",
            "text": json_text(reused),
            "structured": reused,
        }
    result = _run_check(project_id, chapter_id, chapter_number, recheck=True)
    if blocking_issues(result.get("structured") or {}):
        persist_check(project_id, chapter_id, chapter_number, result.get("structured") or {})
        raise RuntimeError("章节连续性复检仍存在高风险问题，已停止定稿。")
    return result


def continuity_executor(project_id: str, chapter_id: str, workflow: str, chapter_number: int) -> dict[str, Any]:
    from . import main

    if workflow == "build_chapter_contract":
        return build_chapter_contract(project_id, chapter_id, chapter_number)
    if workflow == "generate_chapter_draft":
        contract_row = latest_contract(project_id, chapter_id)
        contract = contract_row.get("payload") if contract_row and isinstance(contract_row.get("payload"), dict) else {}
        return main.run_ai_workflow(
            project_id,
            workflow,
            main.AiWorkflowIn(
                chapter_id=chapter_id,
                prompt=draft_prompt(contract, chapter_number),
                payload={"chapter_contract": contract},
            ),
        )
    if workflow == "check_chapter_continuity":
        return _run_check(project_id, chapter_id, chapter_number, recheck=False)
    if workflow == "repair_chapter_continuity":
        return _repair_step_output(project_id, chapter_id)
    if workflow == "recheck_chapter_continuity":
        return _recheck_step_output(project_id, chapter_id, chapter_number)
    if workflow == "compile_chapter_memory":
        return _compile_memory(project_id, chapter_id)
    return _BASE_EXECUTOR(project_id, chapter_id, workflow, chapter_number)


def continuity_apply_step_result(conn, job_id: str, step: dict[str, Any], result: dict[str, Any]) -> None:
    workflow = str(step["workflow"])
    if workflow in {"generate_chapter_brief", "generate_chapter_draft", "finalize_chapter"}:
        _BASE_APPLY_STEP_RESULT(conn, job_id, step, result)
        return
    if workflow == "build_chapter_contract":
        persist_contract(conn, step, result.get("structured") if isinstance(result.get("structured"), dict) else {})
        return
    if workflow in {"check_chapter_continuity", "recheck_chapter_continuity"}:
        insert_check(
            conn, step["project_id"], step["chapter_id"], step["chapter_number"],
            result.get("structured") if isinstance(result.get("structured"), dict) else {},
        )
        return
    if workflow == "repair_chapter_continuity":
        _apply_repair(conn, job_id, step, result)
        return
    if workflow == "compile_chapter_memory":
        persist_bridge_and_memory(
            conn, step, result.get("structured") if isinstance(result.get("structured"), dict) else {}
        )
        return
    _BASE_APPLY_STEP_RESULT(conn, job_id, step, result)


def _apply_repair(conn, job_id: str, step: dict[str, Any], result: dict[str, Any]) -> None:
    structured = result.get("structured") if isinstance(result.get("structured"), dict) else {}
    if not structured.get("changed"):
        return
    text = str(result.get("text") or "")
    if not text.strip():
        raise RuntimeError("连续性修复结果为空。")
    now = utc_now()
    conn.execute(
        """
        UPDATE chapters
        SET draft = ?, word_count = ?, status = 'draft', updated_at = ?
        WHERE id = ? AND project_id = ?
        """,
        (text, len(text), now, step["chapter_id"], step["project_id"]),
    )
    conn.execute(
        """
        INSERT INTO chapter_versions (
            id, project_id, chapter_id, label, content, model, context_summary, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id(), step["project_id"], step["chapter_id"],
            f"连续性修复 · 第 {step['chapter_number']} 章", text,
            str(result.get("model") or ""), f"autopilot_job={job_id}; continuity_repair=true", now,
        ),
    )


def install_continuity() -> None:
    from . import main
    from .continuity import router as continuity_router

    autopilot.AUTOPILOT_STEPS = CONTINUITY_STEPS
    autopilot._apply_step_result = continuity_apply_step_result
    autopilot.set_step_executor(continuity_executor)
    app_id = id(main.app)
    if app_id not in autopilot._INSTALLED_APP_IDS:
        main.app.include_router(autopilot.router)
        autopilot._INSTALLED_APP_IDS.add(app_id)
    if app_id not in _INSTALLED_APP_IDS:
        main.app.include_router(continuity_router)
        _INSTALLED_APP_IDS.add(app_id)
    autopilot.recover_interrupted_jobs()
