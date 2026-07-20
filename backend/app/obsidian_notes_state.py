from collections import defaultdict
from typing import Any

from .obsidian_notes_core import note_path, record
from .obsidian_render import bullet_lines, frontmatter, wikilink


def render_state(files: dict[str, dict[str, Any]], data: dict[str, Any], ctx: dict[str, Any]) -> None:
    render_foreshadowings(files, data, ctx)
    render_debts(files, data, ctx)
    render_items(files, data, ctx)
    render_impacts(files, data, ctx)
    render_plans(files, data, ctx)


def render_foreshadowings(files: dict, data: dict, ctx: dict) -> None:
    links = []
    for row in data["latest_foreshadowings"]:
        key = str(row.get("foreshadowing_key") or "unknown")
        title = row.get("title") or row.get("description") or key
        path = note_path("07-伏笔", title, key)
        links.append(wikilink(path, title))
        page = frontmatter({"type": "foreshadowing", "key": key, "status": row.get("status", "planted"), "setup_chapter": row.get("setup_chapter", 0), "payoff_chapter": row.get("payoff_chapter", 0), "priority": row.get("priority", 0), "tags": ctx["tags"] + ["foreshadowing"]})
        page += f"# {title}\n\n{row.get('description') or ''}\n\n- 状态：{row.get('status') or 'planted'}\n- 埋设章节：{row.get('setup_chapter') or 0}\n- 回收章节：{row.get('payoff_chapter') or 0}\n"
        files[path] = record(page, "foreshadowing", key)
    overview = frontmatter({"type": "index", "tags": ctx["tags"] + ["foreshadowing"]}) + "# 伏笔总览\n\n" + bullet_lines(links)
    files["07-伏笔/伏笔总览.md"] = record(overview, "index", "foreshadowings")


def render_debts(files: dict, data: dict, ctx: dict) -> None:
    links = []
    for row in data["latest_debts"]:
        key = str(row.get("debt_key") or "unknown")
        title = row.get("description") or key
        path = note_path("08-叙事债务", title, key)
        links.append(wikilink(path, title))
        page = frontmatter({"type": "narrative-debt", "key": key, "debt_type": row.get("debt_type", "open_question"), "status": row.get("status", "open"), "priority": row.get("priority", 0), "deadline_chapter": row.get("deadline_chapter", 0), "tags": ctx["tags"] + ["narrative-debt"]})
        page += f"# {title}\n\n- 状态：{row.get('status') or 'open'}\n- 类型：{row.get('debt_type') or 'open_question'}\n- 优先级：{row.get('priority') or 0}\n- 截止章节：{row.get('deadline_chapter') or 0}\n"
        files[path] = record(page, "narrative-debt", key)
    overview = frontmatter({"type": "index", "tags": ctx["tags"] + ["narrative-debt"]}) + "# 叙事债务总览\n\n" + bullet_lines(links)
    files["08-叙事债务/债务总览.md"] = record(overview, "index", "narrative-debts")


def render_items(files: dict, data: dict, ctx: dict) -> None:
    ownership = {str(row.get("item_key") or ""): row for row in data["latest_ownership"]}
    links = []
    for row in data["latest_items"]:
        key = str(row.get("item_key") or "unknown")
        title = row.get("item_name") or key
        path = note_path("09-物品", title, key)
        links.append(wikilink(path, title))
        owner = ownership.get(key, {})
        page = frontmatter({"type": "item", "key": key, "status": row.get("status", "active"), "owner": owner.get("owner_name", ""), "location": owner.get("location", ""), "tags": ctx["tags"] + ["item"]})
        page += f"# {title}\n\n{row.get('description') or ''}\n\n- 状态：{row.get('status') or 'active'}\n- 当前持有者：{owner.get('owner_name') or '未知'}\n- 所在地点：{owner.get('location') or '未知'}\n- 所有权状态：{owner.get('status') or 'unknown'}\n"
        files[path] = record(page, "item", key)
    overview = frontmatter({"type": "index", "tags": ctx["tags"] + ["item"]}) + "# 物品总览\n\n" + bullet_lines(links)
    files["09-物品/物品总览.md"] = record(overview, "index", "items")


def render_impacts(files: dict, data: dict, ctx: dict) -> None:
    targets, observations = defaultdict(list), defaultdict(list)
    for row in data["impact_targets"]:
        targets[str(row.get("run_id") or "")].append(row)
    for row in data["impact_observations"]:
        observations[str(row.get("run_id") or "")].append(row)
    links = []
    for run in data["impact_runs"]:
        number = int(run.get("chapter_number") or 0)
        path = f"10-影响传播/第{number:03d}章 · 影响传播.md"
        links.append(wikilink(path, f"第 {number} 章影响传播"))
        page = frontmatter({"type": "impact-run", "chapter": number, "max_depth": run.get("max_depth", 3), "threshold": run.get("threshold", 0.15), "tags": ctx["tags"] + ["impact"]})
        page += f"# 第 {number} 章影响传播\n\n{run.get('summary') or ''}\n\n"
        if number in ctx["chapter_paths"]:
            page += f"- 来源章节：{wikilink(ctx['chapter_paths'][number])}\n\n"
        page += "## 传播目标\n\n"
        for target in targets.get(str(run.get("id") or ""), []):
            target_type, target_key = target.get("target_type") or "unknown", str(target.get("target_key") or "")
            link = target_key
            if target_type == "node" and target_key in ctx["node_paths"]:
                link = wikilink(ctx["node_paths"][target_key], ctx["nodes"].get(target_key, {}).get("title") or target_key)
            if target_type == "thread" and target_key in ctx["thread_paths"]:
                link = wikilink(ctx["thread_paths"][target_key], ctx["threads"].get(target_key, {}).get("title") or target_key)
            page += f"- {link}：分数 {target.get('impact_score') or 0}，深度 {target.get('depth') or 0}，路径 {' → '.join(target.get('path') or [])}\n"
        page += "\n## 规划观察\n\n" + bullet_lines([f"[{row.get('severity') or 'medium'}] {row.get('message') or ''} — {row.get('recommended_action') or ''}" for row in observations.get(str(run.get("id") or ""), [])])
        files[path] = record(page, "impact-run", str(run.get("id") or number))
    overview = frontmatter({"type": "index", "tags": ctx["tags"] + ["impact"]}) + "# 影响传播记录\n\n" + bullet_lines(links)
    files["10-影响传播/影响总览.md"] = record(overview, "index", "impact")


def render_plans(files: dict, data: dict, ctx: dict) -> None:
    links = []
    for row in data["rolling_plan_items"]:
        number = int(row.get("chapter_number") or 0)
        path = f"11-滚动计划/第{number:03d}章 · 计划.md"
        links.append(wikilink(path, f"第 {number} 章计划"))
        primary = str(row.get("primary_thread_key") or "")
        page = frontmatter({"type": "rolling-plan", "chapter": number, "status": row.get("status", "planned"), "locked": bool(row.get("locked")), "risk_score": row.get("risk_score", 0), "tags": ctx["tags"] + ["rolling-plan"]})
        page += f"# 第 {number} 章滚动计划\n\n- 目标：{row.get('goal') or '未设置'}\n"
        if primary:
            page += f"- 主推进线：{wikilink(ctx['thread_paths'][primary], ctx['threads'].get(primary, {}).get('title') or primary) if primary in ctx['thread_paths'] else primary}\n"
        page += f"- 锁定：{'是' if row.get('locked') else '否'}\n- 风险分数：{row.get('risk_score') or 0}\n\n## 目标节点\n\n"
        page += bullet_lines([wikilink(ctx["node_paths"][key], ctx["nodes"].get(key, {}).get("title") or key) if key in ctx["node_paths"] else key for key in row.get("target_node_keys") or []])
        page += "\n\n## 必须处理\n\n" + bullet_lines(row.get("must_address") or [])
        page += "\n\n## 避免事项\n\n" + bullet_lines(row.get("avoid") or [])
        if row.get("rationale"):
            page += f"\n\n## 规划依据\n\n{row['rationale']}\n"
        files[path] = record(page, "rolling-plan", str(number))
    overview = frontmatter({"type": "index", "tags": ctx["tags"] + ["rolling-plan"]}) + "# 滚动计划总览\n\n" + bullet_lines(links)
    files["11-滚动计划/计划总览.md"] = record(overview, "index", "rolling-plan")
