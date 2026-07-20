import hashlib
import json
import shutil
from typing import Any

from .database import connect, new_id, row_to_dict, rows_to_dicts, utc_now
from .storage import ensure_project_dirs
from .worldline_clone import clone_project_at_fork, write_project_files


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _number(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def ensure_main_worldline(project_id: str) -> dict[str, Any]:
    with connect() as conn:
        existing = row_to_dict(
            conn.execute("SELECT * FROM worldlines WHERE project_id = ?", (project_id,)).fetchone()
        )
        if existing:
            return existing
        project = row_to_dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())
        if not project:
            raise ValueError("Project not found")
        worldline_id, now = new_id(), utc_now()
        conn.execute(
            """
            INSERT INTO worldlines (
                id, root_project_id, project_id, parent_worldline_id, parent_project_id,
                name, description, fork_chapter_number, status, is_primary,
                created_at, updated_at
            ) VALUES (?, ?, ?, '', '', '主世界线', '项目原始世界线', 0, 'active', 1, ?, ?)
            """,
            (worldline_id, project_id, project_id, now, now),
        )
        conn.execute(
            "INSERT INTO worldline_roots (root_project_id, primary_worldline_id, active_worldline_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (project_id, worldline_id, worldline_id, now, now),
        )
        conn.execute(
            "INSERT INTO worldline_events (id, root_project_id, worldline_id, event_type, payload, created_at) VALUES (?, ?, ?, 'worldline.registered', '{}', ?)",
            (new_id(), project_id, worldline_id, now),
        )
        return row_to_dict(conn.execute("SELECT * FROM worldlines WHERE id = ?", (worldline_id,)).fetchone())


def resolve_worldline(project_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = row_to_dict(conn.execute("SELECT * FROM worldlines WHERE project_id = ?", (project_id,)).fetchone())
    return row or ensure_main_worldline(project_id)


def _root_state(root_project_id: str) -> dict[str, Any]:
    with connect() as conn:
        return row_to_dict(
            conn.execute("SELECT * FROM worldline_roots WHERE root_project_id = ?", (root_project_id,)).fetchone()
        ) or {}


def list_worldlines(project_id: str) -> dict[str, Any]:
    current = resolve_worldline(project_id)
    root_id = str(current["root_project_id"])
    state = _root_state(root_id)
    with connect() as conn:
        lines = rows_to_dicts(
            conn.execute(
                """
                SELECT worldlines.*, projects.title AS project_title, projects.status AS project_status
                FROM worldlines
                JOIN projects ON projects.id = worldlines.project_id
                WHERE worldlines.root_project_id = ?
                ORDER BY worldlines.created_at
                """,
                (root_id,),
            ).fetchall()
        )
        events = rows_to_dicts(
            conn.execute(
                "SELECT * FROM worldline_events WHERE root_project_id = ? ORDER BY created_at DESC LIMIT 100",
                (root_id,),
            ).fetchall()
        )
    for line in lines:
        line["is_active"] = line.get("id") == state.get("active_worldline_id")
        line["is_primary"] = line.get("id") == state.get("primary_worldline_id")
    return {
        "root_project_id": root_id,
        "current_worldline_id": current["id"],
        "current_project_id": current["project_id"],
        "active_worldline_id": state.get("active_worldline_id", ""),
        "primary_worldline_id": state.get("primary_worldline_id", ""),
        "worldlines": lines,
        "events": events,
        "isolation_model": "project_backed",
    }


def require_worldline(project_id: str, worldline_id: str) -> dict[str, Any]:
    current = resolve_worldline(project_id)
    with connect() as conn:
        line = row_to_dict(
            conn.execute(
                "SELECT * FROM worldlines WHERE id = ? AND root_project_id = ?",
                (worldline_id, current["root_project_id"]),
            ).fetchone()
        )
    if not line:
        raise ValueError("Worldline not found in project family")
    return line


def create_worldline(
    source_project_id: str,
    *,
    name: str,
    fork_chapter_number: int,
    description: str = "",
) -> dict[str, Any]:
    source_line = resolve_worldline(source_project_id)
    root_project_id = str(source_line["root_project_id"])
    fork_chapter_number = max(0, int(fork_chapter_number))
    with connect() as conn:
        active_job = conn.execute(
            "SELECT 1 FROM generation_jobs WHERE project_id = ? AND status IN ('queued','running','paused') LIMIT 1",
            (source_project_id,),
        ).fetchone()
        if active_job:
            raise ValueError("存在未结束托管任务，不能在运行中创建世界线")
        if fork_chapter_number > 0:
            chapter = conn.execute(
                "SELECT 1 FROM chapters WHERE project_id = ? AND chapter_number = ?",
                (source_project_id, fork_chapter_number),
            ).fetchone()
            if not chapter:
                raise ValueError("分叉章节不存在")
        duplicate = conn.execute(
            "SELECT 1 FROM worldlines WHERE root_project_id = ? AND name = ? AND status != 'archived'",
            (root_project_id, name.strip()),
        ).fetchone()
        if duplicate:
            raise ValueError("同一项目下已存在同名世界线")

    target_project_id = new_id()
    target_worldline_id = new_id()
    target_root = ensure_project_dirs(target_project_id)
    try:
        with connect() as conn:
            manifest, manifest_hash = clone_project_at_fork(
                conn,
                source_project_id,
                target_project_id,
                target_root,
                fork_chapter_number,
            )
            now = utc_now()
            conn.execute(
                """
                INSERT INTO worldlines (
                    id, root_project_id, project_id, parent_worldline_id,
                    parent_project_id, name, description, fork_chapter_number,
                    status, is_primary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', 0, ?, ?)
                """,
                (
                    target_worldline_id,
                    root_project_id,
                    target_project_id,
                    source_line["id"],
                    source_project_id,
                    name.strip(),
                    description.strip(),
                    fork_chapter_number,
                    now,
                    now,
                ),
            )
            conn.execute(
                """
                INSERT INTO worldline_snapshots (
                    id, worldline_id, source_worldline_id, source_project_id,
                    fork_chapter_number, manifest_hash, manifest, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id(),
                    target_worldline_id,
                    source_line["id"],
                    source_project_id,
                    fork_chapter_number,
                    manifest_hash,
                    _json(manifest),
                    now,
                ),
            )
            conn.execute(
                """
                INSERT INTO worldline_events (
                    id, root_project_id, worldline_id, event_type,
                    source_worldline_id, target_worldline_id, payload, created_at
                ) VALUES (?, ?, ?, 'worldline.forked', ?, ?, ?, ?)
                """,
                (
                    new_id(),
                    root_project_id,
                    target_worldline_id,
                    source_line["id"],
                    target_worldline_id,
                    _json({"fork_chapter_number": fork_chapter_number, "manifest_hash": manifest_hash}),
                    now,
                ),
            )
        write_project_files(target_project_id)
    except Exception:
        shutil.rmtree(target_root, ignore_errors=True)
        raise
    return worldline_detail(source_project_id, target_worldline_id)


def worldline_detail(project_id: str, worldline_id: str) -> dict[str, Any]:
    line = require_worldline(project_id, worldline_id)
    state = _root_state(str(line["root_project_id"]))
    with connect() as conn:
        project = row_to_dict(
            conn.execute("SELECT * FROM projects WHERE id = ?", (line["project_id"],)).fetchone()
        ) or {}
        snapshot = row_to_dict(
            conn.execute("SELECT * FROM worldline_snapshots WHERE worldline_id = ?", (worldline_id,)).fetchone()
        )
        chapter_count = int(
            conn.execute("SELECT COUNT(*) FROM chapters WHERE project_id = ?", (line["project_id"],)).fetchone()[0]
        )
        latest_chapter = int(
            conn.execute(
                "SELECT COALESCE(MAX(chapter_number),0) FROM chapters WHERE project_id = ?",
                (line["project_id"],),
            ).fetchone()[0]
        )
    return {
        **line,
        "project": project,
        "snapshot": snapshot,
        "chapter_count": chapter_count,
        "latest_chapter_number": latest_chapter,
        "is_active": worldline_id == state.get("active_worldline_id"),
        "is_primary": worldline_id == state.get("primary_worldline_id"),
    }


def _event(root_project_id: str, worldline_id: str, event_type: str, payload: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO worldline_events (id, root_project_id, worldline_id, event_type, target_worldline_id, payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_id(), root_project_id, worldline_id, event_type, worldline_id, _json(payload), utc_now()),
        )


def activate_worldline(project_id: str, worldline_id: str) -> dict[str, Any]:
    line = require_worldline(project_id, worldline_id)
    if line.get("status") != "active":
        raise ValueError("已归档世界线不能激活")
    now = utc_now()
    with connect() as conn:
        conn.execute(
            "UPDATE worldline_roots SET active_worldline_id = ?, updated_at = ? WHERE root_project_id = ?",
            (worldline_id, now, line["root_project_id"]),
        )
    _event(
        str(line["root_project_id"]),
        worldline_id,
        "worldline.activated",
        {"active_project_id": line["project_id"]},
    )
    return worldline_detail(project_id, worldline_id)


def promote_worldline(project_id: str, worldline_id: str) -> dict[str, Any]:
    line = require_worldline(project_id, worldline_id)
    if line.get("status") != "active":
        raise ValueError("已归档世界线不能提升为主线")
    now = utc_now()
    with connect() as conn:
        conn.execute(
            "UPDATE worldlines SET is_primary = 0, updated_at = ? WHERE root_project_id = ?",
            (now, line["root_project_id"]),
        )
        conn.execute("UPDATE worldlines SET is_primary = 1, updated_at = ? WHERE id = ?", (now, worldline_id))
        conn.execute(
            "UPDATE worldline_roots SET primary_worldline_id = ?, active_worldline_id = ?, updated_at = ? WHERE root_project_id = ?",
            (worldline_id, worldline_id, now, line["root_project_id"]),
        )
    _event(
        str(line["root_project_id"]),
        worldline_id,
        "worldline.promoted",
        {"primary_project_id": line["project_id"]},
    )
    return worldline_detail(project_id, worldline_id)


def archive_worldline(project_id: str, worldline_id: str) -> dict[str, Any]:
    line = require_worldline(project_id, worldline_id)
    state = _root_state(str(line["root_project_id"]))
    if worldline_id in {state.get("primary_worldline_id"), state.get("active_worldline_id")}:
        raise ValueError("当前主线或激活世界线不能归档")
    with connect() as conn:
        conn.execute(
            "UPDATE worldlines SET status = 'archived', updated_at = ? WHERE id = ?",
            (utc_now(), worldline_id),
        )
    _event(str(line["root_project_id"]), worldline_id, "worldline.archived", {})
    return worldline_detail(project_id, worldline_id)


def _chapter_map(project_id: str) -> dict[int, dict[str, Any]]:
    with connect() as conn:
        rows = rows_to_dicts(
            conn.execute(
                "SELECT chapter_number, title, brief, draft, summary, status, word_count FROM chapters WHERE project_id = ? ORDER BY chapter_number",
                (project_id,),
            ).fetchall()
        )
    result = {}
    for row in rows:
        row["draft_hash"] = hashlib.sha256(str(row.get("draft") or "").encode("utf-8")).hexdigest()
        result[_number(row.get("chapter_number"))] = row
    return result


def _map_diff(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_keys, right_keys = set(left), set(right)
    changed = [key for key in sorted(left_keys & right_keys) if left[key] != right[key]]
    return {
        "only_left": sorted(left_keys - right_keys),
        "only_right": sorted(right_keys - left_keys),
        "changed": changed,
    }


def compare_worldlines(project_id: str, left_worldline_id: str, right_worldline_id: str) -> dict[str, Any]:
    left = require_worldline(project_id, left_worldline_id)
    right = require_worldline(project_id, right_worldline_id)
    left_project, right_project = str(left["project_id"]), str(right["project_id"])
    left_chapters, right_chapters = _chapter_map(left_project), _chapter_map(right_project)
    chapter_numbers = sorted(set(left_chapters) | set(right_chapters))
    chapter_differences = []
    shared_prefix = 0
    diverged = False
    for number in chapter_numbers:
        a, b = left_chapters.get(number), right_chapters.get(number)
        same = bool(
            a and b and a.get("draft_hash") == b.get("draft_hash") and a.get("status") == b.get("status")
        )
        if same and not diverged:
            shared_prefix = number
        else:
            diverged = True
            chapter_differences.append(
                {
                    "chapter_number": number,
                    "left": a,
                    "right": b,
                    "change": "only_left" if a and not b else "only_right" if b and not a else "modified",
                }
            )

    from .memory_store import latest_story_facts
    from .rolling_planner import list_current_plan
    from .story_graph_store import list_story_nodes, list_story_threads

    def fact_map(project: str) -> dict[str, Any]:
        return {
            str(row.get("fact_key") or ""): (row.get("fact_text", ""), row.get("fact_status", ""))
            for row in latest_story_facts(project)
        }

    def thread_map(project: str) -> dict[str, Any]:
        return {
            str(row.get("thread_key") or ""): (
                row.get("current_stage", ""),
                row.get("status", ""),
                row.get("next_target", ""),
            )
            for row in list_story_threads(project)
        }

    def node_map(project: str) -> dict[str, Any]:
        return {
            str(row.get("node_key") or ""): (
                row.get("status", ""),
                row.get("planned_chapter", 0),
                row.get("actual_chapter", 0),
            )
            for row in list_story_nodes(project)
        }

    def plan_map(project: str) -> dict[str, Any]:
        return {
            str(row.get("chapter_number") or ""): (
                row.get("status", ""),
                row.get("primary_thread_key", ""),
                tuple(row.get("target_node_keys") or []),
                row.get("goal", ""),
                bool(row.get("locked")),
            )
            for row in list_current_plan(project)
        }

    return {
        "root_project_id": left["root_project_id"],
        "left": worldline_detail(project_id, left_worldline_id),
        "right": worldline_detail(project_id, right_worldline_id),
        "shared_prefix_chapter": shared_prefix,
        "chapter_differences": chapter_differences,
        "memory_facts": _map_diff(fact_map(left_project), fact_map(right_project)),
        "story_threads": _map_diff(thread_map(left_project), thread_map(right_project)),
        "story_nodes": _map_diff(node_map(left_project), node_map(right_project)),
        "rolling_plan": _map_diff(plan_map(left_project), plan_map(right_project)),
    }
