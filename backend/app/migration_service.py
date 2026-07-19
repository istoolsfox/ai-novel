import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .backup_service import create_database_backup, get_database_backup, restore_database_backup
from .database import connect, database_path, new_id, row_to_dict, rows_to_dicts, utc_now
from .runtime_queue import runtime_diagnostics

MigrationCallback = Callable[[sqlite3.Connection], None]


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    description: str
    apply: MigrationCallback

    @property
    def checksum(self) -> str:
        material = f"{self.version}:{self.name}:{self.description}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()


def _metadata(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO application_metadata (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
        """,
        (key, value, utc_now()),
    )


def _migration_1(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS application_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        );
        """
    )
    _metadata(conn, "schema_management", "versioned")
    _metadata(conn, "schema_baseline", "phase-12")


def _migration_2(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_security_events_project_created
        ON security_events(project_id, created_at);

        CREATE INDEX IF NOT EXISTS idx_runtime_events_project_created
        ON runtime_events(project_id, created_at);
        """
    )
    _metadata(conn, "credential_schema", "encrypted-v1")


def _migration_3(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS application_state (
            id TEXT PRIMARY KEY,
            installed_version TEXT NOT NULL DEFAULT '0.0.0-dev',
            release_channel TEXT NOT NULL DEFAULT 'development',
            first_run_completed INTEGER NOT NULL DEFAULT 0,
            setup_step TEXT NOT NULL DEFAULT 'welcome',
            last_upgrade_at TEXT DEFAULT '',
            last_upgrade_backup_id TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    now = utc_now()
    conn.execute(
        """
        INSERT INTO application_state (
            id, installed_version, release_channel, first_run_completed,
            setup_step, created_at, updated_at
        ) VALUES ('current', '0.0.0-dev', 'development', 0, 'welcome', ?, ?)
        ON CONFLICT(id) DO NOTHING
        """,
        (now, now),
    )
    _metadata(conn, "upgrade_engine", "snapshot-rollback-v1")


MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, "adopt_versioned_schema", "Adopt existing phase-one through phase-twelve databases into a checksummed migration history.", _migration_1),
    Migration(2, "security_runtime_indexes", "Add project-aware security and runtime event indexes and mark encrypted credential schema v1.", _migration_2),
    Migration(3, "application_release_state", "Add persistent release channel and first-run setup state for formal releases.", _migration_3),
)

LATEST_SCHEMA_VERSION = MIGRATIONS[-1].version


def init_migration_schema() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                duration_ms INTEGER NOT NULL DEFAULT 0,
                backup_id TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS migration_runs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                from_version INTEGER NOT NULL DEFAULT 0,
                to_version INTEGER NOT NULL DEFAULT 0,
                planned_versions TEXT NOT NULL DEFAULT '[]',
                applied_versions TEXT NOT NULL DEFAULT '[]',
                backup_id TEXT DEFAULT '',
                error_message TEXT DEFAULT '',
                started_at TEXT NOT NULL,
                completed_at TEXT DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_migration_runs_started
            ON migration_runs(started_at);
            """
        )


def _decode_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def migration_history() -> list[dict[str, Any]]:
    init_migration_schema()
    with connect() as conn:
        return rows_to_dicts(conn.execute("SELECT * FROM schema_migrations ORDER BY version").fetchall())


def migration_runs(limit: int = 100) -> list[dict[str, Any]]:
    init_migration_schema()
    safe_limit = max(1, min(int(limit), 500))
    with connect() as conn:
        rows = rows_to_dicts(conn.execute("SELECT * FROM migration_runs ORDER BY started_at DESC LIMIT ?", (safe_limit,)).fetchall())
    for row in rows:
        row["planned_versions"] = _decode_list(row.get("planned_versions"))
        row["applied_versions"] = _decode_list(row.get("applied_versions"))
    return rows


def migration_status() -> dict[str, Any]:
    init_migration_schema()
    applied_rows = migration_history()
    applied_by_version = {int(row["version"]): row for row in applied_rows}
    known_by_version = {migration.version: migration for migration in MIGRATIONS}
    drift: list[dict[str, Any]] = []
    unknown: list[int] = []
    for version, row in applied_by_version.items():
        known = known_by_version.get(version)
        if not known:
            unknown.append(version)
        elif str(row.get("checksum") or "") != known.checksum:
            drift.append({
                "version": version,
                "name": known.name,
                "expected_checksum": known.checksum,
                "stored_checksum": row.get("checksum", ""),
            })
    pending = [migration for migration in MIGRATIONS if migration.version not in applied_by_version]
    current = max(applied_by_version, default=0)
    return {
        "status": "drift" if drift or unknown else ("pending" if pending else "current"),
        "current_version": current,
        "latest_version": LATEST_SCHEMA_VERSION,
        "pending": [migration_payload(item) for item in pending],
        "applied": applied_rows,
        "drift": drift,
        "unknown_versions": sorted(unknown),
        "auto_migrate": os.getenv("AI_NOVEL_AUTO_MIGRATE", "1").lower() not in {"0", "false", "no"},
    }


def migration_payload(migration: Migration) -> dict[str, Any]:
    return {
        "version": migration.version,
        "name": migration.name,
        "description": migration.description,
        "checksum": migration.checksum,
    }


def migration_plan() -> dict[str, Any]:
    status = migration_status()
    diagnostics = runtime_diagnostics()
    blockers = _upgrade_blockers(diagnostics)
    return {
        **status,
        "blockers": blockers,
        "can_apply": not blockers and not status["drift"] and not status["unknown_versions"],
        "will_create_backup": bool(status["pending"]),
    }


def _upgrade_blockers(diagnostics: dict[str, Any] | None = None) -> list[str]:
    data = diagnostics or runtime_diagnostics()
    blockers: list[str] = []
    if int(data.get("active_workers") or 0):
        blockers.append("Stop all healthy runtime workers before applying or rolling back schema migrations.")
    active_jobs = sum(int(data.get("generation_jobs", {}).get(status, 0)) for status in ("queued", "running", "paused"))
    active_tasks = sum(int(data.get("runtime_tasks", {}).get(status, 0)) for status in ("queued", "running"))
    if active_jobs:
        blockers.append("Finish or cancel queued, running, and paused generation jobs before upgrading.")
    if active_tasks:
        blockers.append("Finish queued and running runtime tasks before upgrading.")
    return blockers


def _record_run(run_id: str, **fields: Any) -> None:
    if not fields:
        return
    assignments = ", ".join(f"{key}=?" for key in fields)
    with connect() as conn:
        conn.execute(f"UPDATE migration_runs SET {assignments} WHERE id=?", (*fields.values(), run_id))


def _restore_snapshot_without_bootstrap(backup_id: str) -> None:
    backup = get_database_backup(backup_id, verify=True)
    source_path = Path(str(backup["file_path"])).resolve()
    destination = database_path()
    temporary = destination.with_suffix(".migration-restore.tmp.sqlite")
    temporary.unlink(missing_ok=True)
    source = sqlite3.connect(source_path, timeout=30)
    target = sqlite3.connect(temporary, timeout=30)
    try:
        source.backup(target)
        target.commit()
        integrity = str(target.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity.lower() != "ok":
            raise ValueError(f"Migration rollback integrity check failed: {integrity}")
    finally:
        target.close()
        source.close()
    for suffix in ("-wal", "-shm"):
        Path(f"{destination}{suffix}").unlink(missing_ok=True)
    os.replace(temporary, destination)


def apply_pending_migrations(*, confirmation: str = "APPLY", automatic: bool = False) -> dict[str, Any]:
    if not automatic and confirmation != "APPLY":
        raise ValueError("Migration confirmation must be APPLY")
    init_migration_schema()
    plan = migration_plan()
    if plan["drift"] or plan["unknown_versions"]:
        raise ValueError("Migration history drift detected; automatic application is blocked")
    if plan["blockers"]:
        raise ValueError(" ".join(plan["blockers"]))
    pending_versions = [int(item["version"]) for item in plan["pending"]]
    if not pending_versions:
        return {"status": "current", "applied_versions": [], "backup": None, "schema": migration_status()}

    backup = create_database_backup(
        note=f"Automatic pre-upgrade backup before schema {plan['current_version']} -> {plan['latest_version']}",
        backup_kind="pre_upgrade",
    )
    run_id = new_id()
    started = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO migration_runs (
                id, status, from_version, to_version, planned_versions,
                applied_versions, backup_id, started_at
            ) VALUES (?, 'running', ?, ?, ?, '[]', ?, ?)
            """,
            (run_id, plan["current_version"], plan["latest_version"], json.dumps(pending_versions), backup["id"], started),
        )

    applied: list[int] = []
    try:
        known = {migration.version: migration for migration in MIGRATIONS}
        for version in pending_versions:
            migration = known[version]
            began = time.perf_counter()
            with connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                migration.apply(conn)
                duration_ms = int((time.perf_counter() - began) * 1000)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (
                        version, name, description, checksum, applied_at, duration_ms, backup_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        migration.version,
                        migration.name,
                        migration.description,
                        migration.checksum,
                        utc_now(),
                        duration_ms,
                        backup["id"],
                    ),
                )
            applied.append(version)
            _record_run(run_id, applied_versions=json.dumps(applied), to_version=version)
        with connect() as conn:
            if "application_state" in {str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}:
                conn.execute(
                    "UPDATE application_state SET last_upgrade_at=?, last_upgrade_backup_id=?, updated_at=? WHERE id='current'",
                    (utc_now(), backup["id"], utc_now()),
                )
        _record_run(run_id, status="completed", completed_at=utc_now(), applied_versions=json.dumps(applied), to_version=LATEST_SCHEMA_VERSION)
        return {
            "status": "completed",
            "run_id": run_id,
            "applied_versions": applied,
            "backup": backup,
            "schema": migration_status(),
        }
    except Exception as exc:
        error = str(exc)
        _restore_snapshot_without_bootstrap(backup["id"])
        init_migration_schema()
        with connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO migration_runs (
                    id, status, from_version, to_version, planned_versions,
                    applied_versions, backup_id, error_message, started_at, completed_at
                ) VALUES (?, 'rolled_back', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    plan["current_version"],
                    plan["latest_version"],
                    json.dumps(pending_versions),
                    json.dumps(applied),
                    backup["id"],
                    error,
                    started,
                    utc_now(),
                ),
            )
        raise ValueError(f"Migration failed and database snapshot was restored: {error}") from exc


def rollback_upgrade(backup_id: str, *, confirmation: str) -> dict[str, Any]:
    if confirmation != "ROLLBACK":
        raise ValueError("Rollback confirmation must be ROLLBACK")
    blockers = _upgrade_blockers()
    if blockers:
        raise ValueError(" ".join(blockers))
    backup = get_database_backup(backup_id, verify=True)
    if backup.get("kind") not in {"pre_upgrade", "pre_restore", "manual"}:
        raise ValueError("Only verified pre-upgrade, pre-restore, or manual backups can be used for schema rollback")
    result = restore_database_backup(backup_id, confirmation="RESTORE")
    init_migration_schema()
    return {"status": "rolled_back", "restore": result, "schema": migration_status()}


def auto_apply_migrations() -> dict[str, Any]:
    enabled = os.getenv("AI_NOVEL_AUTO_MIGRATE", "1").lower() not in {"0", "false", "no"}
    if not enabled:
        return {"status": "disabled", "schema": migration_status()}
    status = migration_status()
    if not status["pending"]:
        return {"status": "current", "schema": status}
    return apply_pending_migrations(automatic=True)
