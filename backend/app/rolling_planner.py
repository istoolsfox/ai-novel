import json
from typing import Any

from .database import connect, new_id, row_to_dict, rows_to_dicts, utc_now
from .impact_engine import latest_impact_run
from .memory_store import latest_foreshadowings, latest_narrative_debts
from .story_graph_store import list_story_nodes, story_graph_context


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _list(value: Any) -> list:
    if isinstance(value, list): return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value); return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError: return []
    return []


def deserialize_plan_row(row: dict | None) -> dict | None:
    if not row: return None
    item = dict(row)
    for key in ("secondary_thread_keys", "target_node_keys", "must_address", "avoid"):
        item[key] = _list(item.get(key))
    item["locked"] = bool(item.get("locked"))
    return item


def _payload(item: dict | None) -> dict:
    if not item: return {}
    return {
        "chapter_number": int(item.get("chapter_number") or 0),
        "status": str(item.get("status") or "planned"),
        "locked": bool(item.get("locked")),
        "primary_thread_key": str(item.get("primary_thread_key") or ""),
        "secondary_thread_keys": list(item.get("secondary_thread_keys") or []),
        "target_node_keys": list(item.get("target_node_keys") or []),
        "goal": str(item.get("goal") or ""),
        "must_address": list(item.get("must_address") or []),
        "avoid": list(item.get("avoid") or []),
        "risk_score": round(float(item.get("risk_score") or 0), 4),
        "rationale": str(item.get("rationale") or ""),
    }


def get_plan_item(project_id: str, chapter_number: int) -> dict | None:
    with connect() as conn:
        row = row_to_dict(conn.execute("SELECT * FROM rolling_plan_items WHERE project_id = ? AND chapter_number = ?", (project_id, chapter_number)).fetchone())
    return deserialize_plan_row(row)


def list_current_plan(project_id: str, *, start_chapter: int = 0, end_chapter: int = 0) -> list[dict]:
    sql, params = "SELECT * FROM rolling_plan_items WHERE project_id = ?", [project_id]
    if start_chapter > 0: sql += " AND chapter_number >= ?"; params.append(start_chapter)
    if end_chapter > 0: sql += " AND chapter_number <= ?"; params.append(end_chapter)
    sql += " ORDER BY chapter_number"
    with connect() as conn: rows = rows_to_dicts(conn.execute(sql, tuple(params)).fetchall())
    return [deserialize_plan_row(row) for row in rows]


def list_plan_history(project_id: str, chapter_number: int = 0) -> list[dict]:
    sql, params = "SELECT * FROM rolling_plan_item_revisions WHERE project_id = ?", [project_id]
    if chapter_number > 0: sql += " AND chapter_number = ?"; params.append(chapter_number)
    sql += " ORDER BY created_at DESC"
    with connect() as conn: return rows_to_dicts(conn.execute(sql, tuple(params)).fetchall())


def _impact(project_id: str, chapter_id: str) -> dict:
    run = latest_impact_run(project_id, chapter_id)
    if not run: return {"run": {}, "targets": [], "observations": []}
    with connect() as conn:
        targets = rows_to_dicts(conn.execute("SELECT * FROM impact_targets WHERE run_id = ? ORDER BY impact_score DESC", (run["id"],)).fetchall())
        observations = rows_to_dicts(conn.execute("SELECT * FROM impact_observations WHERE run_id = ? ORDER BY created_at", (run["id"],)).fetchall())
    return {"run": run, "targets": targets, "observations": observations}


def _project_end(project_id: str, proposed: int) -> int:
    with connect() as conn:
        row = conn.execute("SELECT target_chapter_count FROM projects WHERE id = ?", (project_id,)).fetchone()
    target = int(row[0] or 0) if row else 0
    return min(proposed, target) if target > 0 else proposed


def _final_chapters(project_id: str) -> set[int]:
    with connect() as conn:
        return {int(row[0]) for row in conn.execute("SELECT chapter_number FROM chapters WHERE project_id = ? AND status = 'final'", (project_id,)).fetchall()}


def build_rolling_plan_proposal(project_id: str, source_chapter_id: str, source_chapter_number: int, *, window_size: int = 5) -> dict:
    window_size = max(3, min(int(window_size), 10))
    start, end = source_chapter_number + 1, _project_end(project_id, source_chapter_number + window_size)
    if end < start:
        return {"project_id": project_id, "source_chapter_id": source_chapter_id, "source_chapter_number": source_chapter_number, "source_impact_run_id": "", "window_start": start, "window_end": end, "items": [], "summary": "项目已到目标章节末尾，无需创建未来滚动计划。"}

    graph, impact = story_graph_context(project_id, current_chapter=start), _impact(project_id, source_chapter_id)
    node_scores, thread_scores = {}, {}
    for target in impact["targets"]:
        key, score = str(target.get("target_key") or ""), float(target.get("impact_score") or 0)
        (node_scores if target.get("target_type") == "node" else thread_scores)[key] = score
    focus = list(graph.get("story_focus") or graph.get("story_threads") or [])
    focus.sort(key=lambda row: (-(float(row.get("focus_score") or 0) + thread_scores.get(str(row.get("thread_key") or ""), 0)), -float(row.get("priority") or 0), str(row.get("thread_key") or "")))
    thread_keys = [str(row.get("thread_key") or "") for row in focus if row.get("thread_key")]
    nodes_by_thread: dict[str, list[dict]] = {}
    for node in list_story_nodes(project_id):
        if str(node.get("status") or "") not in {"planned", "active", "blocked"}: continue
        nodes_by_thread.setdefault(str(node.get("thread_key") or ""), []).append(node)
    for rows in nodes_by_thread.values():
        rows.sort(key=lambda row: (-node_scores.get(str(row.get("node_key") or ""), 0), abs(int(row.get("planned_chapter") or start) - start), -float(row.get("importance") or 0)))

    existing = {row["chapter_number"]: row for row in list_current_plan(project_id, start_chapter=start, end_chapter=end)}
    finals = _final_chapters(project_id)
    due_debts = [row for row in latest_narrative_debts(project_id, open_only=True) if not int(row.get("deadline_chapter") or 0) or int(row.get("deadline_chapter") or 0) <= source_chapter_number + 1]
    due_foreshadowings = [row for row in latest_foreshadowings(project_id, active_only=True) if int(row.get("payoff_chapter") or 0) and int(row.get("payoff_chapter") or 0) <= source_chapter_number + 2]
    high_observations = [row for row in impact["observations"] if str(row.get("severity") or "") in {"high", "critical"}]
    items = []
    for offset, chapter_number in enumerate(range(start, end + 1)):
        old = existing.get(chapter_number)
        if chapter_number in finals:
            if old: items.append({**_payload(old), "status": "completed", "locked": True, "action": "completed"})
            continue
        if old and old.get("locked"):
            items.append({**_payload(old), "action": "preserved_locked"}); continue
        primary = thread_keys[offset % len(thread_keys)] if thread_keys else ""
        nodes = nodes_by_thread.get(primary, [])
        target_keys = [str(row.get("node_key") or "") for row in nodes[:2] if row.get("node_key")]
        secondary = [key for key in thread_keys if key != primary][:2]
        thread = next((row for row in focus if str(row.get("thread_key") or "") == primary), {})
        target = nodes[0] if nodes else {}
        must = [str(row.get("description") or row.get("debt_key") or "") for row in due_debts[:2]]
        must += [f"伏笔：{row.get('title') or row.get('description') or row.get('foreshadowing_key')}" for row in due_foreshadowings[:1]]
        must += [str(row.get("message") or "") for row in high_observations[:2]]
        impacted = max([thread_scores.get(primary, 0)] + [node_scores.get(key, 0) for key in target_keys])
        candidate = {
            "chapter_number": chapter_number, "status": "planned", "locked": False,
            "primary_thread_key": primary, "secondary_thread_keys": secondary,
            "target_node_keys": target_keys,
            "goal": str(target.get("title") or target.get("description") or thread.get("next_target") or thread.get("current_goal") or "承接上一章结果，并推进当前最高优先级剧情线。"),
            "must_address": [item for item in must if item], "avoid": [],
            "risk_score": round(min(1.0, impacted * .55 + (.22 if due_debts else 0) + (.12 if due_foreshadowings else 0) + (.12 if graph.get("stalled_threads") else 0)), 4),
            "rationale": "按剧情优先级、停滞压力、影响传播和叙事债务共同排序。",
        }
        candidate["action"] = "created" if not old else ("unchanged" if _payload(old) == _payload(candidate) else "replanned")
        items.append(candidate)
    run = impact["run"]
    return {"project_id": project_id, "source_chapter_id": source_chapter_id, "source_chapter_number": source_chapter_number, "source_impact_run_id": str(run.get("id") or ""), "window_start": start, "window_end": end, "items": items, "summary": f"已重算第 {start}—{end} 章滚动计划，共 {len(items)} 个计划项。"}


def persist_rolling_plan(conn, proposal: dict) -> str:
    project_id, source_id, now = str(proposal["project_id"]), str(proposal["source_chapter_id"]), utc_now()
    snapshot = row_to_dict(conn.execute("SELECT * FROM rolling_plan_snapshots WHERE project_id = ? AND source_chapter_id = ?", (project_id, source_id)).fetchone())
    snapshot_id, snapshot_revision = (str(snapshot["id"]), int(snapshot.get("revision") or 0) + 1) if snapshot else (new_id(), 1)
    conn.execute("""
        INSERT INTO rolling_plan_snapshots (id, project_id, source_chapter_id, source_chapter_number, source_impact_run_id, window_start, window_end, revision, status, payload, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
        ON CONFLICT(project_id, source_chapter_id) DO UPDATE SET source_chapter_number=excluded.source_chapter_number, source_impact_run_id=excluded.source_impact_run_id, window_start=excluded.window_start, window_end=excluded.window_end, revision=excluded.revision, status='active', payload=excluded.payload, updated_at=excluded.updated_at
    """, (snapshot_id, project_id, source_id, int(proposal.get("source_chapter_number") or 0), str(proposal.get("source_impact_run_id") or ""), int(proposal.get("window_start") or 0), int(proposal.get("window_end") or 0), snapshot_revision, _json(proposal), now, now))
    for item in proposal.get("items") or []:
        chapter_number = int(item.get("chapter_number") or 0)
        if chapter_number <= 0: continue
        old = deserialize_plan_row(row_to_dict(conn.execute("SELECT * FROM rolling_plan_items WHERE project_id = ? AND chapter_number = ?", (project_id, chapter_number)).fetchone()))
        if old and old.get("locked") and item.get("action") != "completed": continue
        previous, current = _payload(old), _payload(item)
        changed, revision = previous != current, (int(old.get("revision") or 0) + 1 if old and previous != current else int(old.get("revision") or 1) if old else 1)
        item_id = str(old["id"]) if old else new_id()
        conn.execute("""
            INSERT INTO rolling_plan_items (id, project_id, chapter_number, status, locked, primary_thread_key, secondary_thread_keys, target_node_keys, goal, must_address, avoid, risk_score, source_snapshot_id, source_impact_run_id, revision, rationale, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id, chapter_number) DO UPDATE SET status=excluded.status, locked=excluded.locked, primary_thread_key=excluded.primary_thread_key, secondary_thread_keys=excluded.secondary_thread_keys, target_node_keys=excluded.target_node_keys, goal=excluded.goal, must_address=excluded.must_address, avoid=excluded.avoid, risk_score=excluded.risk_score, source_snapshot_id=excluded.source_snapshot_id, source_impact_run_id=excluded.source_impact_run_id, revision=excluded.revision, rationale=excluded.rationale, payload=excluded.payload, updated_at=excluded.updated_at
        """, (item_id, project_id, chapter_number, str(item.get("status") or "planned"), 1 if item.get("locked") else 0, str(item.get("primary_thread_key") or ""), _json(item.get("secondary_thread_keys") or []), _json(item.get("target_node_keys") or []), str(item.get("goal") or ""), _json(item.get("must_address") or []), _json(item.get("avoid") or []), float(item.get("risk_score") or 0), snapshot_id, str(proposal.get("source_impact_run_id") or ""), revision, str(item.get("rationale") or ""), _json(current), now, now))
        if changed or not old:
            conn.execute("""INSERT INTO rolling_plan_item_revisions (id, project_id, chapter_number, snapshot_id, revision, action, previous_payload, new_payload, reason, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (new_id(), project_id, chapter_number, snapshot_id, revision, str(item.get("action") or ("created" if not old else "replanned")), _json(previous), _json(current), str(item.get("rationale") or proposal.get("summary") or ""), now))
    return snapshot_id


def planning_context(project_id: str, chapter_number: int) -> dict:
    with connect() as conn:
        observations = rows_to_dicts(conn.execute("SELECT * FROM impact_observations WHERE project_id = ? AND chapter_number < ? AND severity IN ('high','critical') ORDER BY chapter_number DESC, created_at DESC LIMIT 12", (project_id, chapter_number)).fetchall())
    return {"rolling_plan": get_plan_item(project_id, chapter_number) or {}, "rolling_plan_window": list_current_plan(project_id, start_chapter=max(1, chapter_number), end_chapter=chapter_number + 4), "impact_warnings": observations}


def update_plan_lock(project_id: str, chapter_number: int, locked: bool) -> dict | None:
    with connect() as conn:
        conn.execute("UPDATE rolling_plan_items SET locked = ?, updated_at = ? WHERE project_id = ? AND chapter_number = ?", (1 if locked else 0, utc_now(), project_id, chapter_number))
    return get_plan_item(project_id, chapter_number)


def mark_plan_completed(project_id: str, chapter_number: int) -> dict | None:
    old = get_plan_item(project_id, chapter_number)
    if not old or old.get("status") == "completed": return old
    previous, current, now = _payload(old), {**_payload(old), "status": "completed", "locked": True}, utc_now()
    revision = int(old.get("revision") or 0) + 1
    with connect() as conn:
        conn.execute("UPDATE rolling_plan_items SET status='completed', locked=1, revision=?, payload=?, updated_at=? WHERE project_id=? AND chapter_number=?", (revision, _json(current), now, project_id, chapter_number))
        conn.execute("""INSERT INTO rolling_plan_item_revisions (id, project_id, chapter_number, snapshot_id, revision, action, previous_payload, new_payload, reason, created_at) VALUES (?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?)""", (new_id(), project_id, chapter_number, str(old.get("source_snapshot_id") or ""), revision, _json(previous), _json(current), "章节已定稿，滚动计划项冻结为已完成。", now))
    return get_plan_item(project_id, chapter_number)
