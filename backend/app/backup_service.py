import hashlib
import json
import os
import shutil
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .database import connect, database_path, init_db, new_id, utc_now
from .runtime_queue import runtime_diagnostics

_RESTORE_LOCK = threading.Lock()


def backup_directory() -> Path:
    configured = os.getenv("AI_NOVEL_BACKUP_DIR", "").strip()
    path = Path(configured).expanduser().resolve() if configured else (database_path().parent / "backups").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _integrity(path: Path) -> str:
    conn = sqlite3.connect(path)
    try:
        return str(conn.execute("PRAGMA integrity_check").fetchone()[0])
    finally:
        conn.close()


def _manifest_path(backup_path: Path) -> Path:
    return backup_path.with_suffix(".json")


def _safe_backup_path(backup_id: str) -> Path:
    if not backup_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in backup_id):
        raise ValueError("Invalid backup id")
    path = (backup_directory() / f"{backup_id}.sqlite").resolve()
    path.relative_to(backup_directory())
    return path


def _read_manifest(path: Path) -> dict[str, Any]:
    manifest_path = _manifest_path(path)
    if not manifest_path.is_file():
        raise ValueError("Backup manifest not found")
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError("Backup manifest is invalid") from exc


def create_database_backup(*, note: str = "", backup_kind: str = "manual") -> dict[str, Any]:
    source_path = database_path()
    if not source_path.is_file():
        init_db()
    backup_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{new_id()[:10]}"
    final_path = _safe_backup_path(backup_id)
    temporary_path = final_path.with_suffix(".tmp.sqlite")
    if temporary_path.exists():
        temporary_path.unlink()

    source = sqlite3.connect(source_path, timeout=30)
    target = sqlite3.connect(temporary_path, timeout=30)
    try:
        source.execute("PRAGMA busy_timeout=30000")
        source.backup(target)
        target.commit()
    finally:
        target.close()
        source.close()

    integrity = _integrity(temporary_path)
    if integrity.lower() != "ok":
        temporary_path.unlink(missing_ok=True)
        raise ValueError(f"Backup integrity check failed: {integrity}")
    temporary_path.replace(final_path)

    manifest = {
        "id": backup_id,
        "status": "completed",
        "kind": backup_kind,
        "note": note.strip(),
        "database_path": str(source_path),
        "file_path": str(final_path),
        "size_bytes": final_path.stat().st_size,
        "sha256": _sha256(final_path),
        "integrity": integrity,
        "created_at": utc_now(),
    }
    _manifest_path(final_path).write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def list_database_backups() -> list[dict[str, Any]]:
    backups: list[dict[str, Any]] = []
    for manifest_path in backup_directory().glob("*.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        file_path = Path(str(manifest.get("file_path") or ""))
        manifest["exists"] = file_path.is_file()
        backups.append(manifest)
    # Multiple backups can be created within the same second. Sort by the
    # full ISO timestamp and then the unique ID rather than filename alone.
    backups.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")), reverse=True)
    return backups


def get_database_backup(backup_id: str, *, verify: bool = False) -> dict[str, Any]:
    path = _safe_backup_path(backup_id)
    if not path.is_file():
        raise ValueError("Backup not found")
    manifest = _read_manifest(path)
    if verify:
        actual_hash = _sha256(path)
        if actual_hash != manifest.get("sha256"):
            raise ValueError("Backup checksum mismatch")
        integrity = _integrity(path)
        if integrity.lower() != "ok":
            raise ValueError(f"Backup integrity check failed: {integrity}")
        manifest = {**manifest, "verified": True, "integrity": integrity}
    return manifest


def _assert_restore_safe() -> None:
    diagnostics = runtime_diagnostics()
    active_jobs = sum(
        int(diagnostics.get("generation_jobs", {}).get(status, 0))
        for status in ("queued", "running", "paused")
    )
    active_tasks = sum(
        int(diagnostics.get("runtime_tasks", {}).get(status, 0))
        for status in ("queued", "running")
    )
    if diagnostics.get("active_workers"):
        raise ValueError("Stop all runtime workers before restoring a backup")
    if active_jobs or active_tasks:
        raise ValueError("Finish or cancel queued and running tasks before restoring a backup")


def restore_database_backup(backup_id: str, *, confirmation: str) -> dict[str, Any]:
    if confirmation != "RESTORE":
        raise ValueError("Restore confirmation must be RESTORE")
    with _RESTORE_LOCK:
        _assert_restore_safe()
        backup = get_database_backup(backup_id, verify=True)
        backup_path = _safe_backup_path(backup_id)
        safety = create_database_backup(note=f"Automatic safety backup before restoring {backup_id}", backup_kind="pre_restore")
        destination = database_path()
        temporary = destination.with_suffix(".restore.tmp.sqlite")
        temporary.unlink(missing_ok=True)

        source = sqlite3.connect(backup_path, timeout=30)
        target = sqlite3.connect(temporary, timeout=30)
        try:
            source.backup(target)
            target.commit()
        finally:
            target.close()
            source.close()
        integrity = _integrity(temporary)
        if integrity.lower() != "ok":
            temporary.unlink(missing_ok=True)
            raise ValueError(f"Restored database integrity check failed: {integrity}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        for suffix in ("-wal", "-shm"):
            Path(f"{destination}{suffix}").unlink(missing_ok=True)
        os.replace(temporary, destination)
        init_db()
        return {
            "status": "restored",
            "backup": backup,
            "safety_backup": safety,
            "restored_at": utc_now(),
            "database_path": str(destination),
        }


def remove_database_backup(backup_id: str) -> dict[str, Any]:
    path = _safe_backup_path(backup_id)
    manifest = _read_manifest(path) if path.exists() else {"id": backup_id}
    path.unlink(missing_ok=True)
    _manifest_path(path).unlink(missing_ok=True)
    return {"deleted": True, "backup": manifest}
