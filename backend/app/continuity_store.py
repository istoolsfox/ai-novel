import json
from typing import Any

from fastapi import HTTPException

from .database import connect, new_id, row_to_dict, rows_to_dicts, utc_now


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def character_key(character_id: str, character_name: str) -> str:
    return character_id.strip() or character_name.strip().lower() or "unknown"


def require_project(project_id: str) -> dict[str, Any]:
    with connect() as conn:
        project = row_to_dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def require_chapter(project_id: str, chapter_id: str) -> dict[str, Any]:
    require_project(project_id)
    with connect() as conn:
        chapter = row_to_dict(
            conn.execute(
                "SELECT * FROM chapters WHERE id = ? AND project_id = ?",
                (chapter_id, project_id),
            ).fetchone()
        )
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found in project")
    return chapter


def latest_bridge_before(project_id: str, chapter_number: int) -> dict[str, Any] | None:
    with connect() as conn:
        return row_to_dict(
            conn.execute(
                """
                SELECT * FROM chapter_bridges
                WHERE project_id = ? AND chapter_number < ? AND status = 'active'
                ORDER BY chapter_number DESC, updated_at DESC
                LIMIT 1
                """,
                (project_id, chapter_number),
            ).fetchone()
        )


def latest_contract(project_id: str, chapter_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        return row_to_dict(
            conn.execute(
                """
                SELECT * FROM chapter_contracts
                WHERE project_id = ? AND chapter_id = ?
                ORDER BY updated_at DESC LIMIT 1
                """,
                (project_id, chapter_id),
            ).fetchone()
        )


def latest_check(project_id: str, chapter_id: str, stage: str | None = None) -> dict[str, Any] | None:
    sql = "SELECT * FROM continuity_checks WHERE project_id = ? AND chapter_id = ?"
    params: list[Any] = [project_id, chapter_id]
    if stage:
        sql += " AND stage = ?"
        params.append(stage)
    sql += " ORDER BY created_at DESC LIMIT 1"
    with connect() as conn:
        return row_to_dict(conn.execute(sql, tuple(params)).fetchone())


def latest_character_states(project_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT state.*
            FROM character_states AS state
            JOIN (
                SELECT character_key, MAX(chapter_number) AS max_chapter
                FROM character_states
                WHERE project_id = ?
                GROUP BY character_key
            ) AS latest
              ON latest.character_key = state.character_key
             AND latest.max_chapter = state.chapter_number
            WHERE state.project_id = ?
            ORDER BY state.character_name
            """,
            (project_id, project_id),
        ).fetchall()
    return rows_to_dicts(rows)


def latest_character_knowledge(project_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT knowledge.*
            FROM character_knowledge AS knowledge
            JOIN (
                SELECT character_key, fact_key, MAX(source_chapter_number) AS max_chapter
                FROM character_knowledge
                WHERE project_id = ?
                GROUP BY character_key, fact_key
            ) AS latest
              ON latest.character_key = knowledge.character_key
             AND latest.fact_key = knowledge.fact_key
             AND latest.max_chapter = knowledge.source_chapter_number
            WHERE knowledge.project_id = ?
            ORDER BY knowledge.character_name, knowledge.fact_key
            """,
            (project_id, project_id),
        ).fetchall()
    return rows_to_dicts(rows)


def fallback_previous_state(project_id: str, chapter_number: int) -> dict[str, Any]:
    with connect() as conn:
        previous = row_to_dict(
            conn.execute(
                """
                SELECT * FROM chapters
                WHERE project_id = ? AND chapter_number < ? AND status = 'final'
                ORDER BY chapter_number DESC LIMIT 1
                """,
                (project_id, chapter_number),
            ).fetchone()
        )
    if not previous:
        return {}
    draft = str(previous.get("draft") or "")
    summary = str(previous.get("summary") or previous.get("brief") or draft[-300:])
    return {
        "source_chapter_id": previous.get("id", ""),
        "source_chapter_number": previous.get("chapter_number", 0),
        "ending_state": {"time": "", "location": "", "current_action": summary, "current_danger": ""},
        "character_states": [],
        "relationship_changes": [],
        "open_actions": [],
        "open_hooks": [],
        "emotional_residue": [],
        "forbidden_repetition": [summary],
        "next_chapter_seeds": [summary],
    }


def persist_contract(conn, step: dict[str, Any], contract: dict[str, Any]) -> None:
    now = utc_now()
    conn.execute(
        """
        INSERT INTO chapter_contracts (
            id, project_id, chapter_id, chapter_number, previous_bridge_id,
            payload, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
        ON CONFLICT(project_id, chapter_id) DO UPDATE SET
            chapter_number = excluded.chapter_number,
            previous_bridge_id = excluded.previous_bridge_id,
            payload = excluded.payload,
            status = 'active',
            updated_at = excluded.updated_at
        """,
        (
            new_id(), step["project_id"], step["chapter_id"], step["chapter_number"],
            str(contract.get("source_bridge_id") or ""), json_text(contract), now, now,
        ),
    )


def persist_check(project_id: str, chapter_id: str, chapter_number: int, check: dict[str, Any]) -> None:
    with connect() as conn:
        insert_check(conn, project_id, chapter_id, chapter_number, check)


def insert_check(conn, project_id: str, chapter_id: str, chapter_number: int, check: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO continuity_checks (
            id, project_id, chapter_id, chapter_number, stage, status, score, payload, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id(), project_id, chapter_id, chapter_number,
            str(check.get("stage") or "initial"), str(check.get("status") or "warning"),
            float(check.get("score") or 0), json_text(check), utc_now(),
        ),
    )


def persist_bridge_and_memory(conn, step: dict[str, Any], memory: dict[str, Any]) -> None:
    now = utc_now()
    conn.execute(
        """
        INSERT INTO chapter_bridges (
            id, project_id, chapter_id, chapter_number, payload, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
        ON CONFLICT(project_id, chapter_id) DO UPDATE SET
            chapter_number = excluded.chapter_number,
            payload = excluded.payload,
            status = 'active',
            updated_at = excluded.updated_at
        """,
        (new_id(), step["project_id"], step["chapter_id"], step["chapter_number"], json_text(memory), now, now),
    )
    conn.execute(
        "UPDATE chapters SET summary = ?, updated_at = ? WHERE id = ? AND project_id = ?",
        (str(memory.get("summary") or ""), now, step["chapter_id"], step["project_id"]),
    )

    for state in memory.get("character_states") or []:
        _upsert_character_state(conn, step, state, now)
    for knowledge in memory.get("knowledge_changes") or []:
        _upsert_character_knowledge(conn, step, knowledge, now)


def _upsert_character_state(conn, step: dict[str, Any], state: dict[str, Any], now: str) -> None:
    character_id = str(state.get("character_id") or "")
    character_name = str(state.get("character_name") or "")
    key = character_key(character_id, character_name)
    conn.execute(
        """
        INSERT INTO character_states (
            id, project_id, character_key, character_id, character_name, chapter_id,
            chapter_number, location, physical_state, emotional_state, current_goal,
            alive_status, visibility_status, payload, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id, character_key, chapter_id) DO UPDATE SET
            character_id = excluded.character_id,
            character_name = excluded.character_name,
            chapter_number = excluded.chapter_number,
            location = excluded.location,
            physical_state = excluded.physical_state,
            emotional_state = excluded.emotional_state,
            current_goal = excluded.current_goal,
            alive_status = excluded.alive_status,
            visibility_status = excluded.visibility_status,
            payload = excluded.payload,
            updated_at = excluded.updated_at
        """,
        (
            new_id(), step["project_id"], key, character_id, character_name,
            step["chapter_id"], step["chapter_number"], str(state.get("location") or ""),
            str(state.get("physical_state") or ""), str(state.get("emotional_state") or ""),
            str(state.get("current_goal") or ""), str(state.get("alive_status") or "alive"),
            str(state.get("visibility_status") or "public"), json_text(state), now, now,
        ),
    )


def _upsert_character_knowledge(conn, step: dict[str, Any], item: dict[str, Any], now: str) -> None:
    character_id = str(item.get("character_id") or "")
    character_name = str(item.get("character_name") or "")
    fact_text = str(item.get("fact_text") or "")
    fact_key = str(item.get("fact_key") or fact_text[:80] or new_id())
    try:
        confidence = max(0.0, min(float(item.get("confidence") or 0), 1.0))
    except (TypeError, ValueError):
        confidence = 0.0
    conn.execute(
        """
        INSERT INTO character_knowledge (
            id, project_id, character_key, character_id, character_name,
            fact_key, fact_text, knowledge_status, confidence,
            source_chapter_id, source_chapter_number, payload, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id, character_key, fact_key, source_chapter_id) DO UPDATE SET
            fact_text = excluded.fact_text,
            knowledge_status = excluded.knowledge_status,
            confidence = excluded.confidence,
            payload = excluded.payload,
            updated_at = excluded.updated_at
        """,
        (
            new_id(), step["project_id"], character_key(character_id, character_name),
            character_id, character_name, fact_key, fact_text,
            str(item.get("knowledge_status") or "suspected"), confidence,
            step["chapter_id"], step["chapter_number"], json_text(item), now, now,
        ),
    )
