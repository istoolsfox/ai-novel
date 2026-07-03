"""Engine: nine-step story pipeline.

Runs the full nine-step chapter generation pipeline:
  1. generate_chapter_brief      - chapter outline
  2. generate_emotion_seed       - emotional seed (fuzzy entry)
  3. generate_chapter_draft      - body text (free growth)
  4. dialogue_subtext_excavation - dialogue subtext mining [v4]
  5. emotion_archaeology         - three-perspective deep reading
  6. analyze_reader_pull         - reader pull analysis [v4]
  7. deepen_and_bury             - deepen & bury (do subtraction)
  8. anti_ai_polish              - anti-AI cliche scan
  9. summarize_and_bridge        - summary + chapter bridge (finalize)

Key steps (draft, deepen, finalize) persist immediately to DB.
Non-key steps (dialogue, archaeology, reader_pull, anti_ai) can be skipped
or rerun from checkpoints.
"""
import json
from dataclasses import dataclass, field
from typing import Any, Callable

from ..domain.models import AiWorkflowIn
from ..infrastructure.database import (
    connect,
    create_chapter_bridge,
    create_dialogue_map,
    create_emotion_seed,
    create_reader_pull_report,
    create_step,
    get_emotion_seed,
    new_id,
    row_to_dict,
    update_step,
    utc_now,
)
from ..application.context_builder import build_generation_context
from ..workflows.llm_client import run_model_or_stub
from .quality import validate_chapter_prose

# Steps that MUST run (cannot be skipped)
REQUIRED_STEPS = {"brief", "seed", "draft", "archaeology", "deepen", "finalize"}
# Steps that persist output to DB immediately on success
KEY_PERSIST_STEPS = {"draft", "deepen", "finalize"}


@dataclass
class ChapterContext:
    """Per-chapter execution context carried through the pipeline."""
    project_id: str
    chapter_id: str
    chapter_number: int
    target_words: int = 3000
    target_chapter_count: int = 1
    is_final_chapter: bool = False
    ending_required: bool = False
    blueprint: dict[str, Any] = field(default_factory=dict)
    narrative_memory: list[dict[str, Any]] = field(default_factory=list)
    # Accumulated outputs
    brief: dict[str, Any] = field(default_factory=dict)
    emotion_seed: dict[str, Any] = field(default_factory=dict)
    draft: str = ""
    dialogue_map: dict[str, Any] = field(default_factory=dict)
    archaeology: dict[str, Any] = field(default_factory=dict)
    reader_pull: dict[str, Any] = field(default_factory=dict)
    revised_text: str = ""
    summary: str = ""
    bridge: dict[str, Any] = field(default_factory=dict)


# Step definitions: (name, workflow, required)
PIPELINE_STEPS: list[tuple[str, str, bool]] = [
    ("brief", "generate_chapter_brief", True),
    ("seed", "generate_emotion_seed", True),
    ("draft", "generate_chapter_draft", True),
    ("dialogue", "dialogue_subtext_excavation", False),
    ("archaeology", "emotion_archaeology", True),
    ("reader_pull", "analyze_reader_pull", False),
    ("deepen", "deepen_and_bury", True),
    ("anti_ai", "anti_ai_polish", False),
    ("finalize", "summarize_and_bridge", True),
]


class StoryPipeline:
    """Nine-step chapter generation pipeline."""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id

    def run(
        self,
        ctx: ChapterContext,
        skip_steps: set[str] | None = None,
        on_step: Callable[[str, str, dict[str, Any] | None], None] | None = None,
    ) -> ChapterContext:
        """Run the nine-step pipeline for one chapter.

        Args:
            ctx: Chapter execution context.
            skip_steps: Step names to skip (e.g. {"dialogue", "anti_ai"}).
            on_step: Callback(step_name, status, data) for progress reporting.

        Returns:
            Updated ChapterContext with all outputs.
        """
        skip = skip_steps or set()

        for step_name, workflow, required in PIPELINE_STEPS:
            if step_name in skip and not required:
                self._notify(on_step, step_name, "skipped")
                continue

            step_record = create_step(
                self.job_id, ctx.project_id, ctx.chapter_id, ctx.chapter_number, step_name
            )
            self._notify(on_step, step_name, "running")

            try:
                update_step(step_record["id"], "running")
                output = self._execute_step(step_name, workflow, ctx)
                self._validate_step_output(step_name, output)
                update_step(step_record["id"], "completed", output)
                self._notify(on_step, step_name, "completed", output)
                self._apply_output(step_name, ctx, output)

                # Key steps persist immediately
                if step_name in KEY_PERSIST_STEPS:
                    self._persist_key_step(step_name, ctx)

            except Exception as exc:
                update_step(step_record["id"], "failed", error=str(exc))
                self._notify(on_step, step_name, "failed", {"error": str(exc)})
                if required:
                    raise
                # Non-required step failure: continue
                continue

        return ctx

    def _execute_step(self, step_name: str, workflow: str, ctx: ChapterContext) -> dict[str, Any]:
        """Execute a single pipeline step by calling the LLM workflow."""
        # Build generation context for this chapter
        gen_context = build_generation_context(ctx.project_id, ctx.chapter_id)
        gen_context["generation_contract"] = {
            "target_chapter_count": ctx.target_chapter_count,
            "is_final_chapter": ctx.is_final_chapter,
            "ending_required": ctx.ending_required,
            "final_chapter_instruction": (
                "这是本次托管任务的最后一章，必须收束主要冲突和情感债务，"
                "不得写成未完待续，不得只留下下一章钩子。"
                if ctx.is_final_chapter or ctx.ending_required
                else ""
            ),
        }

        # Inject narrative memory into context (v4 horizontal feedback)
        if ctx.narrative_memory:
            memory_lines = [m.get("memory_content", "") for m in ctx.narrative_memory if m.get("memory_content")]
            if memory_lines:
                gen_context["narrative_memory"] = "\n".join(memory_lines[:5])

        # Inject voice prints for draft step (v4 character voice consistency)
        if step_name == "draft":
            from ..application.voice_print_service import inject_voice_prints_into_context
            gen_context = inject_voice_prints_into_context(gen_context, ctx.project_id)

        # Build payload
        payload = AiWorkflowIn(
            chapter_id=ctx.chapter_id,
            content=ctx.draft if step_name in {"deepen", "anti_ai", "archaeology", "dialogue", "reader_pull", "finalize"} else "",
            prompt="",
        )

        # For draft step, auto-generate seed first if missing
        if step_name == "draft" and ctx.chapter_id:
            existing = get_emotion_seed(ctx.project_id, ctx.chapter_id)
            if not existing:
                try:
                    seed_payload = AiWorkflowIn(chapter_id=ctx.chapter_id, prompt="", content="")
                    seed_output = run_model_or_stub(ctx.project_id, "generate_emotion_seed", seed_payload, gen_context)
                    seed_structured = seed_output.get("structured") or {}
                    if isinstance(seed_structured, dict) and seed_structured.get("emotion_seed"):
                        create_emotion_seed(ctx.project_id, ctx.chapter_id, seed_structured["emotion_seed"])
                        gen_context = build_generation_context(ctx.project_id, ctx.chapter_id)
                except Exception:
                    pass  # Seed failure doesn't block draft

        output = run_model_or_stub(ctx.project_id, workflow, payload, gen_context)
        return output

    def _validate_step_output(self, step_name: str, output: dict[str, Any]) -> None:
        if step_name == "draft":
            report = validate_chapter_prose(output.get("text", ""))
        elif step_name == "deepen":
            structured = output.get("structured") if isinstance(output.get("structured"), dict) else {}
            revised = structured.get("revised_text") or output.get("text", "")
            report = validate_chapter_prose(revised)
        else:
            return
        if not report.ok:
            raise ValueError("正文质量检查失败：" + "；".join(report.issues))

    def _apply_output(self, step_name: str, ctx: ChapterContext, output: dict[str, Any]) -> None:
        """Apply workflow output to the chapter context."""
        structured = output.get("structured") or {}

        if step_name == "brief":
            ctx.brief = structured if isinstance(structured, dict) else {}
            # Update chapter title/brief in DB
            self._update_chapter_meta(ctx, structured)

        elif step_name == "seed":
            if isinstance(structured, dict) and structured.get("emotion_seed"):
                ctx.emotion_seed = structured["emotion_seed"]
                create_emotion_seed(ctx.project_id, ctx.chapter_id, ctx.emotion_seed)

        elif step_name == "draft":
            ctx.draft = output.get("text", "")
            self._update_chapter_draft(ctx, ctx.draft)

        elif step_name == "dialogue":
            ctx.dialogue_map = structured if isinstance(structured, dict) else {}
            # Persist dialogue map
            create_dialogue_map(ctx.project_id, ctx.chapter_id, ctx.dialogue_map)

        elif step_name == "archaeology":
            ctx.archaeology = structured if isinstance(structured, dict) else {}

        elif step_name == "reader_pull":
            ctx.reader_pull = structured if isinstance(structured, dict) else {}
            # Persist reader pull report
            create_reader_pull_report(ctx.project_id, ctx.chapter_id, ctx.reader_pull)

        elif step_name == "deepen":
            revised = ""
            if isinstance(structured, dict):
                revised = structured.get("revised_text", "")
            if not revised:
                revised = output.get("text", "")
            if revised:
                ctx.revised_text = revised
                ctx.draft = revised
                self._update_chapter_draft(ctx, revised)

        elif step_name == "anti_ai":
            revised = ""
            if isinstance(structured, dict):
                revised = structured.get("revised_text", "")
            if not revised:
                revised = output.get("text", "")
            if revised:
                ctx.draft = revised
                self._update_chapter_draft(ctx, revised)

        elif step_name == "finalize":
            text = output.get("text", "")
            ctx.summary = text[:300] if text else ""
            bridge = structured if isinstance(structured, dict) else {}
            if bridge.get("ending_state"):
                ctx.bridge = bridge
                bridge.pop("_chapter_id", None)
                bridge.pop("_chapter_number", None)
                create_chapter_bridge(ctx.project_id, ctx.chapter_id, ctx.chapter_number, bridge)

    def _persist_key_step(self, step_name: str, ctx: ChapterContext) -> None:
        """Persist key step output immediately (auto-save policy)."""
        # draft and deepen already persisted in _apply_output via _update_chapter_draft
        # finalize already persisted bridge in _apply_output
        pass  # Persistence happens in _apply_output

    def _update_chapter_meta(self, ctx: ChapterContext, brief: dict[str, Any]) -> None:
        """Update chapter title and brief from outline generation."""
        if not isinstance(brief, dict):
            return
        title = brief.get("chapter_title", "")
        chapter_goal = brief.get("chapter_goal", "")
        now = utc_now()
        with connect() as conn:
            conn.execute(
                "UPDATE chapters SET title = ?, brief = ?, updated_at = ? WHERE id = ?",
                (title, chapter_goal, now, ctx.chapter_id),
            )

    def _update_chapter_draft(self, ctx: ChapterContext, draft: str) -> None:
        """Update chapter draft text and word count."""
        now = utc_now()
        with connect() as conn:
            conn.execute(
                "UPDATE chapters SET draft = ?, word_count = ?, updated_at = ? WHERE id = ?",
                (draft, len(draft), now, ctx.chapter_id),
            )

    def _notify(
        self,
        on_step: Callable | None,
        step_name: str,
        status: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        if on_step:
            on_step(step_name, status, data or {})
