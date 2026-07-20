import json
from typing import Any

_PATCHED = False


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def patch_impact_planning_runtime() -> None:
    global _PATCHED
    if _PATCHED:
        return

    from . import autopilot, continuity_engine
    from .database import connect
    from .impact_engine import analyze_story_impact, persist_impact_analysis
    from .rolling_planner import (
        build_rolling_plan_proposal,
        get_plan_item,
        mark_plan_completed,
        persist_rolling_plan,
        planning_context,
    )

    base_executor = continuity_engine.continuity_executor
    base_contract = continuity_engine.build_chapter_contract

    def impact_planning_executor(
        project_id: str,
        chapter_id: str,
        workflow: str,
        chapter_number: int,
    ) -> dict[str, Any]:
        if workflow == "generate_chapter_brief":
            plan = get_plan_item(project_id, chapter_number)
            if plan:
                from . import main

                return main.run_ai_workflow(
                    project_id,
                    workflow,
                    main.AiWorkflowIn(
                        chapter_id=chapter_id,
                        prompt=(
                            f"为第 {chapter_number} 章生成可直接执行的章节大纲。"
                            "必须遵守滚动计划中的主推进线、目标节点和必须处理事项；"
                            "如果滚动计划与已定稿正文冲突，以已定稿正文为准。"
                            f"\n滚动计划：{_json(plan)}"
                        ),
                        payload={"rolling_plan": plan},
                    ),
                )
        if workflow == "finalize_chapter":
            analysis = analyze_story_impact(project_id, chapter_id, chapter_number)
            with connect() as conn:
                run_id = persist_impact_analysis(conn, analysis)
            proposal = build_rolling_plan_proposal(
                project_id,
                chapter_id,
                chapter_number,
            )
            with connect() as conn:
                snapshot_id = persist_rolling_plan(conn, proposal)
            result = base_executor(project_id, chapter_id, workflow, chapter_number)
            mark_plan_completed(project_id, chapter_number)
            result["impact_run_id"] = run_id
            result["rolling_plan_snapshot_id"] = snapshot_id
            result["impact_summary"] = analysis.get("summary", "")
            result["planning_summary"] = proposal.get("summary", "")
            return result
        return base_executor(project_id, chapter_id, workflow, chapter_number)

    def build_planning_contract(
        project_id: str,
        chapter_id: str,
        chapter_number: int,
    ) -> dict[str, Any]:
        result = base_contract(project_id, chapter_id, chapter_number)
        contract = result.get("structured") if isinstance(result.get("structured"), dict) else {}
        contract.update(planning_context(project_id, chapter_number))
        contract["priority_rule"] = (
            str(contract.get("priority_rule") or "")
            + " 滚动计划只约束未来未定稿章节；已定稿正文、真实状态和知识边界仍具有最高优先级。"
        ).strip()
        result["structured"] = contract
        result["text"] = continuity_engine.json_text(contract)
        return result

    continuity_engine.continuity_executor = impact_planning_executor
    continuity_engine.build_chapter_contract = build_planning_contract
    autopilot.set_step_executor(impact_planning_executor)
    _PATCHED = True


def install_impact_planning_api() -> None:
    from . import main
    from .impact_planning_api import router
    from .router_install import include_router_once, prioritize_prefix

    include_router_once(
        main.app,
        router,
        marker_path="/api/projects/{project_id}/planning/current",
        marker_method="GET",
    )
    prioritize_prefix(main.app, "/api/projects/{project_id}/planning")
    prioritize_prefix(main.app, "/api/projects/{project_id}/impact")
