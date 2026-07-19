from collections import defaultdict
from typing import Any

from .obsidian_render import bullet_lines, frontmatter, safe_name, wikilink


def record(content: str, source_type: str, source_key: str) -> dict[str, Any]:
    return {"content": content.encode("utf-8"), "source_type": source_type, "source_key": source_key}


def note_path(folder: str, title: Any, key: Any = "") -> str:
    suffix = f" · {safe_name(key)}" if key and safe_name(key) != safe_name(title) else ""
    return f"{folder}/{safe_name(title)}{suffix}.md"


def chapter_path(chapter: dict[str, Any]) -> str:
    number = int(chapter.get("chapter_number") or 0)
    title = safe_name(chapter.get("title") or f"第 {number} 章")
    return f"01-章节/第{number:03d}章 · {title}.md"


def tags_for(data: dict[str, Any]) -> list[str]:
    name = safe_name(data["worldline"].get("name") or "主世界线")
    return ["ai-novel", "worldline", f"worldline/{name}"]


def character_catalog(data: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    catalog: dict[str, dict[str, Any]] = {}
    for profile in data["character_profiles"]:
        payload = profile.get("payload") if isinstance(profile.get("payload"), dict) else {}
        name = str(profile.get("title") or payload.get("name") or "").strip()
        key = str(payload.get("character_key") or payload.get("id") or name).strip()
        if key or name:
            catalog[key or name] = {"name": name or key, "profile": profile, "state": {}, "knowledge": []}
    for state in data["latest_character_states"]:
        key = str(state.get("character_key") or state.get("character_id") or state.get("character_name") or "unknown")
        entry = catalog.setdefault(key, {"name": state.get("character_name") or key, "profile": {}, "state": {}, "knowledge": []})
        entry["state"] = state
        entry["name"] = state.get("character_name") or entry["name"]
    for knowledge in data["latest_character_knowledge"]:
        key = str(knowledge.get("character_key") or knowledge.get("character_id") or knowledge.get("character_name") or "unknown")
        entry = catalog.setdefault(key, {"name": knowledge.get("character_name") or key, "profile": {}, "state": {}, "knowledge": []})
        entry["knowledge"].append(knowledge)
    return catalog, {key: note_path("02-人物", entry["name"], key) for key, entry in catalog.items()}


def initialize_context(data: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    chapters = data["chapters"]
    threads = {str(row.get("thread_key") or ""): row for row in data["story_threads"] if row.get("thread_key")}
    nodes = {str(row.get("node_key") or ""): row for row in data["story_nodes"] if row.get("node_key")}
    characters, character_paths = character_catalog(data)
    context = {
        "tags": tags_for(data),
        "chapter_paths": {int(row.get("chapter_number") or 0): chapter_path(row) for row in chapters},
        "threads": threads,
        "thread_paths": {key: note_path("04-剧情线", row.get("title") or key, key) for key, row in threads.items()},
        "nodes": nodes,
        "node_paths": {key: note_path("05-剧情节点", row.get("title") or key, key) for key, row in nodes.items()},
        "characters": characters,
        "character_paths": character_paths,
        "progress_by_chapter": defaultdict(list),
        "bridge_by_chapter": {int(row.get("chapter_number") or 0): row for row in data["chapter_bridges"]},
    }
    for progress in data["chapter_story_progress"]:
        context["progress_by_chapter"][int(progress.get("chapter_number") or 0)].append(progress)
    files: dict[str, dict[str, Any]] = {}
    render_project_pages(files, data, context)
    render_chapters(files, data, context)
    render_characters(files, data, context)
    render_relationships(files, data, context)
    return files, context


def render_project_pages(files: dict, data: dict, ctx: dict) -> None:
    project, worldline, tags = data["project"], data["worldline"], ctx["tags"]
    readme = frontmatter({"type": "obsidian-vault", "project_id": project["id"], "worldline_id": worldline.get("id", ""), "worldline": worldline.get("name", "主世界线"), "tags": tags})
    readme += f"# {project.get('title') or 'AI 小说项目'}\n\n> 当前世界线：**{worldline.get('name') or '主世界线'}**\n\n"
    readme += "从 [[00-首页/主页]] 开始浏览。剧情网络位于 `Canvas/剧情网络.canvas`，世界线总览位于 `Canvas/世界线总览.canvas`。\n"
    files["README.md"] = record(readme, "vault", str(worldline.get("id") or project["id"]))

    home = frontmatter({"type": "index", "project_id": project["id"], "worldline_id": worldline.get("id", ""), "tags": tags + ["index"]})
    home += f"# {project.get('title') or 'AI 小说项目'} · {worldline.get('name') or '主世界线'}\n\n{worldline.get('description') or '当前世界线知识库。'}\n\n"
    home += "## 项目信息\n\n"
    home += f"- 类型：{project.get('genre') or '未设置'}\n- 语气：{project.get('tone') or '未设置'}\n- 目标章节：{project.get('target_chapter_count') or 0}\n- 当前章节：{len(data['chapters'])}\n"
    home += f"- 主世界线：{'是' if worldline.get('is_primary') else '否'}\n- 当前激活：{'是' if worldline.get('is_active') else '否'}\n\n## 导航\n\n"
    home += bullet_lines([
        wikilink("00-首页/章节目录", "章节目录"), wikilink("00-首页/人物目录", "人物目录"),
        wikilink("00-首页/剧情线目录", "剧情线目录"), wikilink("00-首页/剧情节点目录", "剧情节点目录"),
        wikilink("06-时间线/时间线总览", "时间线"), wikilink("07-伏笔/伏笔总览", "伏笔"),
        wikilink("08-叙事债务/债务总览", "叙事债务"), wikilink("11-滚动计划/计划总览", "滚动计划"),
    ])
    files["00-首页/主页.md"] = record(home, "index", "home")

    line = frontmatter({"type": "worldline", "worldline_id": worldline.get("id", ""), "project_id": project["id"], "status": worldline.get("status", "active"), "fork_chapter": worldline.get("fork_chapter_number", 0), "tags": tags})
    line += f"# 世界线：{worldline.get('name') or '主世界线'}\n\n{worldline.get('description') or '项目原始世界线。'}\n\n"
    line += f"- 内部项目 ID：`{project['id']}`\n- 父世界线：`{worldline.get('parent_worldline_id') or '无'}`\n- 分叉章节：{worldline.get('fork_chapter_number') or 0}\n"
    line += f"- 主世界线：{'是' if worldline.get('is_primary') else '否'}\n- 激活世界线：{'是' if worldline.get('is_active') else '否'}\n"
    files["00-首页/世界线.md"] = record(line, "worldline", str(worldline.get("id") or project["id"]))


def render_chapters(files: dict, data: dict, ctx: dict) -> None:
    chapters, paths, tags = data["chapters"], ctx["chapter_paths"], ctx["tags"]
    index = frontmatter({"type": "index", "tags": tags + ["chapters"]}) + "# 章节目录\n\n"
    index += bullet_lines([wikilink(paths[int(row.get("chapter_number") or 0)], f"第 {row.get('chapter_number')} 章 · {row.get('title') or ''}") for row in chapters])
    files["00-首页/章节目录.md"] = record(index, "index", "chapters")
    for chapter in chapters:
        number = int(chapter.get("chapter_number") or 0)
        page = frontmatter({"type": "chapter", "chapter": number, "status": chapter.get("status", "draft"), "word_count": chapter.get("word_count", 0), "project_id": data["project"]["id"], "worldline_id": data["worldline"].get("id", ""), "tags": tags + ["chapter"]})
        page += f"# 第 {number} 章 · {chapter.get('title') or '未命名'}\n\n"
        if chapter.get("brief"): page += f"> **章节目标**：{chapter['brief']}\n\n"
        if chapter.get("summary"): page += f"## 摘要\n\n{chapter['summary']}\n\n"
        page += f"## 正文\n\n{chapter.get('draft') or '尚无正文。'}\n\n"
        rows = ctx["progress_by_chapter"].get(number, [])
        if rows:
            page += "## 本章推进\n\n"
            for row in rows:
                key = str(row.get("thread_key") or "")
                title = ctx["threads"].get(key, {}).get("title") or key
                link = wikilink(ctx["thread_paths"][key], title) if key in ctx["thread_paths"] else key
                page += f"- {link}：{row.get('progress_summary') or row.get('progress_type') or '推进'}\n"
            page += "\n"
        bridge = ctx["bridge_by_chapter"].get(number, {}).get("payload") or {}
        ending = bridge.get("ending_state") if isinstance(bridge.get("ending_state"), dict) else {}
        if ending:
            page += "## 章节结束状态\n\n"
            for label, field in (("时间", "time"), ("地点", "location"), ("行动", "current_action"), ("危险", "current_danger")):
                if ending.get(field): page += f"- {label}：{ending[field]}\n"
        files[paths[number]] = record(page, "chapter", str(chapter.get("id") or number))


def render_characters(files: dict, data: dict, ctx: dict) -> None:
    characters, paths, tags = ctx["characters"], ctx["character_paths"], ctx["tags"]
    index = frontmatter({"type": "index", "tags": tags + ["characters"]}) + "# 人物目录\n\n"
    index += bullet_lines([wikilink(paths[key], entry["name"]) for key, entry in sorted(characters.items())])
    files["00-首页/人物目录.md"] = record(index, "index", "characters")
    for key, entry in characters.items():
        state, profile = entry.get("state") or {}, entry.get("profile") or {}
        page = frontmatter({"type": "character", "character_key": key, "name": entry["name"], "alive_status": state.get("alive_status", "unknown"), "tags": tags + ["character"]})
        page += f"# {entry['name']}\n\n"
        if profile.get("content"): page += f"## 人物设定\n\n{profile['content']}\n\n"
        page += "## 当前状态\n\n" + bullet_lines([
            f"位置：{state.get('location')}" if state.get("location") else "",
            f"身体：{state.get('physical_state')}" if state.get("physical_state") else "",
            f"情绪：{state.get('emotional_state')}" if state.get("emotional_state") else "",
            f"目标：{state.get('current_goal')}" if state.get("current_goal") else "",
        ])
        page += "\n\n## 知识边界\n\n" + bullet_lines([
            f"{row.get('fact_text') or row.get('fact_key')}（{row.get('knowledge_status') or 'unknown'}，置信度 {row.get('confidence') or 0}）"
            for row in entry.get("knowledge") or []
        ])
        files[paths[key]] = record(page, "character", key)


def render_relationships(files: dict, data: dict, ctx: dict) -> None:
    links, tags = [], ctx["tags"]
    for row in data["latest_relationship_states"]:
        source_key = str(row.get("source_character_key") or row.get("source_character_name") or "未知")
        target_key = str(row.get("target_character_key") or row.get("target_character_name") or "未知")
        source_name = row.get("source_character_name") or ctx["characters"].get(source_key, {}).get("name") or source_key
        target_name = row.get("target_character_name") or ctx["characters"].get(target_key, {}).get("name") or target_key
        title = f"{source_name} → {target_name} · {row.get('relation_type') or '关系'}"
        path = note_path("03-人物关系", title, f"{source_key}-{target_key}-{row.get('relation_type')}")
        links.append(wikilink(path, title))
        page = frontmatter({"type": "relationship", "source": source_name, "target": target_name, "relation_type": row.get("relation_type", ""), "status": row.get("status", "active"), "value": row.get("value", 0), "tags": tags + ["relationship"]})
        page += f"# {title}\n\n"
        page += f"- 来源人物：{wikilink(ctx['character_paths'][source_key], source_name) if source_key in ctx['character_paths'] else source_name}\n"
        page += f"- 目标人物：{wikilink(ctx['character_paths'][target_key], target_name) if target_key in ctx['character_paths'] else target_name}\n"
        page += f"- 当前值：{row.get('value') or 0}\n- 状态：{row.get('status') or 'active'}\n"
        if row.get("reason"): page += f"\n## 变化原因\n\n{row['reason']}\n"
        files[path] = record(page, "relationship", f"{source_key}|{target_key}|{row.get('relation_type')}")
    overview = frontmatter({"type": "index", "tags": tags + ["relationships"]}) + "# 人物关系\n\n" + bullet_lines(links)
    files["03-人物关系/关系总览.md"] = record(overview, "index", "relationships")
