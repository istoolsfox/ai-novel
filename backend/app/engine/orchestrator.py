"""Engine: multi-chapter orchestrator.

Runs the nine-step pipeline for N chapters in a background thread.
Supports:
  - Pure autonomous mode (default: no checkpoint pauses)
  - Checkpoint strategy (every_chapter / every_3 / every_5 / none)
  - Smart-stop (auto-pause on quality issues)
  - Circuit breaker (auto-pause on consecutive failures)
  - Narrative memory harvesting (v4 horizontal feedback)
  - SSE progress broadcasting

Auto-save policy: key steps (draft/deepen/finalize) persist immediately.
"""
import json
import threading
import time
from typing import Any, Callable

from ..infrastructure.database import (
    connect,
    get_active_jobs,
    get_blueprint,
    get_job,
    get_active_narrative_memory,
    insert_narrative_memory,
    new_id,
    row_to_dict,
    rows_to_dicts,
    update_job_status,
    utc_now,
)
from .checkpoint import CheckpointManager
from .circuit_breaker import CircuitBreaker
from .pipeline import ChapterContext, StoryPipeline
from ..workflows.blueprint_generator import check_foreshadowing_plan

# Job event queue for SSE broadcasting
# job_id -> list of events (consumed by SSE endpoint)
_JOB_EVENTS: dict[str, list[dict[str, Any]]] = {}
_JOB_EVENTS_LOCK = threading.Lock()

# Running job threads (for abort signaling)
_JOB_THREADS: dict[str, threading.Thread] = {}
_JOB_ABORT_FLAGS: dict[str, bool] = {}


def broadcast_event(job_id: str, event: dict[str, Any]) -> None:
    """Add an event to the job's SSE queue."""
    with _JOB_EVENTS_LOCK:
        if job_id not in _JOB_EVENTS:
            _JOB_EVENTS[job_id] = []
        _JOB_EVENTS[job_id].append(event)


def consume_events(job_id: str, after_index: int = 0) -> list[dict[str, Any]]:
    """Get events for a job after the given index (for SSE polling)."""
    with _JOB_EVENTS_LOCK:
        events = _JOB_EVENTS.get(job_id, [])
        return events[after_index:]


def get_event_count(job_id: str) -> int:
    with _JOB_EVENTS_LOCK:
        return len(_JOB_EVENTS.get(job_id, []))


def request_abort(job_id: str) -> None:
    """Signal a running job to abort."""
    _JOB_ABORT_FLAGS[job_id] = True


def is_aborted(job_id: str) -> bool:
    return _JOB_ABORT_FLAGS.get(job_id, False)


class Orchestrator:
    """Multi-chapter generation orchestrator. Runs in a background thread."""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        self.pipeline = StoryPipeline(job_id)
        self.checkpoint = CheckpointManager()
        self.breaker = CircuitBreaker(threshold=3, window=5)

    def run(self) -> None:
        """Main orchestrator loop. Runs in a background thread."""
        try:
            self._run_impl()
        except Exception as exc:
            update_job_status(self.job_id, "failed", error_message=str(exc))
            broadcast_event(self.job_id, {
                "type": "error",
                "message": str(exc),
                "timestamp": utc_now(),
            })

    def _run_impl(self) -> None:
        job = get_job(self.job_id)
        if not job:
            return

        project_id = job["project_id"]
        start_chapter = int(job["start_chapter_number"])
        target_count = int(job["target_chapter_count"])
        checkpoint_strategy = job.get("checkpoint_strategy", "none")
        auto_finalize = bool(job.get("auto_finalize", 1))
        params = {}
        if isinstance(job.get("params_json"), str):
            try:
                params = json.loads(job["params_json"])
            except json.JSONDecodeError:
                params = {}

        skip_steps = set(params.get("skip_steps", []))
        blueprint_id = job.get("volume_blueprint_id", "")
        blueprint = {}
        if blueprint_id:
            bp = get_blueprint(blueprint_id)
            if bp and isinstance(bp.get("blueprint_json"), str):
                try:
                    blueprint = json.loads(bp["blueprint_json"])
                except json.JSONDecodeError:
                    blueprint = {}

        # Mark job as running
        update_job_status(self.job_id, "running")
        broadcast_event(self.job_id, {
            "type": "job_started",
            "start_chapter": start_chapter,
            "target_count": target_count,
            "timestamp": utc_now(),
        })

        for offset in range(target_count):
            # Check abort
            if is_aborted(self.job_id):
                update_job_status(self.job_id, "aborted", pause_reason="user_aborted")
                broadcast_event(self.job_id, {"type": "aborted", "timestamp": utc_now()})
                return

            # Check pause (user-requested)
            job = get_job(self.job_id)
            if job and job.get("status") == "paused":
                broadcast_event(self.job_id, {"type": "paused", "timestamp": utc_now()})
                return  # Thread exits; resume creates a new thread

            chapter_number = start_chapter + offset

            # v5: Resume from checkpoint — skip chapters with all required steps completed
            if self._is_chapter_complete(chapter_number):
                broadcast_event(self.job_id, {
                    "type": "chapter_skipped",
                    "chapter_number": chapter_number,
                    "reason": "already_completed",
                    "timestamp": utc_now(),
                })
                continue

            # Create or get chapter
            chapter = self._get_or_create_chapter(project_id, chapter_number)
            if not chapter:
                self.breaker.record_failure()
                if self.breaker.should_trip():
                    update_job_status(
                        self.job_id, "failed",
                        error_message=f"circuit breaker: {self.breaker.consecutive_failures} consecutive failures"
                    )
                    broadcast_event(self.job_id, {"type": "circuit_breaker", "timestamp": utc_now()})
                    return
                continue

            chapter_id = chapter["id"]

            # Build context
            narrative_memory = get_active_narrative_memory(project_id)

            # v5: Check foreshadowing plan for this chapter
            foreshadowing_hints = check_foreshadowing_plan(blueprint, chapter_number)
            if foreshadowing_hints["plant"] or foreshadowing_hints["payoff"]:
                broadcast_event(self.job_id, {
                    "type": "foreshadowing",
                    "chapter_number": chapter_number,
                    "plant": [f.get("name", "") for f in foreshadowing_hints["plant"]],
                    "payoff": [f.get("name", "") for f in foreshadowing_hints["payoff"]],
                    "timestamp": utc_now(),
                })

            ctx = ChapterContext(
                project_id=project_id,
                chapter_id=chapter_id,
                chapter_number=chapter_number,
                target_words=int(blueprint.get("generation_params", {}).get("words_per_chapter", 3000)),
                blueprint=blueprint,
                narrative_memory=narrative_memory,
            )

            # Progress: chapter started
            update_job_status(
                self.job_id, "running",
                current_chapter_number=chapter_number,
                current_step="pipeline_start",
            )
            broadcast_event(self.job_id, {
                "type": "chapter_started",
                "chapter_number": chapter_number,
                "chapter_id": chapter_id,
                "timestamp": utc_now(),
            })

            # Run pipeline
            try:
                self.pipeline.run(
                    ctx,
                    skip_steps=skip_steps,
                    on_step=lambda step, status, data: self._on_step(
                        chapter_number, step, status, data
                    ),
                )
                self.breaker.record_success()

                # Harvest narrative memory (v4 horizontal feedback)
                self._harvest_narrative_memory(ctx)

                # Smart-stop check
                should_stop, reason = self.checkpoint.should_smart_stop(
                    project_id,
                    {
                        "chapter_number": chapter_number,
                        "draft": ctx.draft,
                        "summary": ctx.summary,
                        "archaeology": ctx.archaeology,
                        "target_words": ctx.target_words,
                        "volume_memory": None,  # Could fetch if needed
                    },
                )
                if should_stop:
                    update_job_status(
                        self.job_id, "checkpoint",
                        current_step="smart_stop",
                        pause_reason="smart_stop",
                        pause_detail=reason,
                    )
                    broadcast_event(self.job_id, {
                        "type": "smart_stop",
                        "chapter_number": chapter_number,
                        "reason": reason,
                        "timestamp": utc_now(),
                    })
                    return  # Thread exits; resume creates a new thread

                # Scheduled checkpoint
                if self.checkpoint.hit_checkpoint(checkpoint_strategy, offset):
                    update_job_status(
                        self.job_id, "checkpoint",
                        current_step="checkpoint",
                        pause_reason="checkpoint",
                        pause_detail=f"chapter {chapter_number}",
                    )
                    broadcast_event(self.job_id, {
                        "type": "checkpoint",
                        "chapter_number": chapter_number,
                        "timestamp": utc_now(),
                    })
                    return  # Thread exits; resume creates a new thread

                # Auto-finalize
                if auto_finalize:
                    self._finalize_chapter(project_id, chapter_id)

                broadcast_event(self.job_id, {
                    "type": "chapter_completed",
                    "chapter_number": chapter_number,
                    "chapter_id": chapter_id,
                    "word_count": len(ctx.draft),
                    "timestamp": utc_now(),
                })

            except Exception as exc:
                self.breaker.record_failure(exc)
                broadcast_event(self.job_id, {
                    "type": "chapter_failed",
                    "chapter_number": chapter_number,
                    "error": str(exc),
                    "timestamp": utc_now(),
                })
                if self.breaker.should_trip():
                    update_job_status(
                        self.job_id, "failed",
                        error_message=f"circuit breaker: {self.breaker.consecutive_failures} consecutive failures. Last error: {exc}"
                    )
                    broadcast_event(self.job_id, {"type": "circuit_breaker", "timestamp": utc_now()})
                    return
                continue

        # All chapters done
        update_job_status(self.job_id, "completed")
        broadcast_event(self.job_id, {"type": "completed", "timestamp": utc_now()})

    def _get_or_create_chapter(self, project_id: str, chapter_number: int) -> dict[str, Any] | None:
        """Get existing chapter or create a new one."""
        with connect() as conn:
            existing = row_to_dict(
                conn.execute(
                    "SELECT * FROM chapters WHERE project_id = ? AND chapter_number = ?",
                    (project_id, chapter_number),
                ).fetchone()
            )
            if existing:
                return existing
            # Create new chapter
            chapter_id = new_id()
            now = utc_now()
            conn.execute(
                """INSERT INTO chapters (id, project_id, outline_id, chapter_number, title, brief, draft, summary, word_count, status, created_at, updated_at)
                   VALUES (?, ?, '', ?, ?, '', '', '', 0, 'draft', ?, ?)""",
                (chapter_id, project_id, chapter_number, f"第 {chapter_number} 章", now, now),
            )
            return row_to_dict(conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone())

    def _is_chapter_complete(self, chapter_number: int) -> bool:
        """v5: Check if a chapter's required pipeline steps are all completed.

        If so, skip it during resume (breakpoint continuation).
        """
        with connect() as conn:
            steps = rows_to_dicts(
                conn.execute(
                    "SELECT * FROM chapter_generation_steps WHERE job_id = ? AND chapter_number = ? ORDER BY step_index",
                    (self.job_id, chapter_number),
                ).fetchall()
            )
        if not steps:
            return False
        required_steps = ["brief", "seed", "draft", "archaeology", "deepen", "finalize"]
        completed_names = {s["step_name"] for s in steps if s.get("status") == "completed"}
        return all(name in completed_names for name in required_steps)

    def _on_step(self, chapter_number: int, step_name: str, status: str, data: dict[str, Any]) -> None:
        """Progress callback for each pipeline step."""
        update_job_status(
            self.job_id, "running" if status == "running" else "running",
            current_chapter_number=chapter_number,
            current_step=step_name,
        )
        broadcast_event(self.job_id, {
            "type": "step",
            "chapter_number": chapter_number,
            "step_name": step_name,
            "status": status,
            "data": data,
            "timestamp": utc_now(),
        })

    def _harvest_narrative_memory(self, ctx: ChapterContext) -> None:
        """Extract valuable emotional leads from archaeology and store as narrative memory (v4)."""
        arch = ctx.archaeology
        if not arch or not isinstance(arch, dict):
            return

        # Extract subconscious leads
        leads = arch.get("subconscious_leads") or []
        for lead in leads[:3]:
            if isinstance(lead, dict) and lead.get("inferred"):
                insert_narrative_memory(
                    ctx.project_id,
                    ctx.chapter_id,
                    "subconscious",
                    lead["inferred"],
                )

        # Extract motif echoes
        motifs = arch.get("motif_echoes") or {}
        new_seeds = motifs.get("new_seeds") or []
        for seed in new_seeds[:2]:
            if isinstance(seed, dict) and seed.get("image"):
                insert_narrative_memory(
                    ctx.project_id,
                    ctx.chapter_id,
                    "motif",
                    f"new motif seed: {seed.get('image', '')}",
                )

        # Extract reader-felt resonance
        felt = arch.get("reader_felt_map") or {}
        resonances = felt.get("resonance_points") or []
        for r in resonances[:2]:
            if isinstance(r, dict) and r.get("felt"):
                insert_narrative_memory(
                    ctx.project_id,
                    ctx.chapter_id,
                    "reader_felt",
                    r["felt"],
                )

        # v4: Harvest voice traits from archaeology + dialogue (voice print growth)
        try:
            from ..application.voice_print_service import harvest_voice_traits_from_archaeology
            harvest_voice_traits_from_archaeology(
                ctx.project_id, ctx.chapter_id, ctx.archaeology, ctx.dialogue_map
            )
        except Exception:
            pass  # Voice trait harvesting failure doesn't block generation

    def _finalize_chapter(self, project_id: str, chapter_id: str) -> None:
        """Mark chapter as finalized."""
        from ..application.memory_service import (
            rebuild_volume_memory,
            sync_chapter_memory_to_wiki,
            volume_name_for_chapter,
            auto_generate_bridge,
        )
        with connect() as conn:
            chapter = row_to_dict(conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone())
            if not chapter:
                return
            summary = chapter.get("summary") or chapter.get("brief") or (chapter.get("draft") or "")[:80]
            now = utc_now()
            conn.execute(
                "UPDATE chapters SET status = 'final', summary = ?, updated_at = ? WHERE id = ?",
                (summary, now, chapter_id),
            )
            chapter["summary"] = summary
            chapter["status"] = "final"
        sync_chapter_memory_to_wiki(project_id, chapter)
        rebuild_volume_memory(project_id, volume_name_for_chapter(chapter))
        try:
            auto_generate_bridge(project_id, chapter)
        except Exception:
            pass


def start_job_thread(job_id: str) -> threading.Thread:
    """Start the orchestrator in a background thread."""
    # Clear abort flag and old events
    _JOB_ABORT_FLAGS[job_id] = False
    with _JOB_EVENTS_LOCK:
        _JOB_EVENTS[job_id] = []

    orchestrator = Orchestrator(job_id)
    thread = threading.Thread(target=orchestrator.run, daemon=True, name=f"job-{job_id}")
    _JOB_THREADS[job_id] = thread
    thread.start()
    return thread
