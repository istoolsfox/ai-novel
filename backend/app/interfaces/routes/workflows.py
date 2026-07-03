"""接口层 · AI 工作流路由。

模型连接测试 + AI 工作流调用（含情感深度增强 v2 的持久化逻辑）。
"""
import json
from typing import Any

from fastapi import APIRouter

from ...domain.models import AiWorkflowIn, ModelConnectionTestIn, VersionIn
from ...infrastructure.database import (
    connect,
    create_archaeology,
    create_chapter_bridge,
    create_emotion_seed,
    create_image_growth,
    get_emotional_lead,
    get_emotion_seed,
    new_id,
    update_emotional_lead,
    utc_now,
)
from ...infrastructure.storage import require_project
from ...application.context_builder import build_generation_context
from ..dependencies import require_chapter
from ...workflows.generation import validate_workflow_prerequisites
from ...workflows.llm_client import run_model_or_stub, test_remote_model_connection

router = APIRouter(prefix="/api/projects/{project_id}/ai", tags=["ai"])


@router.post("/test-connection")
def test_model_connection(project_id: str, payload: ModelConnectionTestIn) -> dict[str, Any]:
    require_project(project_id)
    return test_remote_model_connection(payload)


@router.post("/{workflow}")
def run_ai_workflow(project_id: str, workflow: str, payload: AiWorkflowIn) -> dict[str, Any]:
    require_project(project_id)
    context = build_generation_context(project_id, payload.chapter_id)
    validate_workflow_prerequisites(workflow, context)

    # 生成正文前自动编排：如果没有情感种子，先生成一颗
    if workflow == "generate_chapter_draft" and payload.chapter_id:
        existing_seed = get_emotion_seed(project_id, payload.chapter_id)
        if not existing_seed:
            try:
                seed_payload = AiWorkflowIn(
                    chapter_id=payload.chapter_id,
                    prompt=payload.prompt or "",
                    content="",
                )
                seed_output = run_model_or_stub(project_id, "generate_emotion_seed", seed_payload, context)
                seed_structured = seed_output.get("structured") or {}
                if isinstance(seed_structured, dict) and seed_structured.get("emotion_seed"):
                    create_emotion_seed(project_id, payload.chapter_id, seed_structured["emotion_seed"])
                    # 重新构建上下文，让正文生成能看到刚生成的种子
                    context = build_generation_context(project_id, payload.chapter_id)
            except Exception:
                pass  # 种子生成失败不阻断正文生成

    output = run_model_or_stub(project_id, workflow, payload, context)
    output["context"] = context
    output_status = output.get("status") or "success"
    output_error = output.get("error") or ""
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO ai_runs (id, project_id, workflow, input_snapshot, output_text, model, status, error_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id(),
                project_id,
                workflow,
                json.dumps(payload.model_dump(), ensure_ascii=False),
                output["text"],
                output["model"],
                output_status,
                output_error,
                now,
            ),
        )
    _persist_workflow_output(project_id, workflow, payload, output, context, now)
    return output


def _persist_workflow_output(
    project_id: str,
    workflow: str,
    payload: AiWorkflowIn,
    output: dict[str, Any],
    context: dict[str, Any],
    now: str,
) -> None:
    """把工作流产出持久化到对应表。"""
    if workflow == "score_chapter" and payload.chapter_id:
        require_chapter(project_id, payload.chapter_id)
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO chapter_scores (id, project_id, chapter_id, total_score, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (new_id(), project_id, payload.chapter_id, output["score"], json.dumps(output, ensure_ascii=False), now),
            )
    if workflow == "generate_chapter_variants" and payload.chapter_id:
        from .chapters import create_chapter_version
        for index in range(max(1, payload.count)):
            create_chapter_version(
                project_id,
                payload.chapter_id,
                VersionIn(label=f"AI 版本 {index + 1}", content=f"{output['text']}\n\n候选版本 {index + 1}。"),
            )
    # ===== 情感深度增强 v2 持久化 =====
    if workflow == "generate_emotion_seed" and payload.chapter_id:
        seed_data = output.get("structured") or {}
        if isinstance(seed_data, dict) and seed_data.get("emotion_seed"):
            create_emotion_seed(project_id, payload.chapter_id, seed_data["emotion_seed"])
    if workflow == "emotion_archaeology" and payload.chapter_id:
        arch_data = output.get("structured") or output.get("text_parsed") or {}
        if isinstance(arch_data, dict) and arch_data.get("subconscious_leads") is not None:
            create_archaeology(project_id, payload.chapter_id, arch_data, payload.payload.get("view_mode", "triple"))
    if workflow == "deepen_and_bury" and payload.chapter_id:
        revised = (output.get("structured") or {}).get("revised_text")
        if revised:
            with connect() as conn:
                conn.execute(
                    "UPDATE chapters SET draft = ?, updated_at = ? WHERE id = ? AND project_id = ?",
                    (revised, now, payload.chapter_id, project_id),
                )
    if workflow == "trace_image_growth" and payload.chapter_id:
        tracked = (output.get("structured") or {}).get("tracked_images") or []
        chapter = context.get("chapter") or {}
        chapter_number = int(chapter.get("chapter_number") or 0)
        for item in tracked:
            if isinstance(item, dict) and item.get("image"):
                create_image_growth(
                    project_id, item["image"], payload.chapter_id, chapter_number,
                    item.get("context", ""), item.get("felt_meaning_hint", ""), bool(item.get("is_new", True)),
                )
    if workflow == "retrospect_deepen" and payload.payload.get("lead_id"):
        lead_id = payload.payload["lead_id"]
        target_chapter_ids = payload.payload.get("target_chapter_ids") or []
        revised = (output.get("structured") or {}).get("revised_text")
        if revised and target_chapter_ids:
            for cid in target_chapter_ids:
                with connect() as conn:
                    conn.execute(
                        "UPDATE chapters SET draft = ?, updated_at = ? WHERE id = ? AND project_id = ?",
                        (revised, now, cid, project_id),
                    )
        lead = get_emotional_lead(project_id, lead_id)
        if lead:
            deepened = lead.get("deepened_chapters") or []
            if isinstance(deepened, str):
                deepened = json.loads(deepened)
            deepened = list(set(deepened + target_chapter_ids))
            update_emotional_lead(project_id, lead_id, {"deepened_chapters": deepened, "status": "deepened"})
    if workflow == "generate_chapter_bridge" and payload.chapter_id:
        bridge_data = output.get("structured") or {}
        if isinstance(bridge_data, dict) and bridge_data.get("ending_state"):
            chapter = context.get("chapter") or {}
            chapter_number = int(chapter.get("chapter_number") or 0)
            bridge_data.pop("_chapter_id", None)
            bridge_data.pop("_chapter_number", None)
            create_chapter_bridge(project_id, payload.chapter_id, chapter_number, bridge_data)
