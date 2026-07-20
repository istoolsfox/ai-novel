import hashlib
import json
from typing import Any

from .database import connect, new_id, row_to_dict, rows_to_dicts, utc_now
from .memory_store import stable_key

ACTIVE_THREAD_STATUSES = {"active", "paused", "blocked"}
OPEN_NODE_STATUSES = {"planned", "active", "blocked"}


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _float(value: Any, *, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        return max(minimum, min(float(value or 0), maximum))
    except (TypeError, ValueError):
        return minimum


def _integer(value: Any, *, default: int = 0) -> int:
    try:
        return max(0, int(value if value is not None else default))
    except (TypeError, ValueError):
        return max(0, default)


def thread_key(item: dict[str, Any]) -> str:
    return stable_key(
        item.get("thread_key"),
        item.get("thread_type"),
        item.get("title"),
        item.get("current_goal"),
        prefix="thread",
    )


def node_key(item: dict[str, Any]) -> str:
    return stable_key(
        item.get("node_key"),
        item.get("thread_key"),
        item.get("node_type"),
        item.get("title"),
        item.get("description"),
        prefix="node",
    )


def edge_key(item: dict[str, Any]) -> str:
    return stable_key(
        item.get("edge_key"),
        item.get("source_node_key"),
        item.get("target_node_key"),
        item.get("relation_type"),
        prefix="edge",
    )


def begin_story_graph_compilation(conn, step: dict[str, Any], memory: dict[str, Any]) -> tuple[str, str]:
    graph_payload = {
        "story_thread_changes": memory.get("story_thread_changes") or [],
        "story_node_changes": memory.get("story_node_changes") or [],
        "story_edge_changes": memory.get("story_edge_changes") or [],
        "story_progress": memory.get("story_progress") or [],
    }
    payload_text = json_text(graph_payload)
    content_hash = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
    existing = row_to_dict(
        conn.execute(
            "SELECT * FROM story_graph_compilations WHERE project_id = ? AND chapter_id = ?",
            (step["project_id"], step["chapter_id"]),
        ).fetchone()
    )
    compilation_id = str(existing.get("id")) if existing else new_id()
    now = utc_now()
    conn.execute(
        """
        INSERT INTO story_graph_compilations (
            id, project_id, chapter_id, chapter_number, content_hash,
            payload, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'committed', ?, ?)
        ON CONFLICT(project_id, chapter_id) DO UPDATE SET
            chapter_number = excluded.chapter_number,
            content_hash = excluded.content_hash,
            payload = excluded.payload,
            status = 'committed',
            updated_at = excluded.updated_at
        """,
        (
            compilation_id, step["project_id"], step["chapter_id"], step["chapter_number"],
            content_hash, payload_text, now, now,
        ),
    )
    return compilation_id, now


def clear_chapter_story_graph(conn, step: dict[str, Any]) -> None:
    project_id = step["project_id"]
    chapter_id = step["chapter_id"]
    conn.execute(
        "DELETE FROM story_thread_states WHERE project_id = ? AND source_chapter_id = ?",
        (project_id, chapter_id),
    )
    conn.execute(
        "DELETE FROM story_node_states WHERE project_id = ? AND source_chapter_id = ?",
        (project_id, chapter_id),
    )
    conn.execute(
        "DELETE FROM story_edges WHERE project_id = ? AND source_chapter_id = ?",
        (project_id, chapter_id),
    )
    conn.execute(
        "DELETE FROM chapter_story_progress WHERE project_id = ? AND chapter_id = ?",
        (project_id, chapter_id),
    )


def persist_story_graph_layers(conn, step: dict[str, Any], memory: dict[str, Any]) -> None:
    compilation_id, now = begin_story_graph_compilation(conn, step, memory)
    clear_chapter_story_graph(conn, step)
    for item in memory.get("story_thread_changes") or []:
        if isinstance(item, dict):
            _insert_thread_state(conn, step, item, compilation_id, now)
    for item in memory.get("story_node_changes") or []:
        if isinstance(item, dict):
            _ensure_thread_for_reference(conn, step, str(item.get("thread_key") or ""), compilation_id, now)
            _insert_node_state(conn, step, item, compilation_id, now)
    for item in memory.get("story_edge_changes") or []:
        if isinstance(item, dict):
            _insert_edge(conn, step, item, compilation_id, now)
    for item in memory.get("story_progress") or []:
        if isinstance(item, dict):
            _ensure_thread_for_reference(conn, step, str(item.get("thread_key") or ""), compilation_id, now)
            _insert_progress(conn, step, item, now)
    refresh_story_thread_cache(conn, step["project_id"])
    refresh_story_node_cache(conn, step["project_id"])


def _insert_thread_state(conn, step, item, compilation_id, now) -> None:
    key = thread_key(item)
    conn.execute(
        """
        INSERT INTO story_thread_states (
            id, project_id, thread_key, title, thread_type, status, priority,
            current_stage, current_goal, next_target, stall_tolerance,
            source_chapter_id, source_chapter_number, compilation_id,
            payload, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id, thread_key, source_chapter_id) DO UPDATE SET
            title = excluded.title,
            thread_type = excluded.thread_type,
            status = excluded.status,
            priority = excluded.priority,
            current_stage = excluded.current_stage,
            current_goal = excluded.current_goal,
            next_target = excluded.next_target,
            stall_tolerance = excluded.stall_tolerance,
            source_chapter_number = excluded.source_chapter_number,
            compilation_id = excluded.compilation_id,
            payload = excluded.payload,
            updated_at = excluded.updated_at
        """,
        (
            new_id(), step["project_id"], key, str(item.get("title") or key),
            str(item.get("thread_type") or "subplot"), str(item.get("status") or "active"),
            _float(item.get("priority")), str(item.get("current_stage") or ""),
            str(item.get("current_goal") or ""), str(item.get("next_target") or ""),
            _integer(item.get("stall_tolerance"), default=3) or 3,
            step["chapter_id"], step["chapter_number"], compilation_id,
            json_text(item), now, now,
        ),
    )


def _ensure_thread_for_reference(conn, step, raw_key: str, compilation_id: str, now: str) -> None:
    key = raw_key.strip()
    if not key:
        return
    exists = conn.execute(
        "SELECT 1 FROM story_thread_states WHERE project_id = ? AND thread_key = ? LIMIT 1",
        (step["project_id"], key),
    ).fetchone()
    if exists:
        return
    _insert_thread_state(
        conn,
        step,
        {
            "thread_key": key,
            "title": key,
            "thread_type": "subplot",
            "status": "active",
            "priority": 0.5,
            "stall_tolerance": 3,
        },
        compilation_id,
        now,
    )


def _insert_node_state(conn, step, item, compilation_id, now) -> None:
    key = node_key(item)
    thread = str(item.get("thread_key") or "").strip()
    if not thread:
        return
    actual = _integer(item.get("actual_chapter"))
    status = str(item.get("status") or "planned")
    if not actual and status == "completed":
        actual = int(step["chapter_number"])
    conn.execute(
        """
        INSERT INTO story_node_states (
            id, project_id, node_key, thread_key, node_type, title,
            description, status, importance, planned_chapter, actual_chapter,
            source_chapter_id, source_chapter_number, compilation_id,
            payload, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id, node_key, source_chapter_id) DO UPDATE SET
            thread_key = excluded.thread_key,
            node_type = excluded.node_type,
            title = excluded.title,
            description = excluded.description,
            status = excluded.status,
            importance = excluded.importance,
            planned_chapter = excluded.planned_chapter,
            actual_chapter = excluded.actual_chapter,
            source_chapter_number = excluded.source_chapter_number,
            compilation_id = excluded.compilation_id,
            payload = excluded.payload,
            updated_at = excluded.updated_at
        """,
        (
            new_id(), step["project_id"], key, thread, str(item.get("node_type") or "event"),
            str(item.get("title") or key), str(item.get("description") or ""), status,
            _float(item.get("importance")), _integer(item.get("planned_chapter")), actual,
            step["chapter_id"], step["chapter_number"], compilation_id,
            json_text(item), now, now,
        ),
    )


def _insert_edge(conn, step, item, compilation_id, now) -> None:
    source = str(item.get("source_node_key") or "").strip()
    target = str(item.get("target_node_key") or "").strip()
    relation = str(item.get("relation_type") or "continues").strip()
    if not source or not target:
        return
    key = edge_key(item)
    conn.execute(
        """
        INSERT INTO story_edges (
            id, project_id, edge_key, source_node_key, target_node_key,
            relation_type, status, weight, source_chapter_id,
            source_chapter_number, compilation_id, payload, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id, edge_key, source_chapter_id) DO UPDATE SET
            source_node_key = excluded.source_node_key,
            target_node_key = excluded.target_node_key,
            relation_type = excluded.relation_type,
            status = excluded.status,
            weight = excluded.weight,
            source_chapter_number = excluded.source_chapter_number,
            compilation_id = excluded.compilation_id,
            payload = excluded.payload,
            updated_at = excluded.updated_at
        """,
        (
            new_id(), step["project_id"], key, source, target, relation,
            str(item.get("status") or "active"),
            _float(item.get("weight") if item.get("weight") is not None else 1.0),
            step["chapter_id"], step["chapter_number"], compilation_id,
            json_text(item), now, now,
        ),
    )


def _insert_progress(conn, step, item, now) -> None:
    key = str(item.get("thread_key") or "").strip()
    if not key:
        return
    source_nodes = item.get("source_node_keys") if isinstance(item.get("source_node_keys"), list) else []
    conn.execute(
        """
        INSERT INTO chapter_story_progress (
            id, project_id, chapter_id, chapter_number, thread_key,
            progress_type, progress_summary, before_stage, after_stage,
            progress_score, source_node_keys, payload, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id, chapter_id, thread_key) DO UPDATE SET
            progress_type = excluded.progress_type,
            progress_summary = excluded.progress_summary,
            before_stage = excluded.before_stage,
            after_stage = excluded.after_stage,
            progress_score = excluded.progress_score,
            source_node_keys = excluded.source_node_keys,
            payload = excluded.payload,
            updated_at = excluded.updated_at
        """,
        (
            new_id(), step["project_id"], step["chapter_id"], step["chapter_number"], key,
            str(item.get("progress_type") or "advanced"), str(item.get("progress_summary") or ""),
            str(item.get("before_stage") or ""), str(item.get("after_stage") or ""),
            _float(item.get("progress_score")), json_text(source_nodes), json_text(item), now, now,
        ),
    )


def _latest_state_rows(conn, table: str, key_column: str, project_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        f"""
        SELECT current.*
        FROM {table} AS current
        JOIN (
            SELECT {key_column}, MAX(source_chapter_number) AS max_chapter
            FROM {table}
            WHERE project_id = ?
            GROUP BY {key_column}
        ) AS latest
          ON latest.{key_column} = current.{key_column}
         AND latest.max_chapter = current.source_chapter_number
        WHERE current.project_id = ?
        ORDER BY current.updated_at DESC
        """,
        (project_id, project_id),
    ).fetchall()
    unique: dict[str, dict[str, Any]] = {}
    for row in rows_to_dicts(rows):
        unique.setdefault(str(row.get(key_column) or ""), row)
    return list(unique.values())


def refresh_story_thread_cache(conn, project_id: str) -> None:
    latest = _latest_state_rows(conn, "story_thread_states", "thread_key", project_id)
    valid_keys = {str(row.get("thread_key") or "") for row in latest}
    for row in latest:
        key = str(row.get("thread_key") or "")
        progress = row_to_dict(
            conn.execute(
                """
                SELECT * FROM chapter_story_progress
                WHERE project_id = ? AND thread_key = ?
                  AND progress_type IN ('introduced','advanced','resolved','regressed','blocked')
                ORDER BY chapter_number DESC, updated_at DESC LIMIT 1
                """,
                (project_id, key),
            ).fetchone()
        )
        first_chapter = conn.execute(
            "SELECT MIN(source_chapter_number) FROM story_thread_states WHERE project_id = ? AND thread_key = ?",
            (project_id, key),
        ).fetchone()[0] or 0
        last_progress = int(progress.get("chapter_number") or 0) if progress else int(row.get("source_chapter_number") or 0)
        now = utc_now()
        conn.execute(
            """
            INSERT INTO story_threads (
                id, project_id, thread_key, title, thread_type, status, priority,
                current_stage, current_goal, next_target, stall_tolerance,
                first_chapter, last_progress_chapter, last_source_chapter_id,
                payload, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id, thread_key) DO UPDATE SET
                title = excluded.title,
                thread_type = excluded.thread_type,
                status = excluded.status,
                priority = excluded.priority,
                current_stage = excluded.current_stage,
                current_goal = excluded.current_goal,
                next_target = excluded.next_target,
                stall_tolerance = excluded.stall_tolerance,
                first_chapter = excluded.first_chapter,
                last_progress_chapter = excluded.last_progress_chapter,
                last_source_chapter_id = excluded.last_source_chapter_id,
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (
                new_id(), project_id, key, row.get("title", ""), row.get("thread_type", "subplot"),
                row.get("status", "active"), _float(row.get("priority")), row.get("current_stage", ""),
                row.get("current_goal", ""), row.get("next_target", ""),
                _integer(row.get("stall_tolerance"), default=3) or 3,
                first_chapter, last_progress, row.get("source_chapter_id", ""),
                json_text(row.get("payload") if isinstance(row.get("payload"), dict) else row), now, now,
            ),
        )
    if valid_keys:
        placeholders = ",".join("?" for _ in valid_keys)
        conn.execute(
            f"DELETE FROM story_threads WHERE project_id = ? AND thread_key NOT IN ({placeholders})",
            (project_id, *sorted(valid_keys)),
        )
    else:
        conn.execute("DELETE FROM story_threads WHERE project_id = ?", (project_id,))


def refresh_story_node_cache(conn, project_id: str) -> None:
    latest = _latest_state_rows(conn, "story_node_states", "node_key", project_id)
    valid_keys = {str(row.get("node_key") or "") for row in latest}
    for row in latest:
        key = str(row.get("node_key") or "")
        existing = row_to_dict(
            conn.execute(
                "SELECT * FROM story_nodes WHERE project_id = ? AND node_key = ?",
                (project_id, key),
            ).fetchone()
        )
        now = utc_now()
        conn.execute(
            """
            INSERT INTO story_nodes (
                id, project_id, node_key, thread_key, node_type, title,
                description, status, importance, planned_chapter, actual_chapter,
                first_source_chapter_id, last_source_chapter_id,
                payload, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id, node_key) DO UPDATE SET
                thread_key = excluded.thread_key,
                node_type = excluded.node_type,
                title = excluded.title,
                description = excluded.description,
                status = excluded.status,
                importance = excluded.importance,
                planned_chapter = excluded.planned_chapter,
                actual_chapter = excluded.actual_chapter,
                last_source_chapter_id = excluded.last_source_chapter_id,
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (
                new_id(), project_id, key, row.get("thread_key", ""), row.get("node_type", "event"),
                row.get("title", ""), row.get("description", ""), row.get("status", "planned"),
                _float(row.get("importance")), _integer(row.get("planned_chapter")),
                _integer(row.get("actual_chapter")),
                existing.get("first_source_chapter_id", "") if existing else row.get("source_chapter_id", ""),
                row.get("source_chapter_id", ""),
                json_text(row.get("payload") if isinstance(row.get("payload"), dict) else row), now, now,
            ),
        )
    if valid_keys:
        placeholders = ",".join("?" for _ in valid_keys)
        conn.execute(
            f"DELETE FROM story_nodes WHERE project_id = ? AND node_key NOT IN ({placeholders})",
            (project_id, *sorted(valid_keys)),
        )
    else:
        conn.execute("DELETE FROM story_nodes WHERE project_id = ?", (project_id,))


def list_story_threads(project_id: str, *, status: str = "") -> list[dict[str, Any]]:
    sql = "SELECT * FROM story_threads WHERE project_id = ?"
    params: list[Any] = [project_id]
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY priority DESC, last_progress_chapter ASC, title"
    with connect() as conn:
        return rows_to_dicts(conn.execute(sql, tuple(params)).fetchall())


def list_story_nodes(project_id: str, *, thread: str = "", status: str = "") -> list[dict[str, Any]]:
    sql = "SELECT * FROM story_nodes WHERE project_id = ?"
    params: list[Any] = [project_id]
    if thread:
        sql += " AND thread_key = ?"
        params.append(thread)
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY importance DESC, planned_chapter, title"
    with connect() as conn:
        return rows_to_dicts(conn.execute(sql, tuple(params)).fetchall())


def latest_story_edges(project_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT current.*
            FROM story_edges AS current
            JOIN (
                SELECT edge_key, MAX(source_chapter_number) AS max_chapter
                FROM story_edges
                WHERE project_id = ?
                GROUP BY edge_key
            ) AS latest
              ON latest.edge_key = current.edge_key
             AND latest.max_chapter = current.source_chapter_number
            WHERE current.project_id = ?
            ORDER BY current.weight DESC, current.updated_at DESC
            """,
            (project_id, project_id),
        ).fetchall()
    unique: dict[str, dict[str, Any]] = {}
    for row in rows_to_dicts(rows):
        unique.setdefault(str(row.get("edge_key") or ""), row)
    return list(unique.values())


def list_chapter_progress(project_id: str, chapter_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = rows_to_dicts(
            conn.execute(
                """
                SELECT * FROM chapter_story_progress
                WHERE project_id = ? AND chapter_id = ?
                ORDER BY progress_score DESC, thread_key
                """,
                (project_id, chapter_id),
            ).fetchall()
        )
    for row in rows:
        raw = row.get("source_node_keys")
        if isinstance(raw, str):
            try:
                row["source_node_keys"] = json.loads(raw)
            except json.JSONDecodeError:
                row["source_node_keys"] = []
    return rows


def list_recent_progress(project_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                """
                SELECT * FROM chapter_story_progress
                WHERE project_id = ?
                ORDER BY chapter_number DESC, progress_score DESC
                LIMIT ?
                """,
                (project_id, max(1, min(limit, 500))),
            ).fetchall()
        )


def story_graph_context(project_id: str, *, current_chapter: int | None = None) -> dict[str, Any]:
    if current_chapter is None:
        with connect() as conn:
            current_chapter = int(
                conn.execute(
                    "SELECT COALESCE(MAX(chapter_number), 0) FROM chapters WHERE project_id = ?",
                    (project_id,),
                ).fetchone()[0] or 0
            )
    decorated: list[dict[str, Any]] = []
    for row in list_story_threads(project_id):
        last_progress = int(row.get("last_progress_chapter") or row.get("first_chapter") or 0)
        tolerance = max(1, int(row.get("stall_tolerance") or 3))
        chapters_since = max(0, int(current_chapter or 0) - last_progress)
        stalled = chapters_since > tolerance and str(row.get("status") or "") in ACTIVE_THREAD_STATUSES
        pressure = min(chapters_since / tolerance, 2.0)
        focus_score = float(row.get("priority") or 0) + min(pressure, 1.0) * 0.5
        if str(row.get("status") or "") == "blocked":
            focus_score += 0.15
        decorated.append(
            {
                "thread_key": row.get("thread_key", ""),
                "title": row.get("title", ""),
                "thread_type": row.get("thread_type", ""),
                "status": row.get("status", ""),
                "priority": row.get("priority", 0),
                "current_stage": row.get("current_stage", ""),
                "current_goal": row.get("current_goal", ""),
                "next_target": row.get("next_target", ""),
                "last_progress_chapter": last_progress,
                "chapters_since_progress": chapters_since,
                "stall_tolerance": tolerance,
                "stalled": stalled,
                "focus_score": round(focus_score, 4),
            }
        )
    active_threads = [item for item in decorated if item["status"] in ACTIVE_THREAD_STATUSES]
    focus = sorted(
        active_threads,
        key=lambda item: (-item["focus_score"], -float(item["priority"] or 0), item["thread_key"]),
    )[:5]
    nodes = [
        {
            "node_key": row.get("node_key", ""),
            "thread_key": row.get("thread_key", ""),
            "node_type": row.get("node_type", ""),
            "title": row.get("title", ""),
            "description": row.get("description", ""),
            "status": row.get("status", ""),
            "importance": row.get("importance", 0),
            "planned_chapter": row.get("planned_chapter", 0),
            "actual_chapter": row.get("actual_chapter", 0),
        }
        for row in list_story_nodes(project_id)
        if str(row.get("status") or "") in OPEN_NODE_STATUSES
    ]
    edges = [
        {
            "edge_key": row.get("edge_key", ""),
            "source_node_key": row.get("source_node_key", ""),
            "target_node_key": row.get("target_node_key", ""),
            "relation_type": row.get("relation_type", ""),
            "status": row.get("status", ""),
            "weight": row.get("weight", 0),
        }
        for row in latest_story_edges(project_id)
        if str(row.get("status") or "") == "active"
    ]
    return {
        "story_threads": active_threads[:40],
        "story_nodes": nodes[:80],
        "story_edges": edges[:120],
        "story_focus": focus,
        "stalled_threads": [item for item in active_threads if item["stalled"]],
    }


def upsert_manual_thread(project_id: str, item: dict[str, Any]) -> dict[str, Any]:
    key = thread_key(item)
    step = {"project_id": project_id, "chapter_id": f"manual:thread:{key}", "chapter_number": 0}
    now = utc_now()
    with connect() as conn:
        _insert_thread_state(conn, step, {**item, "thread_key": key}, "manual", now)
        refresh_story_thread_cache(conn, project_id)
        return row_to_dict(
            conn.execute(
                "SELECT * FROM story_threads WHERE project_id = ? AND thread_key = ?",
                (project_id, key),
            ).fetchone()
        )


def upsert_manual_node(project_id: str, item: dict[str, Any]) -> dict[str, Any]:
    key = node_key(item)
    step = {"project_id": project_id, "chapter_id": f"manual:node:{key}", "chapter_number": 0}
    now = utc_now()
    with connect() as conn:
        _ensure_thread_for_reference(conn, step, str(item.get("thread_key") or ""), "manual", now)
        _insert_node_state(conn, step, {**item, "node_key": key}, "manual", now)
        refresh_story_thread_cache(conn, project_id)
        refresh_story_node_cache(conn, project_id)
        return row_to_dict(
            conn.execute(
                "SELECT * FROM story_nodes WHERE project_id = ? AND node_key = ?",
                (project_id, key),
            ).fetchone()
        )


def upsert_manual_edge(project_id: str, item: dict[str, Any]) -> dict[str, Any]:
    key = edge_key(item)
    step = {"project_id": project_id, "chapter_id": f"manual:edge:{key}", "chapter_number": 0}
    now = utc_now()
    with connect() as conn:
        _insert_edge(conn, step, {**item, "edge_key": key}, "manual", now)
        return row_to_dict(
            conn.execute(
                """
                SELECT * FROM story_edges
                WHERE project_id = ? AND edge_key = ? AND source_chapter_id = ?
                """,
                (project_id, key, step["chapter_id"]),
            ).fetchone()
        )
