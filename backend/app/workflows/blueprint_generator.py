"""Workflows: blueprint generator.

AI-powered blueprint generation: takes project settings + previous volume summary
and produces a complete blueprint JSON (volume arc / emotional climate / foreshadowings /
character arcs / recurring motifs / taboo list / generation params).

Uses the existing LLM client for AI generation, with stub fallback for offline/test mode.
"""
import json
import math
from typing import Any

from ..infrastructure.database import connect, row_to_dict


def generate_blueprint(
    project_id: str,
    volume_number: int,
    project_data: dict[str, Any],
    previous_volume_summary: str = "",
) -> dict[str, Any]:
    """Generate a complete blueprint via AI (with stub fallback).

    Args:
        project_id: Project UUID.
        volume_number: Volume number to generate (1-based).
        project_data: Project dict (title, genre, synopsis, etc.).
        previous_volume_summary: Summary of prior volumes (for continuity).

    Returns:
        Complete blueprint dict.
    """
    title = project_data.get("title", "未命名")
    genre = project_data.get("genre", "")
    synopsis = project_data.get("synopsis", "")
    target_chapter_count = int(project_data.get("target_chapter_count", 20))
    words_per_chapter = int(project_data.get("target_words_per_chapter", 3000))

    # Build context for LLM
    ctx = {
        "project_title": title,
        "genre": genre,
        "synopsis": synopsis[:500],
        "volume_number": volume_number,
        "target_chapter_count": target_chapter_count,
        "words_per_chapter": words_per_chapter,
        "previous_volume_summary": previous_volume_summary[:500],
    }

    # Try AI generation
    ai_text = _try_ai_generation(project_id, ctx)
    if ai_text:
        parsed = _parse_blueprint_json(ai_text, ctx)
        if parsed:
            return parsed

    # Fallback: generate a structured stub blueprint
    return _stub_blueprint(ctx)


def _try_ai_generation(project_id: str, ctx: dict[str, Any]) -> str | None:
    """Try to generate blueprint text via configured LLM. Returns None if no model configured."""
    import urllib.request
    import urllib.error

    from ..workflows.llm_client import resolve_model_config

    config = resolve_model_config(project_id, "generate_blueprint")
    if not config:
        return None

    config_payload = config.get("payload") if isinstance(config.get("payload"), dict) else {}
    api_key = str(config_payload.get("api_key") or "")
    base_url = str(config_payload.get("base_url") or "https://api.openai.com/v1").rstrip("/")
    model = str(config_payload.get("model_name") or config.get("title") or "")
    if not api_key or not model:
        return None

    system_prompt = _build_system_prompt(ctx)
    user_prompt = _build_user_prompt(ctx)
    request_body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def _build_system_prompt(ctx: dict[str, Any]) -> str:
    return (
        "You are an expert novel editor and story architect. "
        "Generate a complete volume blueprint in JSON format.\n\n"
        "The blueprint must include:\n"
        "1. volume_title: A poetic volume title in Chinese\n"
        "2. volume_arc: One paragraph describing the core arc of this volume\n"
        "3. chapter_range: {start, end} chapter numbers\n"
        "4. emotional_climate: Object mapping chapter numbers to tension levels (1-10)\n"
        "5. key_foreshadowings: Array of {name, planted_in, payoff_in, description}\n"
        "6. character_arcs: Array of {character, arc_summary}\n"
        "7. recurring_motifs: Array of motif strings that recur across chapters\n"
        "8. taboo_list: Array of things to avoid in this volume\n"
        "9. generation_params: {words_per_chapter}\n\n"
        "Return ONLY valid JSON, no markdown fences."
    )


def _build_user_prompt(ctx: dict[str, Any]) -> str:
    parts = [
        f"Project: {ctx['project_title']}",
        f"Genre: {ctx.get('genre', 'general')}",
        f"Volume: {ctx['volume_number']}",
        f"Total chapters: {ctx['target_chapter_count']}",
        f"Words per chapter: {ctx['words_per_chapter']}",
    ]
    if ctx.get("synopsis"):
        parts.append(f"Synopsis: {ctx['synopsis']}")
    if ctx.get("previous_volume_summary"):
        parts.append(f"Previous volume summary: {ctx['previous_volume_summary']}")
    parts.append("\nGenerate the complete blueprint JSON now.")
    return "\n".join(parts)


def _parse_blueprint_json(text: str, ctx: dict[str, Any]) -> dict[str, Any] | None:
    """Try to parse the LLM output as blueprint JSON."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)
    try:
        bp = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    if not isinstance(bp, dict):
        return None
    if "volume_title" not in bp:
        bp["volume_title"] = f"第{ctx['volume_number']}卷"
    if "chapter_range" not in bp:
        start = (ctx["volume_number"] - 1) * ctx["target_chapter_count"] + 1
        bp["chapter_range"] = {"start": start, "end": start + ctx["target_chapter_count"] - 1}
    if "generation_params" not in bp:
        bp["generation_params"] = {"words_per_chapter": ctx["words_per_chapter"]}
    return bp


def _stub_blueprint(ctx: dict[str, Any]) -> dict[str, Any]:
    """Generate a minimal blueprint when AI is unavailable."""
    vol = ctx["volume_number"]
    total = ctx["target_chapter_count"]
    wpc = ctx["words_per_chapter"]
    start = (vol - 1) * total + 1
    end = start + total - 1

    # Emotional climate: gentle sine curve
    climate = {}
    for i in range(total):
        ch = start + i
        tension = 4 + int(4 * abs(math.sin(i / max(total, 1) * 3.14)))
        climate[str(ch)] = tension

    # Foreshadowings: 2-3 per volume
    foreshadowings = [
        {
            "name": "隐藏信物",
            "planted_in": start,
            "payoff_in": end,
            "description": "主角在第一发现的一个看似不起眼的物品，在卷末揭示其重要性。",
        },
        {
            "name": "未解之谜",
            "planted_in": start + 1,
            "payoff_in": min(end, start + total // 2 + 2),
            "description": "一个令人困惑的事件，半卷后揭晓真相。",
        },
    ]

    return {
        "volume_number": vol,
        "volume_title": f"第{vol}卷",
        "volume_arc": f"第{vol}卷的主线推进，从第{start}章到第{end}章，逐步展开核心冲突。",
        "chapter_range": {"start": start, "end": end},
        "emotional_climate": climate,
        "key_foreshadowings": foreshadowings,
        "character_arcs": [
            {"character": "主角", "arc_summary": "从被动卷入到主动选择"},
        ],
        "recurring_motifs": ["月光", "旧信"],
        "taboo_list": [],
        "generation_params": {"words_per_chapter": wpc},
    }


def check_foreshadowing_plan(
    blueprint: dict[str, Any], chapter_number: int
) -> dict[str, list]:
    """Check which foreshadowings should be planted or paid off in this chapter.

    Args:
        blueprint: Blueprint dict with key_foreshadowings list.
        chapter_number: Current chapter number.

    Returns:
        {"plant": [...], "payoff": [...]} lists of foreshadowing dicts.
    """
    foreshadowings = blueprint.get("key_foreshadowings", [])
    to_plant = []
    to_payoff = []

    for f in foreshadowings:
        if not isinstance(f, dict):
            continue
        planted_in = f.get("planted_in")
        payoff_in = f.get("payoff_in")
        status = f.get("status", "planned")

        if planted_in == chapter_number and status == "planned":
            to_plant.append(f)
        elif payoff_in == chapter_number and status == "planted":
            to_payoff.append(f)

    return {"plant": to_plant, "payoff": to_payoff}
