"""Quality gates for generated chapter prose."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DraftQualityReport:
    ok: bool
    issues: list[str] = field(default_factory=list)


def validate_chapter_prose(text: str, min_chars: int = 220) -> DraftQualityReport:
    """Validate that text looks like publishable prose, not outline/advice."""
    issues: list[str] = []
    stripped = text.strip()
    if len(stripped) < min_chars:
        issues.append(f"正文过短：{len(stripped)} < {min_chars}")
    if not stripped:
        issues.append("正文为空")
        return DraftQualityReport(False, issues)

    if _looks_like_json(stripped):
        issues.append("正文像 JSON/结构化输出")

    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    bullet_lines = [line for line in lines if re.match(r"^([-*+]|\d+[.、)]|[一二三四五六七八九十]+[、.])\s*", line)]
    if len(lines) >= 4 and len(bullet_lines) / len(lines) >= 0.45:
        issues.append("正文像列表/大纲")

    outline_markers = [
        "本章目标",
        "主要冲突",
        "关键事件",
        "情绪节奏",
        "结尾钩子",
        "写作建议",
        "建议：",
        "可写成",
        "这一章应该",
        "需要描写",
        "角色弧线",
        "剧情板",
        "章节大纲",
    ]
    marker_hits = [marker for marker in outline_markers if marker in stripped]
    if len(marker_hits) >= 2:
        issues.append("正文含多个大纲/建议标记：" + "、".join(marker_hits[:4]))

    if re.search(r"```|^#{1,4}\s", stripped, re.MULTILINE):
        issues.append("正文含 Markdown/代码块结构")

    if "（stub）" in stripped or "(stub)" in stripped:
        issues.append("正文含占位符 stub")

    dialogue_marks = stripped.count("“") + stripped.count("”")
    narrative_punctuation = sum(stripped.count(mark) for mark in "，。；？！")
    if len(stripped) >= min_chars and narrative_punctuation < max(8, len(stripped) // 120):
        issues.append("正文叙事标点过少，疑似非小说正文")
    if len(stripped) >= min_chars and dialogue_marks == 0 and "：" in stripped and len(marker_hits) > 0:
        issues.append("正文缺少叙事/对话质感")

    return DraftQualityReport(not issues, issues)


def build_chapter_quality_report(
    chapter: dict[str, Any],
    bridge: dict[str, Any] | None = None,
    *,
    is_final_chapter: bool = False,
) -> dict[str, Any]:
    """Build a deterministic chapter quality report for autonomous generation."""
    draft = str(chapter.get("draft") or "")
    bridge_json = _bridge_json(bridge)
    prose_report = validate_chapter_prose(draft)
    issues = list(prose_report.issues)

    open_hooks = bridge_json.get("open_hooks") if isinstance(bridge_json, dict) else []
    if not isinstance(open_hooks, list):
        open_hooks = []
    has_final_open_hooks = bool(is_final_chapter and open_hooks)
    has_continuation_ending = bool(is_final_chapter and _looks_like_continuation_ending(draft))
    if has_final_open_hooks:
        issues.append(f"终章仍有未回收钩子：{len(open_hooks)}")

    if has_continuation_ending:
        issues.append("终章结尾仍像未完待续")

    repeated_fragments = _repeated_fragments(draft)
    if len(repeated_fragments) >= 6:
        issues.append(f"重复片段偏多：{len(repeated_fragments)}")

    score = 100
    score -= len(prose_report.issues) * 18
    if has_final_open_hooks:
        score -= min(35, len(open_hooks) * 12)
    if has_continuation_ending:
        score -= 30
    score -= min(20, max(0, len(repeated_fragments) - 2) * 3)
    score = max(0, min(100, score))

    return {
        "total_score": score,
        "ok": score >= 70 and not prose_report.issues and not has_final_open_hooks and not has_continuation_ending,
        "issues": issues,
        "metrics": {
            "char_count": len(draft),
            "open_hook_count": len(open_hooks),
            "repeated_fragment_count": len(repeated_fragments),
            "is_final_chapter": is_final_chapter,
        },
        "repeated_fragments": repeated_fragments[:10],
    }


def _looks_like_json(text: str) -> bool:
    if not ((text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]"))):
        return False
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return False
    return True


def _bridge_json(bridge: dict[str, Any] | None) -> dict[str, Any]:
    if not bridge:
        return {}
    bridge_json = bridge.get("bridge_json", bridge)
    if isinstance(bridge_json, str):
        try:
            bridge_json = json.loads(bridge_json)
        except json.JSONDecodeError:
            return {}
    return bridge_json if isinstance(bridge_json, dict) else {}


def _looks_like_continuation_ending(text: str) -> bool:
    tail = text.strip()[-260:]
    continuation_markers = [
        "下一章",
        "未完待续",
        "还没结束",
        "真正的开始",
        "更大的秘密",
        "等的不是天亮",
        "有人来找她要",
    ]
    return any(marker in tail for marker in continuation_markers)


def _repeated_fragments(text: str, width: int = 10) -> list[str]:
    normalized = re.sub(r"\s+", "", text)
    if len(normalized) < width * 3:
        return []
    counts: dict[str, int] = {}
    for index in range(0, len(normalized) - width + 1, width):
        fragment = normalized[index:index + width]
        if len(set(fragment)) <= 3:
            continue
        counts[fragment] = counts.get(fragment, 0) + 1
    return [fragment for fragment, count in counts.items() if count >= 2]
