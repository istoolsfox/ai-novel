"""Quality gates for generated chapter prose."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


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


def _looks_like_json(text: str) -> bool:
    if not ((text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]"))):
        return False
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return False
    return True
