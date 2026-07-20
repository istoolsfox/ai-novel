import hashlib
import json
import re
from typing import Any

from .database import connect, new_id, row_to_dict, rows_to_dicts, utc_now


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def stable_key(explicit: Any, *parts: Any, prefix: str) -> str:
    raw = str(explicit or "").strip()
    if raw:
        normalized = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", raw).strip("_")
        if normalized:
            return normalized[:120]
    source = "|".join(str(part or "").strip().lower() for part in parts)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def entity_key(entity_id: Any, entity_name: Any) -> str:
    return stable_key(entity_id, entity_name, prefix="entity")


def _latest_rows(project_id: str, table: str, key_columns: tuple[str, ...]) -> list[dict[str, Any]]:
    group_columns = ", ".join(key_columns)
    join_conditions = " AND ".join(f"latest.{column} = current.{column}" for column in key_columns)
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT current.*
            FROM {table} AS current
            JOIN (
                SELECT {group_columns}, MAX(source_chapter_number) AS max_chapter
                FROM {table}
                WHERE project_id = ?
                GROUP BY {group_columns}
            ) AS latest
              ON {join_conditions}
             AND latest.max_chapter = current.source_chapter_number
            WHERE current.project_id = ?
            ORDER BY current.source_chapter_number DESC, current.updated_at DESC
            """,
            (project_id, project_id),
        ).fetchall()
    return rows_to_dicts(rows)


def latest_story_facts(project_id: str) -> list[dict[str, Any]]:
    return _latest_rows(project_id, "story_facts", ("fact_key",))


def latest_relationship_states(project_id: str) -> list[dict[str, Any]]:
    return _latest_rows(
        project_id,
        "relationship_states",
        ("source_character_key", "target_character_key", "relation_type"),
    )


def latest_item_ownership(project_id: str) -> list[dict[str, Any]]:
    return _latest_rows(project_id, "item_ownership", ("item_key",))


def latest_narrative_debts(project_id: str, *, open_only: bool = False) -> list[dict[str, Any]]:
    rows = _latest_rows(project_id, "narrative_debts", ("debt_key",))
    if not open_only:
        return rows
    return [row for row in rows if str(row.get("status") or "") in {"open", "progressed"}]


def latest_foreshadowings(project_id: str, *, active_only: bool = False) -> list[dict[str, Any]]:
    rows = _latest_rows(project_id, "foreshadowing_states", ("foreshadowing_key",))
    if not active_only:
        return rows
    return [row for row in rows if str(row.get("status") or "") in {"planted", "deepened"}]


def list_memory_compilations(project_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                """
                SELECT * FROM memory_compilations
                WHERE project_id = ?
                ORDER BY chapter_number DESC, updated_at DESC
                """,
                (project_id,),
            ).fetchall()
        )


def memory_context(project_id: str) -> dict[str, Any]:
    facts = [
        {
            "fact_key": row.get("fact_key", ""),
            "fact_text": row.get("fact_text", ""),
            "fact_status": row.get("fact_status", ""),
            "confidence": row.get("confidence", 0),
        }
        for row in latest_story_facts(project_id)
        if str(row.get("fact_status") or "") != "retracted"
    ]
    relationships = [
        {
            "source_character_name": row.get("source_character_name", ""),
            "target_character_name": row.get("target_character_name", ""),
            "relation_type": row.get("relation_type", ""),
            "value": row.get("value", 0),
            "status": row.get("status", ""),
            "reason": row.get("reason", ""),
        }
        for row in latest_relationship_states(project_id)
        if str(row.get("status") or "") != "ended"
    ]
    items = [
        {
            "item_key": row.get("item_key", ""),
            "item_name": row.get("item_name", ""),
            "owner_type": row.get("owner_type", ""),
            "owner_name": row.get("owner_name", ""),
            "location": row.get("location", ""),
            "status": row.get("status", ""),
        }
        for row in latest_item_ownership(project_id)
        if str(row.get("status") or "") not in {"destroyed", "consumed"}
    ]
    debts = [
        {
            "debt_key": row.get("debt_key", ""),
            "debt_type": row.get("debt_type", ""),
            "description": row.get("description", ""),
            "priority": row.get("priority", 0),
            "deadline_chapter": row.get("deadline_chapter", 0),
            "status": row.get("status", ""),
        }
        for row in latest_narrative_debts(project_id, open_only=True)
    ]
    foreshadowings = [
        {
            "foreshadowing_key": row.get("foreshadowing_key", ""),
            "title": row.get("title", ""),
            "description": row.get("description", ""),
            "priority": row.get("priority", 0),
            "setup_chapter": row.get("setup_chapter", 0),
            "status": row.get("status", ""),
        }
        for row in latest_foreshadowings(project_id, active_only=True)
    ]
    return {
        "hard_facts": facts[:80],
        "relationship_states": relationships[:80],
        "item_ownership": items[:80],
        "narrative_debts": debts[:80],
        "active_foreshadowings": foreshadowings[:80],
    }


def begin_compilation(
    conn,
    step: dict[str, Any],
    memory: dict[str, Any],
    *,
    model: str = "",
) -> tuple[str, str]:
    payload_text = json_text(memory)
    content_hash = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
    existing = row_to_dict(
        conn.execute(
            """
            SELECT * FROM memory_compilations
            WHERE project_id = ? AND chapter_id = ?
            """,
            (step["project_id"], step["chapter_id"]),
        ).fetchone()
    )
    compilation_id = str(existing.get("id")) if existing else new_id()
    now = utc_now()
    conn.execute(
        """
        INSERT INTO memory_compilations (
            id, project_id, chapter_id, chapter_number, model,
            content_hash, payload, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'committed', ?, ?)
        ON CONFLICT(project_id, chapter_id) DO UPDATE SET
            chapter_number = excluded.chapter_number,
            model = excluded.model,
            content_hash = excluded.content_hash,
            payload = excluded.payload,
            status = 'committed',
            updated_at = excluded.updated_at
        """,
        (
            compilation_id,
            step["project_id"],
            step["chapter_id"],
            step["chapter_number"],
            model,
            content_hash,
            payload_text,
            now,
            now,
        ),
    )
    return compilation_id, now


def clear_chapter_layers(conn, step: dict[str, Any]) -> None:
    chapter_id = step["chapter_id"]
    project_id = step["project_id"]
    for table, source_column in (
        ("story_facts", "source_chapter_id"),
        ("relationship_states", "source_chapter_id"),
        ("story_items", "source_chapter_id"),
        ("item_ownership", "source_chapter_id"),
        ("narrative_debts", "source_chapter_id"),
        ("foreshadowing_states", "source_chapter_id"),
    ):
        conn.execute(
            f"DELETE FROM {table} WHERE project_id = ? AND {source_column} = ?",
            (project_id, chapter_id),
        )


def persist_extended_layers(
    conn,
    step: dict[str, Any],
    memory: dict[str, Any],
    compilation_id: str,
    now: str,
) -> None:
    clear_chapter_layers(conn, step)
    for item in memory.get("hard_facts") or []:
        if isinstance(item, dict):
            _insert_fact(conn, step, item, compilation_id, now)
    for item in memory.get("relationship_changes") or []:
        if isinstance(item, dict):
            _insert_relationship(conn, step, item, compilation_id, now)
    for item in memory.get("item_changes") or []:
        if isinstance(item, dict):
            _insert_item(conn, step, item, compilation_id, now)
    for item in memory.get("narrative_debt_changes") or []:
        if isinstance(item, dict):
            _insert_debt(conn, step, item, compilation_id, now)
    for item in memory.get("foreshadowing_changes") or []:
        if isinstance(item, dict):
            _insert_foreshadowing(conn, step, item, compilation_id, now)


def _confidence(value: Any) -> float:
    try:
        return max(0.0, min(float(value or 0), 1.0))
    except (TypeError, ValueError):
        return 0.0


def _priority(value: Any) -> float:
    return _confidence(value)


def _integer(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _insert_fact(conn, step, item, compilation_id, now) -> None:
    fact_text = str(item.get("fact_text") or "").strip()
    if not fact_text:
        return
    key = stable_key(item.get("fact_key"), fact_text, prefix="fact")
    conn.execute(
        """
        INSERT INTO story_facts (
            id, project_id, fact_key, fact_text, fact_status, confidence,
            source_chapter_id, source_chapter_number, compilation_id,
            payload, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id(), step["project_id"], key, fact_text,
            str(item.get("fact_status") or "confirmed"),
            _confidence(item.get("confidence")),
            step["chapter_id"], step["chapter_number"], compilation_id,
            json_text(item), now, now,
        ),
    )


def _insert_relationship(conn, step, item, compilation_id, now) -> None:
    source_id = str(item.get("source_character_id") or "")
    source_name = str(item.get("source_character_name") or "")
    target_id = str(item.get("target_character_id") or "")
    target_name = str(item.get("target_character_name") or "")
    relation_type = str(item.get("relation_type") or "unspecified").strip()
    if not (source_id or source_name) or not (target_id or target_name):
        return
    try:
        value = max(-1.0, min(float(item.get("value") or 0), 1.0))
    except (TypeError, ValueError):
        value = 0.0
    conn.execute(
        """
        INSERT INTO relationship_states (
            id, project_id, source_character_key, source_character_id,
            source_character_name, target_character_key, target_character_id,
            target_character_name, relation_type, value, status, reason,
            source_chapter_id, source_chapter_number, compilation_id,
            payload, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id(), step["project_id"], entity_key(source_id, source_name),
            source_id, source_name, entity_key(target_id, target_name),
            target_id, target_name, relation_type, value,
            str(item.get("status") or "active"), str(item.get("reason") or ""),
            step["chapter_id"], step["chapter_number"], compilation_id,
            json_text(item), now, now,
        ),
    )


def _insert_item(conn, step, item, compilation_id, now) -> None:
    item_name = str(item.get("item_name") or "").strip()
    item_key = stable_key(item.get("item_key"), item_name, item.get("description"), prefix="item")
    if not item_name and not item.get("item_key"):
        return
    description = str(item.get("description") or "")
    item_status = str(item.get("item_status") or item.get("status") or "active")
    conn.execute(
        """
        INSERT INTO story_items (
            id, project_id, item_key, item_name, description, status,
            source_chapter_id, source_chapter_number, compilation_id,
            payload, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id(), step["project_id"], item_key, item_name, description,
            item_status, step["chapter_id"], step["chapter_number"],
            compilation_id, json_text(item), now, now,
        ),
    )
    owner_id = str(item.get("owner_id") or "")
    owner_name = str(item.get("owner_name") or "")
    owner_type = str(item.get("owner_type") or "unknown")
    owner_key = stable_key(owner_id, owner_name, owner_type, prefix="owner") if (owner_id or owner_name) else ""
    conn.execute(
        """
        INSERT INTO item_ownership (
            id, project_id, item_key, item_name, owner_type, owner_key,
            owner_name, location, status, source_chapter_id,
            source_chapter_number, compilation_id, payload, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id(), step["project_id"], item_key, item_name, owner_type,
            owner_key, owner_name, str(item.get("location") or ""),
            str(item.get("ownership_status") or item.get("change_type") or "held"),
            step["chapter_id"], step["chapter_number"], compilation_id,
            json_text(item), now, now,
        ),
    )


def _insert_debt(conn, step, item, compilation_id, now) -> None:
    description = str(item.get("description") or "").strip()
    if not description:
        return
    key = stable_key(item.get("debt_key"), item.get("debt_type"), description, prefix="debt")
    conn.execute(
        """
        INSERT INTO narrative_debts (
            id, project_id, debt_key, debt_type, description, status,
            priority, deadline_chapter, source_chapter_id,
            source_chapter_number, compilation_id, payload, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id(), step["project_id"], key,
            str(item.get("debt_type") or "open_question"), description,
            str(item.get("status") or "open"), _priority(item.get("priority")),
            _integer(item.get("deadline_chapter")), step["chapter_id"],
            step["chapter_number"], compilation_id, json_text(item), now, now,
        ),
    )


def _insert_foreshadowing(conn, step, item, compilation_id, now) -> None:
    title = str(item.get("title") or "").strip()
    description = str(item.get("description") or "").strip()
    if not title and not description:
        return
    key = stable_key(item.get("foreshadowing_key"), title, description, prefix="foreshadow")
    conn.execute(
        """
        INSERT INTO foreshadowing_states (
            id, project_id, foreshadowing_key, title, description, status,
            setup_chapter, payoff_chapter, priority, source_chapter_id,
            source_chapter_number, compilation_id, payload, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id(), step["project_id"], key, title, description,
            str(item.get("status") or "planted"),
            _integer(item.get("setup_chapter") or step["chapter_number"]),
            _integer(item.get("payoff_chapter")), _priority(item.get("priority")),
            step["chapter_id"], step["chapter_number"], compilation_id,
            json_text(item), now, now,
        ),
    )
