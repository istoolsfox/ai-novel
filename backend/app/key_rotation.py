import json
import os
import stat
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from .backup_service import create_database_backup
from .database import connect, new_id, row_to_dict, rows_to_dicts, utc_now
from .migration_service import _restore_snapshot_without_bootstrap, _upgrade_blockers
from .secret_store import key_fingerprint, master_key_path, security_status
from .security_schema import init_security_schema


def init_key_rotation_schema() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS master_key_rotations (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                previous_fingerprint TEXT NOT NULL,
                new_fingerprint TEXT DEFAULT '',
                credential_count INTEGER NOT NULL DEFAULT 0,
                backup_id TEXT DEFAULT '',
                key_backup_path TEXT DEFAULT '',
                error_message TEXT DEFAULT '',
                started_at TEXT NOT NULL,
                completed_at TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_master_key_rotations_started
            ON master_key_rotations(started_at);
            """
        )


def key_rotation_history(limit: int = 100) -> list[dict[str, Any]]:
    init_key_rotation_schema()
    safe_limit = max(1, min(int(limit), 500))
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM master_key_rotations ORDER BY started_at DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        )


def _load_current_file_key() -> tuple[Path, bytes]:
    if os.getenv("AI_NOVEL_MASTER_KEY", "").strip():
        raise ValueError(
            "Master key rotation is blocked while AI_NOVEL_MASTER_KEY is supplied by the environment. "
            "Rotate the external secret and restart through the deployment secret manager."
        )
    path = master_key_path()
    if not path.is_file():
        from .secret_store import load_master_key

        load_master_key()
    return path, path.read_bytes().strip()


def _write_owner_only(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(value + b"\n")
    try:
        os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    os.replace(temporary, path)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def _validate_key(value: str | bytes | None) -> bytes:
    raw = Fernet.generate_key() if value in (None, "") else (value.encode("utf-8") if isinstance(value, str) else value)
    try:
        Fernet(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError("New master key must be a valid Fernet key") from exc
    return raw


def rotate_master_key(*, confirmation: str, new_master_key: str = "") -> dict[str, Any]:
    if confirmation != "ROTATE":
        raise ValueError("Master key rotation confirmation must be ROTATE")
    blockers = _upgrade_blockers()
    if blockers:
        raise ValueError(" ".join(blockers))

    init_security_schema()
    init_key_rotation_schema()
    key_path, old_key = _load_current_file_key()
    new_key = _validate_key(new_master_key)
    old_fernet = Fernet(old_key)
    new_fernet = Fernet(new_key)
    previous_fingerprint = key_fingerprint(old_key)
    next_fingerprint = key_fingerprint(new_key)
    if previous_fingerprint == next_fingerprint:
        raise ValueError("New master key must differ from the current key")

    with connect() as conn:
        credentials = rows_to_dicts(
            conn.execute(
                "SELECT id, encrypted_secret, key_fingerprint FROM encrypted_credentials ORDER BY id"
            ).fetchall()
        )

    plaintext: dict[str, bytes] = {}
    for credential in credentials:
        if str(credential.get("key_fingerprint") or "") != previous_fingerprint:
            raise ValueError(f"Credential {credential['id']} fingerprint does not match the active master key")
        try:
            plaintext[str(credential["id"])] = old_fernet.decrypt(str(credential["encrypted_secret"]).encode("ascii"))
        except InvalidToken as exc:
            raise ValueError(f"Credential {credential['id']} cannot be decrypted before rotation") from exc

    backup = create_database_backup(
        note=f"Automatic pre-key-rotation backup from {previous_fingerprint} to {next_fingerprint}",
        backup_kind="pre_key_rotation",
    )
    rotation_id = new_id()
    started = utc_now()
    key_backup_path = key_path.with_name(f"{key_path.name}.{rotation_id}.bak")
    _write_owner_only(key_backup_path, old_key)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO master_key_rotations (
                id, status, previous_fingerprint, new_fingerprint,
                credential_count, backup_id, key_backup_path, started_at
            ) VALUES (?, 'running', ?, ?, ?, ?, ?, ?)
            """,
            (
                rotation_id,
                previous_fingerprint,
                next_fingerprint,
                len(credentials),
                backup["id"],
                str(key_backup_path),
                started,
            ),
        )

    try:
        with connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            for credential_id, secret in plaintext.items():
                encrypted = new_fernet.encrypt(secret).decode("ascii")
                conn.execute(
                    """
                    UPDATE encrypted_credentials
                    SET encrypted_secret=?, key_fingerprint=?, rotated_at=?, updated_at=?
                    WHERE id=?
                    """,
                    (encrypted, next_fingerprint, utc_now(), utc_now(), credential_id),
                )
        _write_owner_only(key_path, new_key)

        with connect() as conn:
            verification = rows_to_dicts(
                conn.execute("SELECT id, encrypted_secret, key_fingerprint FROM encrypted_credentials ORDER BY id").fetchall()
            )
        for credential in verification:
            if credential.get("key_fingerprint") != next_fingerprint:
                raise ValueError(f"Credential {credential['id']} was not assigned the new fingerprint")
            try:
                new_fernet.decrypt(str(credential["encrypted_secret"]).encode("ascii"))
            except InvalidToken as exc:
                raise ValueError(f"Credential {credential['id']} failed post-rotation verification") from exc

        with connect() as conn:
            conn.execute(
                """
                UPDATE master_key_rotations
                SET status='completed', completed_at=?
                WHERE id=?
                """,
                (utc_now(), rotation_id),
            )
        return {
            "status": "completed",
            "rotation_id": rotation_id,
            "previous_fingerprint": previous_fingerprint,
            "new_fingerprint": next_fingerprint,
            "credential_count": len(credentials),
            "backup": backup,
            "key_backup_path": str(key_backup_path),
            "security": security_status(),
        }
    except Exception as exc:
        error = str(exc)
        _restore_snapshot_without_bootstrap(backup["id"])
        _write_owner_only(key_path, old_key)
        init_key_rotation_schema()
        with connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO master_key_rotations (
                    id, status, previous_fingerprint, new_fingerprint,
                    credential_count, backup_id, key_backup_path,
                    error_message, started_at, completed_at
                ) VALUES (?, 'rolled_back', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rotation_id,
                    previous_fingerprint,
                    next_fingerprint,
                    len(credentials),
                    backup["id"],
                    str(key_backup_path),
                    error,
                    started,
                    utc_now(),
                ),
            )
        raise ValueError(f"Master key rotation failed and was rolled back: {error}") from exc


def restore_previous_master_key(rotation_id: str, *, confirmation: str) -> dict[str, Any]:
    if confirmation != "RESTORE_KEY":
        raise ValueError("Key restore confirmation must be RESTORE_KEY")
    blockers = _upgrade_blockers()
    if blockers:
        raise ValueError(" ".join(blockers))
    init_key_rotation_schema()
    with connect() as conn:
        rotation = row_to_dict(
            conn.execute("SELECT * FROM master_key_rotations WHERE id=?", (rotation_id,)).fetchone()
        )
    if not rotation:
        raise ValueError("Key rotation record not found")
    backup_id = str(rotation.get("backup_id") or "")
    key_backup = Path(str(rotation.get("key_backup_path") or "")).resolve()
    if not backup_id or not key_backup.is_file():
        raise ValueError("Rotation rollback material is incomplete")
    key_path, _current_key = _load_current_file_key()
    current_safety = create_database_backup(
        note=f"Safety backup before restoring master key rotation {rotation_id}",
        backup_kind="pre_key_restore",
    )
    _restore_snapshot_without_bootstrap(backup_id)
    _write_owner_only(key_path, key_backup.read_bytes().strip())
    init_key_rotation_schema()
    return {
        "status": "restored",
        "rotation_id": rotation_id,
        "database_backup_id": backup_id,
        "safety_backup": current_safety,
        "security": security_status(),
    }
