from typing import Any

from .obsidian_canvas import story_canvas, worldline_canvas
from .obsidian_notes_core import initialize_context, record
from .obsidian_notes_state import render_state
from .obsidian_notes_story import render_story
from .obsidian_render import json_text


def build_obsidian_files(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    files, context = initialize_context(data)
    render_story(files, data, context)
    render_state(files, data, context)
    files["Canvas/剧情网络.canvas"] = record(
        json_text(story_canvas(context, data["story_edges"])),
        "canvas",
        "story-graph",
    )
    files["Canvas/世界线总览.canvas"] = record(
        json_text(worldline_canvas(data, context)),
        "canvas",
        "worldline-overview",
    )
    return files
