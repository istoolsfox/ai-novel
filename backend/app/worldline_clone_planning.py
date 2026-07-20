import hashlib
from pathlib import Path
from typing import Any

from .database import connect, new_id, row_to_dict, rows_to_dicts, utc_now
from .storage import ensure_project_dirs
from .worldline_clone_core import _decode, _insert_copy, _json, _number, _row_mentions_future, _table_exists

MANIFEST_TABLES = (
    "chapters", "chapter_versions", "character_states", "character_knowledge",
    "memory_compilations", "story_facts", "relationship_states", "story_items",
    "item_ownership", "narrative_debts", "foreshadowing_states", "story_threads",
    "story_nodes", "story_edges", "impact_runs", "impact_targets", "rolling_plan_items",
)


def _copy_planning(conn, source_project_id: str, target_project_id: str, fork_chapter: int, id_map: dict[str, str]) -> None:
    if not _table_exists(conn, "rolling_plan_snapshots"):
        return
    snapshots = rows_to_dicts(
        conn.execute(
            "SELECT * FROM rolling_plan_snapshots WHERE project_id = ? AND source_chapter_number <= ? ORDER BY source_chapter_number, created_at",
            (source_project_id, fork_chapter),
        ).fetchall()
    )
    for snapshot in snapshots:
        source_chapter_id = str(snapshot.get("source_chapter_id") or "")
        if source_chapter_id and source_chapter_id not in id_map:
            continue
        _insert_copy(conn, "rolling_plan_snapshots", snapshot, id_map, overrides={"project_id": target_project_id})

    revisions = rows_to_dicts(
        conn.execute(
            "SELECT * FROM rolling_plan_item_revisions WHERE project_id = ? ORDER BY chapter_number, revision, created_at",
            (source_project_id,),
        ).fetchall()
    )
    for revision in revisions:
        if str(revision.get("snapshot_id") or "") not in id_map:
            continue
        _insert_copy(conn, "rolling_plan_item_revisions", revision, id_map, overrides={"project_id": target_project_id})

    latest: dict[int, dict[str, Any]] = {}
    cloned_revisions = rows_to_dicts(
        conn.execute(
            "SELECT * FROM rolling_plan_item_revisions WHERE project_id = ? ORDER BY chapter_number, revision, created_at",
            (target_project_id,),
        ).fetchall()
    )
    for revision in cloned_revisions:
        latest[_number(revision.get("chapter_number"))] = revision
    for chapter_number, revision in latest.items():
        payload = _decode(revision.get("new_payload"))
        if not isinstance(payload, dict) or chapter_number <= 0:
            continue
        snapshot_id = str(revision.get("snapshot_id") or "")
        snapshot = row_to_dict(
            conn.execute("SELECT * FROM rolling_plan_snapshots WHERE id = ?", (snapshot_id,)).fetchone()
        ) or {}
        now = utc_now()
        conn.execute(
            """
            INSERT INTO rolling_plan_items (
                id, project_id, chapter_number, status, locked, primary_thread_key,
                secondary_thread_keys, target_node_keys, goal, must_address, avoid,
                risk_score, source_snapshot_id, source_impact_run_id, revision,
                rationale, payload, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id(), target_project_id, chapter_number,
                str(payload.get("status") or "planned"),
                1 if payload.get("locked") else 0,
                str(payload.get("primary_thread_key") or ""),
                _json(payload.get("secondary_thread_keys") or []),
                _json(payload.get("target_node_keys") or []),
                str(payload.get("goal") or ""),
                _json(payload.get("must_address") or []),
                _json(payload.get("avoid") or []),
                float(payload.get("risk_score") or 0),
                snapshot_id,
                str(snapshot.get("source_impact_run_id") or ""),
                _number(revision.get("revision")) or 1,
                str(revision.get("reason") or "从分叉点继承的滚动计划。"),
                _json(payload), now, now,
            ),
        )

    source_items = rows_to_dicts(
        conn.execute(
            "SELECT * FROM rolling_plan_items WHERE project_id = ? ORDER BY chapter_number",
            (source_project_id,),
        ).fetchall()
    )
    existing_numbers = set(latest)
    for item in source_items:
        if _number(item.get("chapter_number")) in existing_numbers:
            continue
        if str(item.get("source_snapshot_id") or "") not in id_map:
            continue
        _insert_copy(conn, "rolling_plan_items", item, id_map, overrides={"project_id": target_project_id})


def _copy_wiki(conn, source_project_id: str, target_project_id: str, fork_chapter: int, id_map: dict[str, str]) -> None:
    revisions = rows_to_dicts(
        conn.execute(
            "SELECT * FROM wiki_page_revisions WHERE project_id = ? ORDER BY created_at",
            (source_project_id,),
        ).fetchall()
    )
    for revision in revisions:
        source_chapter_id = str(revision.get("source_chapter_id") or "")
        if source_chapter_id and source_chapter_id not in id_map:
            continue
        if _row_mentions_future(revision, fork_chapter):
            continue
        _insert_copy(conn, "wiki_page_revisions", revision, id_map, overrides={"project_id": target_project_id})
    latest: dict[str, dict[str, Any]] = {}
    rows = rows_to_dicts(
        conn.execute(
            "SELECT * FROM wiki_page_revisions WHERE project_id = ? ORDER BY created_at",
            (target_project_id,),
        ).fetchall()
    )
    for row in rows:
        latest[str(row.get("path") or "")] = row
    for path, revision in latest.items():
        if not path:
            continue
        now = utc_now()
        conn.execute(
            "INSERT INTO wiki_pages (id, project_id, path, title, content, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (new_id(), target_project_id, path, Path(path).stem, str(revision.get("content") or ""), now),
        )


def _write_project_files(project_id: str) -> None:
    root = ensure_project_dirs(project_id)
    with connect() as conn:
        chapters = rows_to_dicts(
            conn.execute(
                "SELECT * FROM chapters WHERE project_id = ? ORDER BY chapter_number",
                (project_id,),
            ).fetchall()
        )
        pages = rows_to_dicts(
            conn.execute("SELECT * FROM wiki_pages WHERE project_id = ?", (project_id,)).fetchall()
        )
    for chapter in chapters:
        path = root / "manuscript" / f"chapter-{int(chapter.get('chapter_number') or 0):03}.md"
        path.write_text(
            f"# {chapter.get('title') or '未命名章节'}\n\n{chapter.get('draft') or ''}",
            encoding="utf-8",
        )
    wiki_root = root / "memory" / "wiki"
    for page in pages:
        relative = str(page.get("path") or "").replace("\\", "/").strip("/")
        if not relative or relative.startswith("../") or "/../" in relative:
            continue
        target = wiki_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(page.get("content") or ""), encoding="utf-8")


def _manifest(conn, project_id: str, fork_chapter: int) -> tuple[dict[str, Any], str]:
    counts: dict[str, int] = {}
    for table in MANIFEST_TABLES:
        if _table_exists(conn, table):
            counts[table] = int(
                conn.execute(f"SELECT COUNT(*) FROM {table} WHERE project_id = ?", (project_id,)).fetchone()[0]
            )
    chapter_rows = rows_to_dicts(
        conn.execute(
            "SELECT chapter_number, title, draft, summary, status FROM chapters WHERE project_id = ? ORDER BY chapter_number",
            (project_id,),
        ).fetchall()
    )
    chapters = [
        {
            "chapter_number": row.get("chapter_number", 0),
            "title": row.get("title", ""),
            "status": row.get("status", ""),
            "draft_hash": hashlib.sha256(str(row.get("draft") or "").encode("utf-8")).hexdigest(),
            "summary_hash": hashlib.sha256(str(row.get("summary") or "").encode("utf-8")).hexdigest(),
        }
        for row in chapter_rows
    ]
    manifest = {
        "project_id": project_id,
        "fork_chapter_number": fork_chapter,
        "counts": counts,
        "chapters": chapters,
    }
    return manifest, hashlib.sha256(_json(manifest).encode("utf-8")).hexdigest()
