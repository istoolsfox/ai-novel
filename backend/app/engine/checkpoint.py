"""Engine: checkpoint manager.

Controls when the orchestrator should pause for human review.
Two categories of pause:
  1. Scheduled checkpoints (every N chapters)
  2. Smart-stop (auto-pause on quality/rhythm issues)

v3 conditions (5):
  - Archaeology rupture points > 3
  - Unresolved hooks > 8
  - Word count deviation > 30%
  - Bridge continuity break
  - Summary overlap with volume memory > 60%

v4 conditions (2, emotional rhythm):
  - 3 consecutive high-tension chapters (fatigue risk)
  - 3 consecutive low-tension chapters (stagnation risk)
  - Emotional debt accumulation > 10
"""
import json
from typing import Any

from ..infrastructure.database import (
    connect,
    get_recent_reader_pull_reports,
    list_chapter_bridges,
    row_to_dict,
    rows_to_dicts,
)


class CheckpointManager:
    """Checkpoint + smart-stop decision maker."""

    def hit_checkpoint(self, strategy: str, offset: int) -> bool:
        """Return True if a scheduled checkpoint should trigger."""
        if strategy == "every_chapter":
            return True
        if strategy == "every_3":
            return (offset + 1) % 3 == 0
        if strategy == "every_5":
            return (offset + 1) % 5 == 0
        # "none" or unknown -> no checkpoint
        return False

    def should_smart_stop(self, project_id: str, ctx: dict[str, Any]) -> tuple[bool, str]:
        """Check all smart-stop conditions. Returns (should_stop, reason)."""
        # --- v3 conditions ---
        reason = self._check_rupture_points(ctx)
        if reason:
            return True, reason

        reason = self._check_hook_accumulation(project_id)
        if reason:
            return True, reason

        reason = self._check_word_count(ctx)
        if reason:
            return True, reason

        reason = self._check_bridge_continuity(project_id, ctx)
        if reason:
            return True, reason

        reason = self._check_summary_overlap(ctx)
        if reason:
            return True, reason

        # --- v4 emotional rhythm conditions ---
        reason = self._check_emotional_rhythm(project_id)
        if reason:
            return True, reason

        reason = self._check_emotional_debt(project_id)
        if reason:
            return True, reason

        return False, ""

    # ------------------------------------------------------------------
    # v3 conditions
    # ------------------------------------------------------------------
    def _check_rupture_points(self, ctx: dict[str, Any]) -> str:
        arch = ctx.get("archaeology")
        if not arch or not isinstance(arch, dict):
            return ""
        felt_map = arch.get("reader_felt_map") or {}
        ruptures = felt_map.get("rupture_points") or []
        if len(ruptures) > 3:
            return f"emotion archaeology rupture points {len(ruptures)} > 3"
        return ""

    def _check_hook_accumulation(self, project_id: str) -> str:
        bridges = list_chapter_bridges(project_id)
        total_hooks = 0
        for b in bridges:
            bj = b.get("bridge_json")
            if isinstance(bj, str):
                try:
                    bj = json.loads(bj)
                except json.JSONDecodeError:
                    bj = {}
            if isinstance(bj, dict):
                total_hooks += len(bj.get("open_hooks") or [])
        if total_hooks > 8:
            return f"unresolved hooks {total_hooks} > 8"
        return ""

    def _check_word_count(self, ctx: dict[str, Any]) -> str:
        target = ctx.get("target_words") or 0
        draft = ctx.get("draft") or ""
        actual = len(draft)
        tolerance = _float_in_range(ctx.get("word_count_tolerance"), default=0.6, minimum=0.1, maximum=1.0)
        if target and (actual < target * (1 - tolerance) or actual > target * (1 + tolerance)):
            return f"word count deviation: target {target}, actual {actual}, tolerance {tolerance:.0%}"
        return ""

    def _check_bridge_continuity(self, project_id: str, ctx: dict[str, Any]) -> str:
        chapter_number = ctx.get("chapter_number") or 0
        draft = ctx.get("draft") or ""
        if chapter_number <= 1 or not draft:
            return ""
        # Check if the opening mentions the previous chapter's location
        from ..infrastructure.database import get_previous_chapter_bridge
        prev_bridge = get_previous_chapter_bridge(project_id, chapter_number)
        if not prev_bridge:
            return ""
        bj = prev_bridge.get("bridge_json")
        if isinstance(bj, str):
            try:
                bj = json.loads(bj)
            except json.JSONDecodeError:
                bj = {}
        if isinstance(bj, dict):
            ending = bj.get("ending_state") or {}
            if isinstance(ending, dict):
                location = ending.get("location", "")
                if location and location not in draft[:500]:
                    return f"opening does not mention previous location '{location}' - possible continuity break"
        return ""

    def _check_summary_overlap(self, ctx: dict[str, Any]) -> str:
        summary = ctx.get("summary") or ""
        volume_memory = ctx.get("volume_memory")
        if not summary or not volume_memory:
            return ""
        vm_content = ""
        if isinstance(volume_memory, dict):
            vm_content = volume_memory.get("content", "")
        if vm_content and self._text_overlap_ratio(summary, vm_content) > 0.6:
            return "chapter summary overlaps volume memory > 60% - possible duplicate events"
        return ""

    # ------------------------------------------------------------------
    # v4 emotional rhythm conditions
    # ------------------------------------------------------------------
    def _check_emotional_rhythm(self, project_id: str) -> str:
        reports = get_recent_reader_pull_reports(project_id, count=3)
        if len(reports) < 3:
            return ""
        scores = [int(r.get("pull_score", 0)) for r in reports]
        # 3 consecutive high tension (fatigue risk)
        if all(s >= 8 for s in scores):
            return "3 consecutive high-tension chapters - consider a low-tension buffer chapter"
        # 3 consecutive low tension (stagnation risk)
        if all(s <= 3 for s in scores):
            return "3 consecutive low-tension chapters - consider advancing an emotional payoff"
        return ""

    def _check_emotional_debt(self, project_id: str) -> str:
        """Check if unresolved emotional debt has accumulated beyond threshold."""
        reports = get_recent_reader_pull_reports(project_id, count=10)
        total_debt = 0
        for r in reports:
            debt_json = r.get("emotional_debt", "[]")
            if isinstance(debt_json, str):
                try:
                    debt_json = json.loads(debt_json)
                except json.JSONDecodeError:
                    debt_json = []
            if isinstance(debt_json, list):
                total_debt += len(debt_json)
        if total_debt > 10:
            return f"emotional debt accumulation {total_debt} > 10 - consider resolving some"
        return ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _text_overlap_ratio(a: str, b: str) -> float:
        """Simple overlap ratio based on shared character bigrams."""
        if not a or not b:
            return 0.0
        bigrams_a = set(a[i:i+2] for i in range(len(a) - 1))
        bigrams_b = set(b[i:i+2] for i in range(len(b) - 1))
        if not bigrams_a:
            return 0.0
        return len(bigrams_a & bigrams_b) / len(bigrams_a)


def _float_in_range(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number < minimum or number > maximum:
        return default
    return number
