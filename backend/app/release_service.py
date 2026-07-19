import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .backup_service import list_database_backups
from .database import connect, database_path, row_to_dict, utc_now
from .migration_service import migration_status
from .runtime_queue import runtime_diagnostics, runtime_sync_enabled
from .secret_store import security_status
from .version import application_version, build_metadata, release_channel

CAPABILITIES = [
    "autopilot",
    "continuity",
    "layered-memory",
    "story-graph",
    "impact-planning",
    "worldlines",
    "obsidian-export",
    "independent-worker",
    "backup-restore",
    "automatic-backups",
    "encrypted-credentials",
    "versioned-migrations",
    "release-artifacts",
]


def _decode(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _ensure_release_state() -> None:
    with connect() as conn:
        tables = {str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "application_state" not in tables:
            return
        columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(application_state)").fetchall()}
        if "setup_payload" not in columns:
            return
        now = utc_now()
        conn.execute(
            """
            INSERT INTO application_state (
                id, installed_version, release_channel, first_run_completed,
                setup_step, setup_payload, created_at, updated_at
            ) VALUES ('current', ?, ?, 0, 'welcome', '{}', ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                installed_version=excluded.installed_version,
                release_channel=excluded.release_channel,
                updated_at=excluded.updated_at
            """,
            (application_version(), release_channel(), now, now),
        )


def setup_state() -> dict[str, Any]:
    _ensure_release_state()
    with connect() as conn:
        try:
            row = row_to_dict(conn.execute("SELECT * FROM application_state WHERE id='current'").fetchone())
        except sqlite3.OperationalError:
            row = None
    if not row:
        return {
            "id": "current",
            "installed_version": application_version(),
            "release_channel": release_channel(),
            "first_run_completed": False,
            "setup_step": "migration-required",
            "setup_payload": {},
            "completed_at": "",
            "updated_at": utc_now(),
        }
    row["first_run_completed"] = bool(row.get("first_run_completed"))
    row["setup_payload"] = _decode(row.get("setup_payload"))
    return row


def update_setup_state(*, setup_step: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_release_state()
    allowed_steps = {"welcome", "storage", "security", "model", "worker", "backup", "review", "completed"}
    step = setup_step if setup_step in allowed_steps else "welcome"
    with connect() as conn:
        conn.execute(
            """
            UPDATE application_state
            SET setup_step=?, setup_payload=?, updated_at=?
            WHERE id='current'
            """,
            (step, json.dumps(payload or {}, ensure_ascii=False), utc_now()),
        )
    return setup_state()


def _database_readiness() -> dict[str, Any]:
    path = database_path()
    try:
        with connect() as conn:
            quick = str(conn.execute("PRAGMA quick_check").fetchone()[0])
        return {"ok": quick.lower() == "ok", "detail": quick, "path": str(path)}
    except sqlite3.Error as exc:
        return {"ok": False, "detail": str(exc), "path": str(path)}


def _storage_readiness() -> dict[str, Any]:
    target = database_path().parent
    target.mkdir(parents=True, exist_ok=True)
    probe = target / ".release-readiness.tmp"
    try:
        probe.write_text(utc_now(), encoding="utf-8")
        probe.unlink(missing_ok=True)
        return {"ok": True, "detail": "writable", "path": str(target)}
    except OSError as exc:
        probe.unlink(missing_ok=True)
        return {"ok": False, "detail": str(exc), "path": str(target)}


def release_readiness() -> dict[str, Any]:
    schema = migration_status()
    security = security_status()
    runtime = runtime_diagnostics()
    database = _database_readiness()
    storage = _storage_readiness()
    with connect() as conn:
        try:
            project_count = int(conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0])
        except sqlite3.OperationalError:
            project_count = 0
        try:
            credential_count = int(conn.execute("SELECT COUNT(*) FROM encrypted_credentials WHERE status='active'").fetchone()[0])
        except sqlite3.OperationalError:
            credential_count = 0
        try:
            model_count = int(conn.execute("SELECT COUNT(*) FROM model_configs WHERE status='active'").fetchone()[0])
        except sqlite3.OperationalError:
            model_count = 0

    checks = [
        {"id": "database", "label": "SQLite 完整性", "status": "pass" if database["ok"] else "fail", "required": True, "detail": database["detail"]},
        {"id": "storage", "label": "数据目录可写", "status": "pass" if storage["ok"] else "fail", "required": True, "detail": storage["path"]},
        {"id": "migrations", "label": "数据库迁移", "status": "pass" if schema["status"] == "current" else "fail", "required": True, "detail": f"{schema['current_version']}/{schema['latest_version']} · {schema['status']}"},
        {"id": "security", "label": "凭证加密", "status": "pass" if security["status"] == "ok" else "fail", "required": True, "detail": f"{security['credential_count']} credentials · {security['unreadable_credentials']} unreadable"},
        {"id": "project", "label": "小说项目", "status": "pass" if project_count else "warning", "required": False, "detail": f"{project_count} projects"},
        {"id": "model", "label": "模型配置", "status": "pass" if model_count and credential_count else "warning", "required": False, "detail": f"{model_count} configs · {credential_count} active credentials"},
        {"id": "worker", "label": "独立 Worker", "status": "pass" if runtime_sync_enabled() or runtime.get("active_workers") else "warning", "required": False, "detail": "sync mode" if runtime_sync_enabled() else f"{runtime.get('active_workers', 0)} healthy"},
        {"id": "backup", "label": "数据库备份", "status": "pass" if list_database_backups() else "warning", "required": False, "detail": f"{len(list_database_backups())} backups"},
    ]
    blockers = [item for item in checks if item["required"] and item["status"] != "pass"]
    warnings = [item for item in checks if not item["required"] and item["status"] != "pass"]
    return {
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "schema": schema,
        "security": security,
        "runtime": runtime,
        "checked_at": utc_now(),
    }


def complete_setup(*, confirmation: str, acknowledge_without_model: bool = False) -> dict[str, Any]:
    if confirmation != "COMPLETE_SETUP":
        raise ValueError("Setup confirmation must be COMPLETE_SETUP")
    readiness = release_readiness()
    if not readiness["ready"]:
        raise ValueError("Required release readiness checks have not passed")
    model_warning = next((item for item in readiness["warnings"] if item["id"] == "model"), None)
    if model_warning and not acknowledge_without_model:
        raise ValueError("Configure a model credential or explicitly acknowledge stub-only mode")
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            UPDATE application_state
            SET installed_version=?, release_channel=?, first_run_completed=1,
                setup_step='completed', completed_at=?, last_readiness_at=?, updated_at=?
            WHERE id='current'
            """,
            (application_version(), release_channel(), now, now, now),
        )
    return {"status": "completed", "state": setup_state(), "readiness": readiness}


def reset_setup(*, confirmation: str) -> dict[str, Any]:
    if confirmation != "RESET_SETUP":
        raise ValueError("Setup reset confirmation must be RESET_SETUP")
    with connect() as conn:
        conn.execute(
            """
            UPDATE application_state
            SET first_run_completed=0, setup_step='welcome', setup_payload='{}',
                completed_at='', updated_at=?
            WHERE id='current'
            """,
            (utc_now(),),
        )
    return setup_state()


def release_info() -> dict[str, Any]:
    state = setup_state()
    schema = migration_status()
    metadata = build_metadata()
    return {
        **metadata,
        "schema_version": schema["current_version"],
        "latest_schema_version": schema["latest_version"],
        "setup_completed": state["first_run_completed"],
        "setup_step": state["setup_step"],
        "capabilities": CAPABILITIES,
        "python": os.sys.version.split()[0],
        "database_path": str(database_path()),
        "data_directory": str(database_path().parent),
    }
