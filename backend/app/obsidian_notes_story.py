from collections import defaultdict
from typing import Any

from .obsidian_notes_core import record
from .obsidian_render import bullet_lines, frontmatter, wikilink


def render_story(files: dict[str, dict[str, Any]], data: dict[str, Any], ctx: dict[str, Any]) -> None:
    render_threads(files, data, ctx)
    render_nodes(files, data, ctx)
    render_timeline(files, data, ctx)


def render_threads(files: dict, data: dict, ctx: dict) -> None:
    threads, paths, tags = ctx["threads"], ctx["thread_paths"], ctx["tags"]
    index = frontmatter({"type": "index", "tags": tags + ["story-thread"]}) + "# 剧情线目录\n\n"
    index += bullet_lines([wikilink(paths[key], row.get("title") or key) for key, row in threads.items()])
    files["00-首页/剧情线目录.md"] = record(index, "index", "story-threads")
    nodes_by_thread: dict[str, list[dict]] = defaultdict(list)
    for node in ctx["nodes"].values():
        nodes_by_thread[str(node.get("thread_key") or "")].append(node)
    for key, row in threads.items():
        page = frontmatter({"type": "story-thread", "thread_key": key, "thread_type": row.get("thread_type", "subplot"), "status": row.get("status", "active"), "priority": row.get("priority", 0), "tags": tags + ["story-thread"]})
        page += f"# {row.get('title') or key}\n\n- 当前阶段：{row.get('current_stage') or '未设置'}\n- 当前目标：{row.get('current_goal') or '未设置'}\n"
        page += f"- 下一目标：{row.get('next_target') or '未设置'}\n- 最近推进章节：{row.get('last_progress_chapter') or 0}\n\n## 剧情节点\n\n"
        page += bullet_lines([wikilink(ctx["node_paths"][str(node.get("node_key"))], node.get("title") or node.get("node_key")) for node in nodes_by_thread.get(key, []) if str(node.get("node_key")) in ctx["node_paths"]])
        files[paths[key]] = record(page, "story-thread", key)


def render_nodes(files: dict, data: dict, ctx: dict) -> None:
    nodes, paths, tags = ctx["nodes"], ctx["node_paths"], ctx["tags"]
    index = frontmatter({"type": "index", "tags": tags + ["story-node"]}) + "# 剧情节点目录\n\n"
    index += bullet_lines([wikilink(paths[key], row.get("title") or key) for key, row in nodes.items()])
    files["00-首页/剧情节点目录.md"] = record(index, "index", "story-nodes")
    incoming, outgoing = defaultdict(list), defaultdict(list)
    for edge in data["story_edges"]:
        outgoing[str(edge.get("source_node_key") or "")].append(edge)
        incoming[str(edge.get("target_node_key") or "")].append(edge)
    for key, row in nodes.items():
        thread_key = str(row.get("thread_key") or "")
        page = frontmatter({"type": "story-node", "node_key": key, "node_type": row.get("node_type", "event"), "status": row.get("status", "planned"), "planned_chapter": row.get("planned_chapter", 0), "actual_chapter": row.get("actual_chapter", 0), "tags": tags + ["story-node"]})
        page += f"# {row.get('title') or key}\n\n{row.get('description') or ''}\n\n"
        if thread_key in ctx["thread_paths"]:
            page += f"- 所属剧情线：{wikilink(ctx['thread_paths'][thread_key], ctx['threads'].get(thread_key, {}).get('title') or thread_key)}\n"
        page += f"- 状态：{row.get('status') or 'planned'}\n- 重要度：{row.get('importance') or 0}\n- 计划章节：{row.get('planned_chapter') or 0}\n- 实际章节：{row.get('actual_chapter') or 0}\n\n"
        page += "## 前置关系\n\n" + bullet_lines([f"{edge.get('relation_type')} ← {wikilink(paths[str(edge.get('source_node_key'))], nodes.get(str(edge.get('source_node_key')), {}).get('title') or edge.get('source_node_key'))}" for edge in incoming.get(key, []) if str(edge.get("source_node_key")) in paths])
        page += "\n\n## 后续关系\n\n" + bullet_lines([f"{edge.get('relation_type')} → {wikilink(paths[str(edge.get('target_node_key'))], nodes.get(str(edge.get('target_node_key')), {}).get('title') or edge.get('target_node_key'))}" for edge in outgoing.get(key, []) if str(edge.get("target_node_key")) in paths])
        files[paths[key]] = record(page, "story-node", key)


def render_timeline(files: dict, data: dict, ctx: dict) -> None:
    page = frontmatter({"type": "timeline", "tags": ctx["tags"] + ["timeline"]}) + "# 时间线总览\n\n"
    for chapter in data["chapters"]:
        number = int(chapter.get("chapter_number") or 0)
        bridge = ctx["bridge_by_chapter"].get(number, {}).get("payload") or {}
        ending = bridge.get("ending_state") if isinstance(bridge.get("ending_state"), dict) else {}
        page += f"## {wikilink(ctx['chapter_paths'][number], f'第 {number} 章')}\n\n- 时间：{ending.get('time') or '未记录'}\n- 地点：{ending.get('location') or '未记录'}\n"
        page += f"- 结束行动：{ending.get('current_action') or chapter.get('summary') or '未记录'}\n\n"
    if data["timeline_events"]:
        page += "## 作者维护的时间线事件\n\n"
        for event in data["timeline_events"]:
            page += f"- **{event.get('title') or '事件'}**：{event.get('content') or ''}\n"
    files["06-时间线/时间线总览.md"] = record(page, "timeline", "timeline")
