import heapq
import json
from collections import defaultdict
from typing import Any

from .database import connect, new_id, row_to_dict, rows_to_dicts, utc_now
from .memory_store import latest_narrative_debts
from .story_graph_store import latest_story_edges, list_story_nodes, list_story_threads, story_graph_context

EDGE_FACTORS = {
    "causes": 0.90, "depends_on": 0.88, "blocks": 0.92,
    "reveals": 0.78, "plants": 0.68, "pays_off": 0.86,
    "conflicts_with": 0.76, "continues": 0.74, "alternative_to": 0.58,
}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _score(value: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(abs(float(value if value is not None else default)), 1.0))
    except (TypeError, ValueError):
        return default


def _event(kind: str, subject_type: str, key: str, change: str, magnitude: Any, payload: dict) -> dict:
    return {
        "event_type": kind, "subject_type": subject_type, "subject_key": key,
        "change_type": change, "magnitude": round(_score(magnitude), 4), "payload": payload,
    }


def collect_chapter_events(project_id: str, chapter_id: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    specs = (
        ("story_thread_states", "thread", "thread_key", "status", "priority", "story.thread.changed"),
        ("story_node_states", "node", "node_key", "status", "importance", "story.node.changed"),
        ("story_edges", "edge", "edge_key", "status", "weight", "story.edge.changed"),
        ("story_facts", "fact", "fact_key", "fact_status", "confidence", "memory.fact.changed"),
        ("item_ownership", "item", "item_key", "status", None, "memory.item.changed"),
        ("narrative_debts", "debt", "debt_key", "status", "priority", "memory.debt.changed"),
        ("foreshadowing_states", "foreshadowing", "foreshadowing_key", "status", "priority", "memory.foreshadowing.changed"),
    )
    with connect() as conn:
        for table, subject_type, key_col, change_col, score_col, kind in specs:
            rows = rows_to_dicts(conn.execute(
                f"SELECT * FROM {table} WHERE project_id = ? AND source_chapter_id = ?",
                (project_id, chapter_id),
            ).fetchall())
            for row in rows:
                key = str(row.get(key_col) or "")
                if key:
                    events.append(_event(kind, subject_type, key, str(row.get(change_col) or "changed"), row.get(score_col) if score_col else .5, row))
        relationships = rows_to_dicts(conn.execute(
            "SELECT * FROM relationship_states WHERE project_id = ? AND source_chapter_id = ?",
            (project_id, chapter_id),
        ).fetchall())
        progress = rows_to_dicts(conn.execute(
            "SELECT * FROM chapter_story_progress WHERE project_id = ? AND chapter_id = ?",
            (project_id, chapter_id),
        ).fetchall())
    for row in relationships:
        key = "|".join([
            str(row.get("source_character_key") or row.get("source_character_name") or ""),
            str(row.get("target_character_key") or row.get("target_character_name") or ""),
            str(row.get("relation_type") or ""),
        ])
        events.append(_event("memory.relationship.changed", "relationship", key, str(row.get("status") or "changed"), row.get("value"), row))
    for row in progress:
        payload = dict(row)
        raw = row.get("source_node_keys")
        if isinstance(raw, str):
            try: raw = json.loads(raw)
            except json.JSONDecodeError: raw = []
        payload["source_node_keys"] = raw if isinstance(raw, list) else []
        events.append(_event("story.thread.progressed", "thread", str(row.get("thread_key") or ""), str(row.get("progress_type") or "advanced"), row.get("progress_score"), payload))
    return [event for event in events if event["subject_key"]]


def _propagate(project_id: str, events: list[dict], max_depth: int, threshold: float) -> list[dict]:
    nodes = list_story_nodes(project_id)
    node_map = {str(node.get("node_key") or ""): node for node in nodes}
    by_thread: dict[str, list[dict]] = defaultdict(list)
    for node in nodes:
        by_thread[str(node.get("thread_key") or "")].append(node)
    adjacency: dict[str, list[tuple[str, float, str]]] = defaultdict(list)
    for edge in latest_story_edges(project_id):
        if str(edge.get("status") or "active") != "active": continue
        source, target = str(edge.get("source_node_key") or ""), str(edge.get("target_node_key") or "")
        if not source or not target: continue
        relation = str(edge.get("relation_type") or "continues")
        factor = EDGE_FACTORS.get(relation, .65) * _score(edge.get("weight"), 1.0)
        adjacency[source].append((target, factor, relation))
        adjacency[target].append((source, factor * .45, f"reverse:{relation}"))
    seeds: list[tuple[str, float, str]] = []
    for event in events:
        magnitude = max(.2, _score(event.get("magnitude")))
        if event["subject_type"] == "node":
            seeds.append((event["subject_key"], magnitude, event["event_type"]))
        elif event["subject_type"] == "thread":
            payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
            source_nodes = payload.get("source_node_keys") if isinstance(payload.get("source_node_keys"), list) else []
            if source_nodes:
                seeds.extend((str(key), magnitude, "thread_progress") for key in source_nodes)
            else:
                seeds.extend((str(node.get("node_key") or ""), magnitude * .72, "thread_change") for node in by_thread.get(event["subject_key"], []) if str(node.get("status") or "") in {"planned", "active", "blocked"})
        elif event["subject_type"] == "edge":
            payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
            seeds.extend((str(payload[key]), magnitude * .8, "edge_change") for key in ("source_node_key", "target_node_key") if payload.get(key))
    queue = [(-score, 0, key, [key], reason) for key, score, reason in seeds if key]
    heapq.heapify(queue)
    best: dict[str, tuple[float, int, list[str], str]] = {}
    while queue:
        negative, depth, key, path, reason = heapq.heappop(queue)
        score = -negative
        if key in best and best[key][0] >= score: continue
        best[key] = (score, depth, path, reason)
        if depth >= max_depth: continue
        for target, factor, relation in adjacency.get(key, []):
            propagated = score * factor
            if propagated >= threshold:
                heapq.heappush(queue, (-propagated, depth + 1, target, path + [target], relation))
    targets, thread_scores = [], {}
    for key, (score, depth, path, reason) in best.items():
        node = node_map.get(key, {})
        targets.append({
            "target_type": "node", "target_key": key, "impact_score": round(score, 4),
            "depth": depth, "path": path, "reason": reason,
            "status": str(node.get("status") or "unknown"),
            "payload": {"title": node.get("title", ""), "thread_key": node.get("thread_key", ""), "node_type": node.get("node_type", "")},
        })
        thread = str(node.get("thread_key") or "")
        if thread: thread_scores[thread] = max(thread_scores.get(thread, 0), score * .85)
    threads = {str(row.get("thread_key") or ""): row for row in list_story_threads(project_id)}
    for key, score in thread_scores.items():
        row = threads.get(key, {})
        targets.append({
            "target_type": "thread", "target_key": key, "impact_score": round(score, 4),
            "depth": 0, "path": [key], "reason": "aggregated_from_nodes",
            "status": str(row.get("status") or "active"),
            "payload": {"title": row.get("title", ""), "current_stage": row.get("current_stage", ""), "next_target": row.get("next_target", "")},
        })
    return sorted(targets, key=lambda item: (-float(item["impact_score"]), item["target_type"], item["target_key"]))


def _list(value: Any) -> list:
    if isinstance(value, list): return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value); return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError: return []
    return []


def _observations(project_id: str, chapter_number: int, targets: list[dict]) -> list[dict]:
    observations = []
    scores = {(item["target_type"], item["target_key"]): float(item["impact_score"]) for item in targets}
    with connect() as conn:
        plans = rows_to_dicts(conn.execute(
            "SELECT * FROM rolling_plan_items WHERE project_id = ? AND chapter_number > ? ORDER BY chapter_number",
            (project_id, chapter_number),
        ).fetchall())
    for plan in plans:
        if int(plan.get("locked") or 0): continue
        refs = [("thread", str(plan.get("primary_thread_key") or ""))]
        refs += [("thread", str(key)) for key in _list(plan.get("secondary_thread_keys"))]
        refs += [("node", str(key)) for key in _list(plan.get("target_node_keys"))]
        score = max((scores.get(ref, 0) for ref in refs), default=0)
        if score >= .35:
            observations.append({
                "observation_type": "future_plan_impacted", "severity": "high" if score >= .65 else "medium",
                "subject_type": "plan", "subject_key": str(plan.get("chapter_number") or ""),
                "message": f"第 {plan.get('chapter_number')} 章计划引用了受影响剧情节点或剧情线。",
                "recommended_action": "重新计算该章主推进线、目标节点和必须处理事项。",
                "payload": {"impact_score": round(score, 4), "plan_id": plan.get("id", "")},
            })
    for debt in latest_narrative_debts(project_id, open_only=True):
        deadline = int(debt.get("deadline_chapter") or 0)
        if deadline and deadline <= chapter_number:
            observations.append({
                "observation_type": "narrative_debt_overdue", "severity": "high",
                "subject_type": "debt", "subject_key": str(debt.get("debt_key") or ""),
                "message": f"叙事债务已超过计划回收章节：{debt.get('description') or debt.get('debt_key')}",
                "recommended_action": "在最近一章推进、解释或明确取消该债务。", "payload": debt,
            })
    for thread in story_graph_context(project_id, current_chapter=chapter_number).get("stalled_threads") or []:
        observations.append({
            "observation_type": "story_thread_stalled", "severity": "high" if float(thread.get("priority") or 0) >= .8 else "medium",
            "subject_type": "thread", "subject_key": str(thread.get("thread_key") or ""),
            "message": f"剧情线已停滞 {thread.get('chapters_since_progress', 0)} 章：{thread.get('title') or thread.get('thread_key')}",
            "recommended_action": "在滚动窗口内安排一次明确推进或正式暂停。", "payload": thread,
        })
    return observations


def analyze_story_impact(project_id: str, chapter_id: str, chapter_number: int, *, max_depth: int = 3, threshold: float = .15, extra_events: list[dict] | None = None) -> dict:
    max_depth, threshold = max(1, min(int(max_depth), 5)), max(.05, min(float(threshold), .8))
    events = collect_chapter_events(project_id, chapter_id)
    for item in extra_events or []:
        if isinstance(item, dict) and item.get("subject_key"):
            events.append(_event(str(item.get("event_type") or "manual.change"), str(item.get("subject_type") or "node"), str(item["subject_key"]), str(item.get("change_type") or "changed"), item.get("magnitude", .7), item.get("payload") if isinstance(item.get("payload"), dict) else item))
    targets = _propagate(project_id, events, max_depth, threshold)
    observations = _observations(project_id, chapter_number, targets)
    return {
        "project_id": project_id, "chapter_id": chapter_id, "chapter_number": chapter_number,
        "max_depth": max_depth, "threshold": threshold, "events": events, "targets": targets,
        "observations": observations,
        "summary": f"检测到 {len(events)} 个变化事件，影响 {len(targets)} 个剧情目标，产生 {len(observations)} 条规划观察。",
    }


def persist_impact_analysis(conn, analysis: dict) -> str:
    project_id, chapter_id = str(analysis["project_id"]), str(analysis["chapter_id"])
    existing = row_to_dict(conn.execute("SELECT * FROM impact_runs WHERE project_id = ? AND chapter_id = ?", (project_id, chapter_id)).fetchone())
    run_id, now = str(existing.get("id")) if existing else new_id(), utc_now()
    conn.execute("DELETE FROM impact_events WHERE project_id = ? AND chapter_id = ?", (project_id, chapter_id))
    conn.execute("DELETE FROM impact_targets WHERE run_id = ?", (run_id,))
    conn.execute("DELETE FROM impact_observations WHERE run_id = ?", (run_id,))
    conn.execute("""
        INSERT INTO impact_runs (id, project_id, chapter_id, chapter_number, root_event_count, max_depth, threshold, status, summary, payload, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?)
        ON CONFLICT(project_id, chapter_id) DO UPDATE SET chapter_number=excluded.chapter_number, root_event_count=excluded.root_event_count, max_depth=excluded.max_depth, threshold=excluded.threshold, status='completed', summary=excluded.summary, payload=excluded.payload, updated_at=excluded.updated_at
    """, (run_id, project_id, chapter_id, int(analysis["chapter_number"]), len(analysis.get("events") or []), int(analysis.get("max_depth") or 3), float(analysis.get("threshold") or .15), str(analysis.get("summary") or ""), _json(analysis), now, now))
    for event in analysis.get("events") or []:
        conn.execute("""INSERT INTO impact_events (id, project_id, chapter_id, chapter_number, event_type, subject_type, subject_key, change_type, magnitude, payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (new_id(), project_id, chapter_id, int(analysis["chapter_number"]), str(event.get("event_type") or "change"), str(event.get("subject_type") or "unknown"), str(event.get("subject_key") or ""), str(event.get("change_type") or "changed"), float(event.get("magnitude") or 0), _json(event.get("payload") if isinstance(event.get("payload"), dict) else event), now))
    for target in analysis.get("targets") or []:
        conn.execute("""INSERT INTO impact_targets (id, run_id, project_id, target_type, target_key, impact_score, depth, path, reason, status, payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (new_id(), run_id, project_id, str(target.get("target_type") or "unknown"), str(target.get("target_key") or ""), float(target.get("impact_score") or 0), int(target.get("depth") or 0), _json(target.get("path") or []), str(target.get("reason") or ""), str(target.get("status") or "active"), _json(target.get("payload") if isinstance(target.get("payload"), dict) else target), now))
    for obs in analysis.get("observations") or []:
        conn.execute("""INSERT INTO impact_observations (id, run_id, project_id, chapter_id, chapter_number, observation_type, severity, subject_type, subject_key, message, recommended_action, payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (new_id(), run_id, project_id, chapter_id, int(analysis["chapter_number"]), str(obs.get("observation_type") or "impact"), str(obs.get("severity") or "medium"), str(obs.get("subject_type") or ""), str(obs.get("subject_key") or ""), str(obs.get("message") or ""), str(obs.get("recommended_action") or ""), _json(obs.get("payload") if isinstance(obs.get("payload"), dict) else obs), now))
    return run_id


def latest_impact_run(project_id: str, chapter_id: str | None = None) -> dict | None:
    sql, params = "SELECT * FROM impact_runs WHERE project_id = ?", [project_id]
    if chapter_id: sql += " AND chapter_id = ?"; params.append(chapter_id)
    sql += " ORDER BY chapter_number DESC, updated_at DESC LIMIT 1"
    with connect() as conn: return row_to_dict(conn.execute(sql, tuple(params)).fetchone())


def list_impact_runs(project_id: str, limit: int = 50) -> list[dict]:
    with connect() as conn: return rows_to_dicts(conn.execute("SELECT * FROM impact_runs WHERE project_id = ? ORDER BY chapter_number DESC, updated_at DESC LIMIT ?", (project_id, max(1, min(int(limit), 200)))).fetchall())


def impact_run_detail(project_id: str, run_id: str) -> dict | None:
    with connect() as conn:
        run = row_to_dict(conn.execute("SELECT * FROM impact_runs WHERE id = ? AND project_id = ?", (run_id, project_id)).fetchone())
        if not run: return None
        targets = rows_to_dicts(conn.execute("SELECT * FROM impact_targets WHERE run_id = ? ORDER BY impact_score DESC", (run_id,)).fetchall())
        observations = rows_to_dicts(conn.execute("SELECT * FROM impact_observations WHERE run_id = ? ORDER BY created_at", (run_id,)).fetchall())
        events = rows_to_dicts(conn.execute("SELECT * FROM impact_events WHERE project_id = ? AND chapter_id = ? ORDER BY created_at", (project_id, run["chapter_id"])).fetchall())
    return {"run": run, "events": events, "targets": targets, "observations": observations}
