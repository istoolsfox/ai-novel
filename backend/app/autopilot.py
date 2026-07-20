import asyncio
import json
import os
import threading
import time
from collections.abc import Callable
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .database import connect, new_id, row_to_dict, rows_to_dicts, utc_now


AUTOPILOT_STEPS = (
    "generate_chapter_brief",
    "generate_chapter_draft",
    "finalize_chapter",
)
ACTIVE_JOB_STATUSES = ("queued", "running", "paused")
TERMINAL_JOB_STATUSES = ("completed", "failed", "cancelled")
StepExecutor = Callable[[str, str, str, int], dict[str, Any]]

router = APIRouter(prefix="/api/projects/{project_id}/autopilot", tags=["autopilot"])
_EXECUTOR: StepExecutor | None = None
_WORKERS: dict[str, threading.Thread] = {}
_WORKERS_LOCK = threading.Lock()
_INSTALLED_APP_IDS: set[int] = set()


class AutopilotStartIn(BaseModel):
    start_chapter: int = Field(default=1, ge=1)
    end_chapter: int | None = Field(default=None, ge=1)
    mode: Literal["full_autopilot", "chapter_checkpoint", "smart_checkpoint"] = "full_autopilot"
    max_retries: int = Field(default=2, ge=0, le=10)


def set_step_executor(executor: StepExecutor) -> None:
    global _EXECUTOR
    _EXECUTOR = executor


def _default_step_executor(project_id: str, chapter_id: str, workflow: str, chapter_number: int) -> dict[str, Any]:
    from . import main

    if workflow == "finalize_chapter":
        chapter = main.finalize_chapter(project_id, chapter_id)
        return {
            "workflow": workflow,
            "status": "success",
            "model": "system",
            "text": chapter.get("summary") or "",
            "chapter": chapter,
        }

    prompt = (
        f"为第 {chapter_number} 章生成可直接执行的章节大纲。"
        if workflow == "generate_chapter_brief"
        else f"根据第 {chapter_number} 章当前大纲生成完整正文，并承接已有章节记忆。"
    )
    return main.run_ai_workflow(
        project_id,
        workflow,
        main.AiWorkflowIn(chapter_id=chapter_id, prompt=prompt),
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _require_project(project_id: str) -> dict[str, Any]:
    with connect() as conn:
        project = row_to_dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _require_job(project_id: str, job_id: str) -> dict[str, Any]:
    with connect() as conn:
        job = row_to_dict(
            conn.execute(
                "SELECT * FROM generation_jobs WHERE id = ? AND project_id = ?",
                (job_id, project_id),
            ).fetchone()
        )
    if not job:
        raise HTTPException(status_code=404, detail="Autopilot job not found")
    return job


def _append_event(
    conn,
    job_id: str,
    project_id: str,
    event_type: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO generation_events (id, job_id, project_id, event_type, message, payload, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (new_id(), job_id, project_id, event_type, message, _json(payload or {}), utc_now()),
    )


def _ensure_chapter(conn, project_id: str, chapter_number: int) -> str:
    row = conn.execute(
        "SELECT id FROM chapters WHERE project_id = ? AND chapter_number = ? ORDER BY created_at LIMIT 1",
        (project_id, chapter_number),
    ).fetchone()
    if row:
        return str(row["id"])

    chapter_id = new_id()
    now = utc_now()
    conn.execute(
        """
        INSERT INTO chapters (
            id, project_id, outline_id, chapter_number, title, brief, draft,
            summary, word_count, status, created_at, updated_at
        )
        VALUES (?, ?, '', ?, ?, '', '', '', 0, 'draft', ?, ?)
        """,
        (chapter_id, project_id, chapter_number, f"第 {chapter_number} 章", now, now),
    )
    return chapter_id


def _job_snapshot(job_id: str) -> dict[str, Any]:
    with connect() as conn:
        job = row_to_dict(conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job_id,)).fetchone())
        if not job:
            raise HTTPException(status_code=404, detail="Autopilot job not found")
        steps = rows_to_dicts(
            conn.execute(
                "SELECT * FROM generation_steps WHERE job_id = ? ORDER BY step_order",
                (job_id,),
            ).fetchall()
        )
        events = rows_to_dicts(
            conn.execute(
                "SELECT * FROM generation_events WHERE job_id = ? ORDER BY created_at DESC LIMIT 100",
                (job_id,),
            ).fetchall()
        )
    total = int(job.get("total_steps") or 0)
    completed = int(job.get("completed_steps") or 0)
    return {
        "job": job,
        "steps": steps,
        "events": events,
        "progress": {
            "completed": completed,
            "total": total,
            "percent": round((completed / total) * 100, 2) if total else 0,
        },
    }


def _retry_delay_seconds(attempt_count: int) -> float:
    try:
        base = float(os.getenv("AI_NOVEL_AUTOPILOT_RETRY_DELAY_SECONDS", "2"))
    except ValueError:
        base = 2
    return max(0.0, min(base * max(1, attempt_count), 30.0))


def _worker_disabled() -> bool:
    return os.getenv("AI_NOVEL_AUTOPILOT_DISABLE_WORKER", "").lower() in {"1", "true", "yes"}


def _sync_worker() -> bool:
    return os.getenv("AI_NOVEL_AUTOPILOT_SYNC", "").lower() in {"1", "true", "yes"}


def _wake_job(job_id: str) -> None:
    if _worker_disabled():
        return
    if _sync_worker():
        _process_job(job_id)
        return

    with _WORKERS_LOCK:
        existing = _WORKERS.get(job_id)
        if existing and existing.is_alive():
            return
        worker = threading.Thread(target=_process_job_guarded, args=(job_id,), daemon=True, name=f"autopilot-{job_id[:8]}")
        _WORKERS[job_id] = worker
        worker.start()


def _process_job_guarded(job_id: str) -> None:
    try:
        _process_job(job_id)
    finally:
        with _WORKERS_LOCK:
            _WORKERS.pop(job_id, None)


def _next_pending_step(conn, job_id: str):
    return conn.execute(
        """
        SELECT * FROM generation_steps
        WHERE job_id = ? AND status = 'pending'
        ORDER BY step_order
        LIMIT 1
        """,
        (job_id,),
    ).fetchone()


def _process_job(job_id: str) -> None:
    while True:
        with connect() as conn:
            job = row_to_dict(conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job_id,)).fetchone())
            if not job or job["status"] in TERMINAL_JOB_STATUSES or job["status"] == "paused":
                return

            if job["status"] == "queued":
                now = utc_now()
                conn.execute(
                    """
                    UPDATE generation_jobs
                    SET status = 'running', started_at = CASE WHEN started_at = '' THEN ? ELSE started_at END,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (now, now, job_id),
                )
                _append_event(conn, job_id, job["project_id"], "job.running", "托管任务开始执行。")

            step_row = _next_pending_step(conn, job_id)
            if not step_row:
                failed_count = conn.execute(
                    "SELECT COUNT(*) FROM generation_steps WHERE job_id = ? AND status = 'failed'",
                    (job_id,),
                ).fetchone()[0]
                now = utc_now()
                if failed_count:
                    conn.execute(
                        "UPDATE generation_jobs SET status = 'failed', updated_at = ?, completed_at = ? WHERE id = ?",
                        (now, now, job_id),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE generation_jobs
                        SET status = 'completed', current_step = '', updated_at = ?, completed_at = ?
                        WHERE id = ?
                        """,
                        (now, now, job_id),
                    )
                    _append_event(conn, job_id, job["project_id"], "job.completed", "托管任务已完成。")
                return
            step = row_to_dict(step_row)

        if not _execute_step(job_id, step):
            return


def _execute_step(job_id: str, step: dict[str, Any]) -> bool:
    global _EXECUTOR
    executor = _EXECUTOR or _default_step_executor

    while True:
        with connect() as conn:
            job = row_to_dict(conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job_id,)).fetchone())
            current = row_to_dict(conn.execute("SELECT * FROM generation_steps WHERE id = ?", (step["id"],)).fetchone())
            if not job or not current:
                return False
            if job["status"] in {"cancelled", "paused"}:
                return False
            if current["status"] == "completed":
                return True

            attempt = int(current.get("attempt_count") or 0) + 1
            now = utc_now()
            conn.execute(
                """
                UPDATE generation_steps
                SET status = 'running', attempt_count = ?, started_at = ?, updated_at = ?, error_message = ''
                WHERE id = ?
                """,
                (attempt, now, now, current["id"]),
            )
            conn.execute(
                """
                UPDATE generation_jobs
                SET status = 'running', current_chapter = ?, current_step = ?, updated_at = ?
                WHERE id = ?
                """,
                (current["chapter_number"], current["workflow"], now, job_id),
            )
            _append_event(
                conn,
                job_id,
                job["project_id"],
                "step.started",
                f"第 {current['chapter_number']} 章：开始 {current['workflow']}。",
                {"step_id": current["id"], "attempt": attempt},
            )

        try:
            result = executor(
                str(job["project_id"]),
                str(current["chapter_id"]),
                str(current["workflow"]),
                int(current["chapter_number"]),
            )
            with connect() as conn:
                latest_job = row_to_dict(conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job_id,)).fetchone())
                if not latest_job or latest_job["status"] == "cancelled":
                    conn.execute(
                        "UPDATE generation_steps SET status = 'cancelled', updated_at = ? WHERE id = ?",
                        (utc_now(), current["id"]),
                    )
                    return False

                _apply_step_result(conn, job_id, current, result)
                now = utc_now()
                conn.execute(
                    """
                    UPDATE generation_steps
                    SET status = 'completed', output_snapshot = ?, error_message = '',
                        completed_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (_json(result), now, now, current["id"]),
                )
                conn.execute(
                    """
                    UPDATE generation_jobs
                    SET completed_steps = completed_steps + 1, error_message = '', updated_at = ?
                    WHERE id = ?
                    """,
                    (now, job_id),
                )
                _append_event(
                    conn,
                    job_id,
                    current["project_id"],
                    "step.completed",
                    f"第 {current['chapter_number']} 章：完成 {current['workflow']}。",
                    {"step_id": current["id"], "workflow": current["workflow"]},
                )
            return True
        except Exception as exc:
            detail = getattr(exc, "detail", None)
            error_message = str(detail if detail is not None else exc)
            max_retries = int(current.get("max_retries") or 0)
            if attempt <= max_retries:
                with connect() as conn:
                    conn.execute(
                        """
                        UPDATE generation_steps
                        SET status = 'pending', error_message = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (error_message, utc_now(), current["id"]),
                    )
                    _append_event(
                        conn,
                        job_id,
                        job["project_id"],
                        "step.retry_scheduled",
                        f"{current['workflow']} 执行失败，将自动重试。",
                        {"step_id": current["id"], "attempt": attempt, "error": error_message},
                    )
                delay = _retry_delay_seconds(attempt)
                if delay:
                    time.sleep(delay)
                continue

            now = utc_now()
            with connect() as conn:
                conn.execute(
                    """
                    UPDATE generation_steps
                    SET status = 'failed', error_message = ?, completed_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (error_message, now, now, current["id"]),
                )
                conn.execute(
                    """
                    UPDATE generation_jobs
                    SET status = 'failed', error_message = ?, updated_at = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (error_message, now, now, job_id),
                )
                _append_event(
                    conn,
                    job_id,
                    job["project_id"],
                    "step.failed",
                    f"{current['workflow']} 执行失败，托管任务已暂停。",
                    {"step_id": current["id"], "attempt": attempt, "error": error_message},
                )
            return False


def _apply_step_result(conn, job_id: str, step: dict[str, Any], result: dict[str, Any]) -> None:
    workflow = str(step["workflow"])
    chapter_id = str(step["chapter_id"])
    now = utc_now()

    if workflow == "generate_chapter_brief":
        structured = result.get("structured") if isinstance(result.get("structured"), dict) else {}
        title = str(structured.get("chapter_title") or "").strip()
        brief = str(structured.get("chapter_goal") or result.get("text") or "").strip()
        conn.execute(
            """
            UPDATE chapters
            SET title = CASE WHEN ? = '' THEN title ELSE ? END,
                brief = ?, updated_at = ?
            WHERE id = ? AND project_id = ?
            """,
            (title, title, brief, now, chapter_id, step["project_id"]),
        )
        return

    if workflow == "generate_chapter_draft":
        text = str(result.get("text") or "")
        if not text.strip():
            raise RuntimeError("章节正文生成结果为空。")
        conn.execute(
            """
            UPDATE chapters
            SET draft = ?, word_count = ?, status = 'draft', updated_at = ?
            WHERE id = ? AND project_id = ?
            """,
            (text, len(text), now, chapter_id, step["project_id"]),
        )
        conn.execute(
            """
            INSERT INTO chapter_versions (
                id, project_id, chapter_id, label, content, model, context_summary, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id(),
                step["project_id"],
                chapter_id,
                f"托管生成 · 第 {step['chapter_number']} 章",
                text,
                str(result.get("model") or ""),
                f"autopilot_job={job_id}",
                now,
            ),
        )


def recover_interrupted_jobs() -> None:
    with connect() as conn:
        interrupted = rows_to_dicts(
            conn.execute(
                "SELECT * FROM generation_jobs WHERE status IN ('queued', 'running') ORDER BY created_at",
            ).fetchall()
        )
        if interrupted:
            now = utc_now()
            conn.execute(
                "UPDATE generation_steps SET status = 'pending', updated_at = ? WHERE status = 'running'",
                (now,),
            )
            conn.execute(
                "UPDATE generation_jobs SET status = 'queued', current_step = '', updated_at = ? WHERE status = 'running'",
                (now,),
            )
            for job in interrupted:
                _append_event(
                    conn,
                    job["id"],
                    job["project_id"],
                    "job.recovered",
                    "检测到未完成托管任务，已恢复到可继续执行状态。",
                )

    for job in interrupted:
        _wake_job(str(job["id"]))


def install_autopilot() -> None:
    from . import main

    app_id = id(main.app)
    if app_id not in _INSTALLED_APP_IDS:
        main.app.include_router(router)
        _INSTALLED_APP_IDS.add(app_id)
    set_step_executor(_default_step_executor)
    recover_interrupted_jobs()


@router.post("/start")
def start_autopilot(project_id: str, payload: AutopilotStartIn) -> dict[str, Any]:
    project = _require_project(project_id)
    end_chapter = payload.end_chapter or int(project.get("target_chapter_count") or 0)
    if end_chapter <= 0:
        raise HTTPException(status_code=400, detail="请设置 end_chapter，或先配置项目目标章节数。")
    if end_chapter < payload.start_chapter:
        raise HTTPException(status_code=400, detail="end_chapter 不能小于 start_chapter。")

    job_id = new_id()
    now = utc_now()
    total_steps = (end_chapter - payload.start_chapter + 1) * len(AUTOPILOT_STEPS)

    with connect() as conn:
        active = row_to_dict(
            conn.execute(
                """
                SELECT * FROM generation_jobs
                WHERE project_id = ? AND status IN ('queued', 'running', 'paused')
                ORDER BY created_at DESC LIMIT 1
                """,
                (project_id,),
            ).fetchone()
        )
        if active:
            raise HTTPException(status_code=409, detail=f"项目已有未结束的托管任务：{active['id']}")

        conn.execute(
            """
            INSERT INTO generation_jobs (
                id, project_id, mode, status, start_chapter, end_chapter,
                current_chapter, current_step, total_steps, completed_steps,
                max_retries, error_message, created_at, updated_at,
                started_at, paused_at, completed_at
            )
            VALUES (?, ?, ?, 'queued', ?, ?, ?, '', ?, 0, ?, '', ?, ?, '', '', '')
            """,
            (
                job_id,
                project_id,
                payload.mode,
                payload.start_chapter,
                end_chapter,
                payload.start_chapter,
                total_steps,
                payload.max_retries,
                now,
                now,
            ),
        )

        step_order = 0
        for chapter_number in range(payload.start_chapter, end_chapter + 1):
            chapter_id = _ensure_chapter(conn, project_id, chapter_number)
            for workflow in AUTOPILOT_STEPS:
                step_order += 1
                step_id = new_id()
                conn.execute(
                    """
                    INSERT INTO generation_steps (
                        id, job_id, project_id, chapter_id, chapter_number, step_order,
                        workflow, status, attempt_count, max_retries, input_snapshot,
                        output_snapshot, error_message, started_at, completed_at,
                        idempotency_key, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?, '{}', '{}', '', '', '', ?, ?, ?)
                    """,
                    (
                        step_id,
                        job_id,
                        project_id,
                        chapter_id,
                        chapter_number,
                        step_order,
                        workflow,
                        payload.max_retries,
                        f"{chapter_number}:{workflow}",
                        now,
                        now,
                    ),
                )

        _append_event(
            conn,
            job_id,
            project_id,
            "job.created",
            f"已创建第 {payload.start_chapter}—{end_chapter} 章托管任务。",
            {"mode": payload.mode, "total_steps": total_steps},
        )

    _wake_job(job_id)
    return _job_snapshot(job_id)


@router.get("/status")
def latest_autopilot_status(project_id: str) -> dict[str, Any]:
    _require_project(project_id)
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM generation_jobs WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
            (project_id,),
        ).fetchone()
    if not row:
        return {"job": None, "steps": [], "events": [], "progress": {"completed": 0, "total": 0, "percent": 0}}
    return _job_snapshot(str(row["id"]))


@router.get("/jobs/{job_id}")
def get_autopilot_job(project_id: str, job_id: str) -> dict[str, Any]:
    _require_job(project_id, job_id)
    return _job_snapshot(job_id)


@router.post("/jobs/{job_id}/pause")
def pause_autopilot(project_id: str, job_id: str) -> dict[str, Any]:
    job = _require_job(project_id, job_id)
    if job["status"] in TERMINAL_JOB_STATUSES:
        raise HTTPException(status_code=409, detail="已结束的托管任务不能暂停。")
    now = utc_now()
    with connect() as conn:
        conn.execute(
            "UPDATE generation_jobs SET status = 'paused', paused_at = ?, updated_at = ? WHERE id = ?",
            (now, now, job_id),
        )
        _append_event(conn, job_id, project_id, "job.paused", "托管任务已暂停；正在执行的模型请求会在返回后停止后续步骤。")
    return _job_snapshot(job_id)


@router.post("/jobs/{job_id}/resume")
def resume_autopilot(project_id: str, job_id: str) -> dict[str, Any]:
    job = _require_job(project_id, job_id)
    if job["status"] != "paused":
        raise HTTPException(status_code=409, detail="只有暂停中的托管任务可以恢复。")
    with connect() as conn:
        conn.execute(
            "UPDATE generation_jobs SET status = 'queued', paused_at = '', updated_at = ? WHERE id = ?",
            (utc_now(), job_id),
        )
        _append_event(conn, job_id, project_id, "job.resumed", "托管任务已恢复。")
    _wake_job(job_id)
    return _job_snapshot(job_id)


@router.post("/jobs/{job_id}/stop")
def stop_autopilot(project_id: str, job_id: str) -> dict[str, Any]:
    job = _require_job(project_id, job_id)
    if job["status"] in TERMINAL_JOB_STATUSES:
        return _job_snapshot(job_id)
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            UPDATE generation_jobs
            SET status = 'cancelled', error_message = '', updated_at = ?, completed_at = ?
            WHERE id = ?
            """,
            (now, now, job_id),
        )
        conn.execute(
            """
            UPDATE generation_steps
            SET status = 'cancelled', updated_at = ?
            WHERE job_id = ? AND status IN ('pending', 'running')
            """,
            (now, job_id),
        )
        _append_event(conn, job_id, project_id, "job.cancelled", "托管任务已停止。")
    return _job_snapshot(job_id)


@router.post("/jobs/{job_id}/steps/{step_id}/retry")
def retry_autopilot_step(project_id: str, job_id: str, step_id: str) -> dict[str, Any]:
    _require_job(project_id, job_id)
    with connect() as conn:
        step = row_to_dict(
            conn.execute(
                "SELECT * FROM generation_steps WHERE id = ? AND job_id = ? AND project_id = ?",
                (step_id, job_id, project_id),
            ).fetchone()
        )
        if not step:
            raise HTTPException(status_code=404, detail="Autopilot step not found")
        if step["status"] != "failed":
            raise HTTPException(status_code=409, detail="只有失败的步骤可以重试。")
        now = utc_now()
        conn.execute(
            """
            UPDATE generation_steps
            SET status = 'pending', attempt_count = 0, error_message = '',
                started_at = '', completed_at = '', updated_at = ?
            WHERE id = ?
            """,
            (now, step_id),
        )
        conn.execute(
            """
            UPDATE generation_jobs
            SET status = 'queued', error_message = '', completed_at = '', updated_at = ?
            WHERE id = ?
            """,
            (now, job_id),
        )
        _append_event(
            conn,
            job_id,
            project_id,
            "step.retry_requested",
            f"已请求重试第 {step['chapter_number']} 章的 {step['workflow']}。",
            {"step_id": step_id},
        )
    _wake_job(job_id)
    return _job_snapshot(job_id)


@router.get("/events")
def list_autopilot_events(project_id: str, limit: int = 100) -> list[dict[str, Any]]:
    _require_project(project_id)
    safe_limit = max(1, min(limit, 500))
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                """
                SELECT * FROM generation_events
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (project_id, safe_limit),
            ).fetchall()
        )


@router.get("/events/stream")
async def stream_autopilot_events(project_id: str):
    _require_project(project_id)

    async def event_stream():
        last_signature = ""
        while True:
            snapshot = latest_autopilot_status(project_id)
            job = snapshot.get("job")
            signature = _json(
                {
                    "job_id": job.get("id") if job else "",
                    "status": job.get("status") if job else "idle",
                    "completed": snapshot["progress"]["completed"],
                    "current_step": job.get("current_step") if job else "",
                }
            )
            if signature != last_signature:
                yield f"data: {_json(snapshot)}\n\n"
                last_signature = signature
            if job and job.get("status") in TERMINAL_JOB_STATUSES:
                yield "event: end\ndata: {}\n\n"
                return
            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
