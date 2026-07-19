import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from .database import connect, database_path, new_id, row_to_dict, rows_to_dicts, utc_now
from .security_schema import init_security_schema

SECRET_KEYS = {
    "api_key",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "password",
    "client_secret",
}


def master_key_path() -> Path:
    configured = os.getenv("AI_NOVEL_MASTER_KEY_FILE", "").strip()
    return Path(configured).expanduser().resolve() if configured else (database_path().parent / ".ai-novel-master.key").resolve()


def _normalize_key(value: str | bytes) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    try:
        Fernet(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError("AI_NOVEL_MASTER_KEY must be a valid Fernet key") from exc
    return raw


def load_master_key(*, create: bool = True) -> bytes:
    env_key = os.getenv("AI_NOVEL_MASTER_KEY", "").strip()
    if env_key:
        return _normalize_key(env_key)

    path = master_key_path()
    if path.is_file():
        return _normalize_key(path.read_bytes().strip())
    if not create:
        raise ValueError("Master key does not exist")

    path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(key + b"\n")
    try:
        os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    os.replace(temporary, path)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return key


def key_fingerprint(key: bytes | None = None) -> str:
    return hashlib.sha256(key or load_master_key()).hexdigest()[:16]


def encrypt_secret(value: str) -> tuple[str, str]:
    secret = value.strip()
    if not secret:
        raise ValueError("Credential secret cannot be empty")
    key = load_master_key()
    return Fernet(key).encrypt(secret.encode("utf-8")).decode("ascii"), key_fingerprint(key)


def decrypt_secret(ciphertext: str, fingerprint: str = "") -> str:
    key = load_master_key(create=False)
    if fingerprint and fingerprint != key_fingerprint(key):
        raise ValueError("Credential was encrypted with a different master key")
    try:
        return Fernet(key).decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Credential cannot be decrypted with the current master key") from exc


def secret_hint(value: str) -> str:
    text = value.strip()
    if len(text) <= 6:
        return "•" * len(text)
    return f"{text[:3]}••••{text[-3:]}"


def redact_secrets(value: Any) -> Any:
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            result[key] = "[REDACTED]" if normalized in SECRET_KEYS or normalized.endswith("_secret") else redact_secrets(item)
        return result
    return value


def _decode_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def public_credential(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id", ""),
        "project_id": row.get("project_id", ""),
        "name": row.get("name", ""),
        "provider": row.get("provider", ""),
        "secret_hint": row.get("secret_hint", ""),
        "metadata": redact_secrets(_decode_metadata(row.get("metadata"))),
        "status": row.get("status", "active"),
        "key_fingerprint": row.get("key_fingerprint", ""),
        "created_at": row.get("created_at", ""),
        "updated_at": row.get("updated_at", ""),
        "last_used_at": row.get("last_used_at", ""),
        "rotated_at": row.get("rotated_at", ""),
    }


def append_security_event(event_type: str, message: str, *, project_id: str = "", credential_id: str = "", payload: dict[str, Any] | None = None) -> None:
    init_security_schema()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO security_events (id, project_id, credential_id, event_type, message, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (new_id(), project_id, credential_id, event_type, message, json.dumps(redact_secrets(payload or {}), ensure_ascii=False), utc_now()),
        )


def create_credential(project_id: str, *, name: str, provider: str, secret: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    init_security_schema()
    encrypted, fingerprint = encrypt_secret(secret)
    now = utc_now()
    credential_id = new_id()
    try:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO encrypted_credentials (
                    id, project_id, name, provider, encrypted_secret, key_fingerprint,
                    secret_hint, metadata, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (
                    credential_id,
                    project_id,
                    name.strip(),
                    provider.strip(),
                    encrypted,
                    fingerprint,
                    secret_hint(secret),
                    json.dumps(redact_secrets(metadata or {}), ensure_ascii=False),
                    now,
                    now,
                ),
            )
            row = row_to_dict(conn.execute("SELECT * FROM encrypted_credentials WHERE id=?", (credential_id,)).fetchone()) or {}
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise ValueError("A credential with this name already exists in the project") from exc
        raise
    append_security_event("credential.created", "加密凭证已创建。", project_id=project_id, credential_id=credential_id, payload={"name": name, "provider": provider})
    return public_credential(row)


def list_credentials(project_id: str) -> list[dict[str, Any]]:
    init_security_schema()
    with connect() as conn:
        rows = rows_to_dicts(
            conn.execute(
                "SELECT * FROM encrypted_credentials WHERE project_id=? ORDER BY updated_at DESC",
                (project_id,),
            ).fetchall()
        )
    return [public_credential(row) for row in rows]


def get_credential(project_id: str, credential_id: str, *, include_secret: bool = False) -> dict[str, Any]:
    init_security_schema()
    with connect() as conn:
        row = row_to_dict(
            conn.execute(
                "SELECT * FROM encrypted_credentials WHERE id=? AND project_id=?",
                (credential_id, project_id),
            ).fetchone()
        )
    if not row:
        raise ValueError("Credential not found")
    result = public_credential(row)
    if include_secret:
        result["secret"] = decrypt_secret(str(row.get("encrypted_secret") or ""), str(row.get("key_fingerprint") or ""))
        with connect() as conn:
            conn.execute("UPDATE encrypted_credentials SET last_used_at=? WHERE id=?", (utc_now(), credential_id))
    return result


def update_credential(project_id: str, credential_id: str, *, name: str | None = None, provider: str | None = None, secret: str | None = None, metadata: dict[str, Any] | None = None, status: str | None = None) -> dict[str, Any]:
    current = get_credential(project_id, credential_id)
    now = utc_now()
    fields = {
        "name": name.strip() if isinstance(name, str) and name.strip() else current["name"],
        "provider": provider.strip() if isinstance(provider, str) else current["provider"],
        "metadata": json.dumps(redact_secrets(metadata if metadata is not None else current["metadata"]), ensure_ascii=False),
        "status": status if status in {"active", "disabled"} else current["status"],
    }
    encrypted_secret = None
    fingerprint = None
    hint = None
    rotated_at = current.get("rotated_at", "")
    if secret is not None:
        encrypted_secret, fingerprint = encrypt_secret(secret)
        hint = secret_hint(secret)
        rotated_at = now
    with connect() as conn:
        if encrypted_secret is None:
            conn.execute(
                """
                UPDATE encrypted_credentials
                SET name=?, provider=?, metadata=?, status=?, updated_at=?
                WHERE id=? AND project_id=?
                """,
                (fields["name"], fields["provider"], fields["metadata"], fields["status"], now, credential_id, project_id),
            )
        else:
            conn.execute(
                """
                UPDATE encrypted_credentials
                SET name=?, provider=?, encrypted_secret=?, key_fingerprint=?, secret_hint=?,
                    metadata=?, status=?, rotated_at=?, updated_at=?
                WHERE id=? AND project_id=?
                """,
                (
                    fields["name"], fields["provider"], encrypted_secret, fingerprint, hint,
                    fields["metadata"], fields["status"], rotated_at, now, credential_id, project_id,
                ),
            )
        row = row_to_dict(conn.execute("SELECT * FROM encrypted_credentials WHERE id=?", (credential_id,)).fetchone()) or {}
    append_security_event(
        "credential.rotated" if secret is not None else "credential.updated",
        "加密凭证已轮换。" if secret is not None else "加密凭证已更新。",
        project_id=project_id,
        credential_id=credential_id,
        payload={"name": fields["name"], "provider": fields["provider"]},
    )
    return public_credential(row)


def delete_credential(project_id: str, credential_id: str) -> dict[str, Any]:
    credential = get_credential(project_id, credential_id)
    with connect() as conn:
        conn.execute("DELETE FROM encrypted_credentials WHERE id=? AND project_id=?", (credential_id, project_id))
    append_security_event("credential.deleted", "加密凭证已删除。", project_id=project_id, credential_id=credential_id, payload={"name": credential["name"]})
    return {"deleted": True, "credential": credential}


def security_events(project_id: str = "", limit: int = 100) -> list[dict[str, Any]]:
    init_security_schema()
    safe_limit = max(1, min(int(limit), 500))
    with connect() as conn:
        if project_id:
            rows = rows_to_dicts(
                conn.execute(
                    "SELECT * FROM security_events WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
                    (project_id, safe_limit),
                ).fetchall()
            )
        else:
            rows = rows_to_dicts(conn.execute("SELECT * FROM security_events ORDER BY created_at DESC LIMIT ?", (safe_limit,)).fetchall())
    for row in rows:
        row["payload"] = redact_secrets(_decode_metadata(row.get("payload")))
    return rows


def security_status() -> dict[str, Any]:
    init_security_schema()
    path = master_key_path()
    source = "environment" if os.getenv("AI_NOVEL_MASTER_KEY", "").strip() else "file"
    key = load_master_key()
    permissions = None
    if source == "file" and path.exists():
        try:
            permissions = oct(stat.S_IMODE(path.stat().st_mode))
        except OSError:
            permissions = None
    with connect() as conn:
        credential_count = int(conn.execute("SELECT COUNT(*) FROM encrypted_credentials").fetchone()[0])
        unreadable = 0
        for row in conn.execute("SELECT encrypted_secret, key_fingerprint FROM encrypted_credentials").fetchall():
            try:
                decrypt_secret(str(row[0]), str(row[1]))
            except ValueError:
                unreadable += 1
    return {
        "status": "ok" if unreadable == 0 else "degraded",
        "master_key_source": source,
        "master_key_path": str(path) if source == "file" else "",
        "master_key_fingerprint": key_fingerprint(key),
        "master_key_permissions": permissions,
        "credential_count": credential_count,
        "unreadable_credentials": unreadable,
        "admin_token_required": bool(os.getenv("AI_NOVEL_ADMIN_TOKEN", "").strip()),
    }


def migrate_plaintext_model_configs() -> dict[str, int]:
    init_security_schema()
    migrated = 0
    skipped = 0
    try:
        with connect() as conn:
            rows = rows_to_dicts(conn.execute("SELECT * FROM model_configs ORDER BY created_at").fetchall())
    except Exception:
        return {"migrated": 0, "skipped": 0}
    for row in rows:
        payload = _decode_metadata(row.get("payload"))
        api_key = str(payload.get("api_key") or "").strip()
        if not api_key:
            skipped += 1
            continue
        name = f"{row.get('title') or '模型'} credential"
        try:
            credential = create_credential(
                str(row.get("project_id") or ""),
                name=name,
                provider=str(payload.get("provider") or row.get("category") or ""),
                secret=api_key,
                metadata={"migrated_from_model_config_id": row.get("id")},
            )
        except ValueError:
            existing = next((item for item in list_credentials(str(row.get("project_id") or "")) if item.get("name") == name), None)
            if not existing:
                skipped += 1
                continue
            credential = existing
        payload["credential_id"] = credential["id"]
        payload["api_key"] = ""
        with connect() as conn:
            conn.execute(
                "UPDATE model_configs SET payload=?, updated_at=? WHERE id=?",
                (json.dumps(payload, ensure_ascii=False), utc_now(), row["id"]),
            )
        migrated += 1
    if migrated:
        append_security_event("credential.legacy_migration", "普通模型配置中的明文 API Key 已迁移到加密凭证库。", payload={"migrated": migrated})
    return {"migrated": migrated, "skipped": skipped}
