"""Application: blueprint service.

Use cases for volume blueprints: CRUD + approve.
"""
import json
from typing import Any

from fastapi import HTTPException

from .memory_service import create_structured_record, list_records_for_context, record_payload, sync_record_to_wiki
from ..infrastructure.database import (
    create_blueprint,
    delete_blueprint,
    get_blueprint,
    list_blueprints,
    update_blueprint,
)


def create_project_blueprint(project_id: str, blueprint: dict[str, Any]) -> dict[str, Any]:
    return create_blueprint(project_id, blueprint)


def list_project_blueprints(project_id: str) -> list[dict[str, Any]]:
    return list_blueprints(project_id)


def get_project_blueprint(project_id: str, blueprint_id: str) -> dict[str, Any]:
    bp = get_blueprint(blueprint_id)
    if not bp or bp["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return bp


def update_project_blueprint(project_id: str, blueprint_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    get_project_blueprint(project_id, blueprint_id)  # validate ownership
    result = update_blueprint(blueprint_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return result


def delete_project_blueprint(project_id: str, blueprint_id: str) -> dict[str, bool]:
    get_project_blueprint(project_id, blueprint_id)  # validate ownership
    ok = delete_blueprint(blueprint_id)
    return {"ok": ok}


def approve_blueprint(project_id: str, blueprint_id: str) -> dict[str, Any]:
    """Approve a blueprint (status -> active)."""
    blueprint = update_project_blueprint(project_id, blueprint_id, {"status": "active"})
    sync_blueprint_foreshadowings(project_id, blueprint)
    return blueprint


def sync_blueprint_foreshadowings(project_id: str, blueprint: dict[str, Any]) -> None:
    """Materialize blueprint foreshadowings into the editable foreshadowing registry."""
    blueprint_payload = _blueprint_payload(blueprint)
    items = blueprint_payload.get("key_foreshadowings") or []
    if not isinstance(items, list):
        return
    existing_records = list_records_for_context(project_id, "foreshadowings", 500)
    existing_by_key = {
        _foreshadowing_key(record_payload(record)): record
        for record in existing_records
        if record_payload(record).get("blueprint_id") == blueprint.get("id")
    }
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("title") or f"伏笔 {index}")
        payload = {
            "name": name,
            "setup_chapter": item.get("planted_in") or item.get("setup_chapter") or "",
            "payoff_chapter": item.get("payoff_in") or item.get("payoff_chapter") or "",
            "status": item.get("status") or "计划回收",
            "related_characters": item.get("related_characters") or "",
            "hint": item.get("description") or item.get("hint") or "",
            "blueprint_id": blueprint.get("id"),
            "volume_number": blueprint_payload.get("volume_number") or blueprint.get("volume_number"),
            "source": "blueprint",
        }
        key = _foreshadowing_key(payload)
        if key in existing_by_key:
            _update_foreshadowing_record(project_id, existing_by_key[key], payload)
            continue
        record = create_structured_record(
            project_id,
            "foreshadowings",
            name,
            "blueprint_foreshadowing",
            payload["hint"] or name,
            payload,
            "active",
        )
        sync_record_to_wiki(project_id, "foreshadowings", record)


def _foreshadowing_key(payload: dict[str, Any]) -> str:
    return "|".join(
        str(payload.get(key) or "")
        for key in ("name", "setup_chapter", "payoff_chapter")
    )


def _blueprint_payload(blueprint: dict[str, Any]) -> dict[str, Any]:
    raw = blueprint.get("blueprint_json")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {}
    elif isinstance(raw, dict):
        parsed = raw
    else:
        parsed = {}
    merged = dict(parsed)
    for key in ("id", "volume_number", "volume_title", "volume_arc", "status"):
        if blueprint.get(key) is not None:
            merged.setdefault(key, blueprint[key])
    return merged


def _update_foreshadowing_record(project_id: str, record: dict[str, Any], payload: dict[str, Any]) -> None:
    from ..infrastructure.database import connect, row_to_dict, utc_now

    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            UPDATE foreshadowings
            SET title = ?, category = ?, content = ?, payload = ?, status = ?, updated_at = ?
            WHERE id = ? AND project_id = ?
            """,
            (
                payload["name"],
                "blueprint_foreshadowing",
                payload["hint"] or payload["name"],
                json.dumps(payload, ensure_ascii=False),
                "active",
                now,
                record["id"],
                project_id,
            ),
        )
        updated = row_to_dict(conn.execute("SELECT * FROM foreshadowings WHERE id = ?", (record["id"],)).fetchone())
    if updated:
        sync_record_to_wiki(project_id, "foreshadowings", updated)
