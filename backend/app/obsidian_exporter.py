import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from .database import connect, new_id, row_to_dict, rows_to_dicts, utc_now
from .obsidian_builder import build_obsidian_files
from .obsidian_collect import collect_obsidian_data
from .obsidian_render import json_text, safe_name, sha256_bytes
from .storage import project_root


def _export_row(project_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        export = row_to_dict(
            conn.execute("SELECT * FROM obsidian_exports WHERE project_id = ?", (project_id,)).fetchone()
        )
    if export and isinstance(export.get("manifest"), str):
        try:
            export["manifest"] = json.loads(export["manifest"])
        except json.JSONDecodeError:
            export["manifest"] = {}
    return export


def _tracked_files(export_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM obsidian_export_files WHERE export_id = ? ORDER BY relative_path",
                (export_id,),
            ).fetchall()
        )


def _managed_target(vault_path: Path, relative_path: str) -> Path:
    normalized = relative_path.replace("\\", "/").strip("/")
    if not normalized or normalized.startswith("../") or "/../" in normalized:
        raise ValueError("Invalid Obsidian export path")
    target = (vault_path / normalized).resolve()
    target.relative_to(vault_path.resolve())
    return target


def _content_hash(files: dict[str, dict[str, Any]]) -> str:
    digest_input = "\n".join(
        f"{path}\0{sha256_bytes(record['content'])}"
        for path, record in sorted(files.items())
    )
    return sha256_bytes(digest_input.encode("utf-8"))


def _stats(data: dict[str, Any]) -> dict[str, int]:
    return {
        "chapters": len(data["chapters"]),
        "characters": len(data["latest_character_states"]),
        "relationships": len(data["latest_relationship_states"]),
        "story_threads": len(data["story_threads"]),
        "story_nodes": len(data["story_nodes"]),
        "story_edges": len(data["story_edges"]),
        "foreshadowings": len(data["latest_foreshadowings"]),
        "narrative_debts": len(data["latest_debts"]),
        "items": len(data["latest_items"]),
        "impact_runs": len(data["impact_runs"]),
        "rolling_plan_items": len(data["rolling_plan_items"]),
    }


def _vault_path(project_id: str, data: dict[str, Any], existing: dict[str, Any] | None) -> Path:
    if existing and existing.get("vault_path"):
        path = Path(str(existing["vault_path"])).resolve()
    else:
        worldline = data["worldline"]
        stable_key = str(worldline.get("id") or project_id)[:8]
        name = safe_name(worldline.get("name") or "主世界线")
        path = (project_root(project_id) / "exports" / "obsidian" / f"{name}-{stable_key}").resolve()
    path.relative_to(project_root(project_id).resolve())
    return path


def _archive_path(project_id: str, vault_path: Path, existing: dict[str, Any] | None) -> Path:
    if existing and existing.get("archive_path"):
        path = Path(str(existing["archive_path"])).resolve()
    else:
        path = vault_path.parent / f"{vault_path.name}.zip"
    path.relative_to(project_root(project_id).resolve())
    return path


def _manifest(
    project_id: str,
    data: dict[str, Any],
    desired: dict[str, dict[str, Any]],
    content_hash: str,
    generated_at: str,
) -> dict[str, Any]:
    worldline = data["worldline"]
    return {
        "format": "ai-novel-obsidian-vault",
        "version": 1,
        "generated_at": generated_at,
        "project": {
            "id": project_id,
            "title": data["project"].get("title", ""),
        },
        "worldline": {
            "id": worldline.get("id", ""),
            "name": worldline.get("name", "主世界线"),
            "description": worldline.get("description", ""),
            "fork_chapter_number": worldline.get("fork_chapter_number", 0),
            "status": worldline.get("status", "active"),
            "is_primary": bool(worldline.get("is_primary")),
            "is_active": bool(worldline.get("is_active")),
        },
        "content_hash": content_hash,
        "stats": _stats(data),
        "files": [
            {
                "path": path,
                "sha256": sha256_bytes(record["content"]),
                "size_bytes": len(record["content"]),
                "source_type": record["source_type"],
                "source_key": record["source_key"],
            }
            for path, record in sorted(desired.items())
        ],
    }


def _write_archive(archive_path: Path, vault_path: Path, paths: list[str]) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive_path.with_suffix(".tmp.zip")
    if temporary.exists():
        temporary.unlink()
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative_path in sorted(paths):
            target = _managed_target(vault_path, relative_path)
            if target.is_file():
                archive.write(target, arcname=relative_path)
    temporary.replace(archive_path)


def export_obsidian_vault(
    project_id: str,
    *,
    include_drafts: bool = True,
    force_rebuild: bool = False,
    create_archive: bool = True,
) -> dict[str, Any]:
    data = collect_obsidian_data(project_id, include_drafts=include_drafts)
    existing = _export_row(project_id)
    desired = build_obsidian_files(data)
    content_hash = _content_hash(desired)
    previous_manifest = existing.get("manifest") if existing and isinstance(existing.get("manifest"), dict) else {}
    generated_at = (
        str(previous_manifest.get("generated_at") or utc_now())
        if existing and existing.get("content_hash") == content_hash
        else utc_now()
    )
    manifest = _manifest(project_id, data, desired, content_hash, generated_at)
    desired["manifest.json"] = {
        "content": json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8"),
        "source_type": "manifest",
        "source_key": "manifest",
    }

    vault_path = _vault_path(project_id, data, existing)
    archive_path = _archive_path(project_id, vault_path, existing)
    vault_path.mkdir(parents=True, exist_ok=True)

    previous_rows = _tracked_files(str(existing.get("id") or "")) if existing else []
    previous_by_path = {str(row.get("relative_path") or ""): row for row in previous_rows}
    created = updated = unchanged = deleted = 0

    for relative_path, record in desired.items():
        target = _managed_target(vault_path, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        current_hash = ""
        if target.is_file():
            current_hash = sha256_bytes(target.read_bytes())
        new_hash = sha256_bytes(record["content"])
        if force_rebuild or current_hash != new_hash:
            target.write_bytes(record["content"])
            if relative_path in previous_by_path or current_hash:
                updated += 1
            else:
                created += 1
        else:
            unchanged += 1

    stale_paths = sorted(set(previous_by_path) - set(desired))
    for relative_path in stale_paths:
        target = _managed_target(vault_path, relative_path)
        if target.is_file():
            target.unlink()
            deleted += 1
        parent = target.parent
        while parent != vault_path and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent

    if create_archive:
        _write_archive(archive_path, vault_path, list(desired))
    elif archive_path.exists():
        archive_path.unlink()

    now = utc_now()
    export_id = str(existing.get("id")) if existing else new_id()
    worldline_id = str(data["worldline"].get("id") or "")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO obsidian_exports (
                id, project_id, worldline_id, status, vault_path, archive_path,
                content_hash, manifest, file_count, created_count, updated_count,
                unchanged_count, deleted_count, created_at, updated_at
            ) VALUES (?, ?, ?, 'completed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id) DO UPDATE SET
                worldline_id=excluded.worldline_id,
                status='completed',
                vault_path=excluded.vault_path,
                archive_path=excluded.archive_path,
                content_hash=excluded.content_hash,
                manifest=excluded.manifest,
                file_count=excluded.file_count,
                created_count=excluded.created_count,
                updated_count=excluded.updated_count,
                unchanged_count=excluded.unchanged_count,
                deleted_count=excluded.deleted_count,
                updated_at=excluded.updated_at
            """,
            (
                export_id,
                project_id,
                worldline_id,
                str(vault_path),
                str(archive_path) if create_archive else "",
                content_hash,
                json_text(manifest),
                len(desired),
                created,
                updated,
                unchanged,
                deleted,
                str(existing.get("created_at") or now) if existing else now,
                now,
            ),
        )
        conn.execute("DELETE FROM obsidian_export_files WHERE export_id = ?", (export_id,))
        for relative_path, record in sorted(desired.items()):
            file_hash = sha256_bytes(record["content"])
            previous = previous_by_path.get(relative_path, {})
            conn.execute(
                """
                INSERT INTO obsidian_export_files (
                    id, export_id, project_id, relative_path, content_hash,
                    size_bytes, source_type, source_key, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(previous.get("id") or new_id()),
                    export_id,
                    project_id,
                    relative_path,
                    file_hash,
                    len(record["content"]),
                    record["source_type"],
                    record["source_key"],
                    str(previous.get("created_at") or now),
                    now,
                ),
            )
    result = get_obsidian_export(project_id)
    if not result:
        raise RuntimeError("Obsidian export record was not persisted")
    return result


def get_obsidian_export(project_id: str) -> dict[str, Any] | None:
    export = _export_row(project_id)
    if not export:
        return None
    export["files"] = _tracked_files(str(export["id"]))
    return export


def require_obsidian_export(project_id: str) -> dict[str, Any]:
    export = get_obsidian_export(project_id)
    if not export:
        raise ValueError("Obsidian export not found")
    return export


def remove_obsidian_export(project_id: str) -> dict[str, bool]:
    export = require_obsidian_export(project_id)
    root = project_root(project_id).resolve()
    vault_path = Path(str(export.get("vault_path") or "")).resolve()
    archive_path = Path(str(export.get("archive_path") or "")).resolve() if export.get("archive_path") else None
    vault_path.relative_to(root)
    shutil.rmtree(vault_path, ignore_errors=True)
    if archive_path:
        archive_path.relative_to(root)
        archive_path.unlink(missing_ok=True)
    with connect() as conn:
        conn.execute("DELETE FROM obsidian_export_files WHERE export_id = ?", (export["id"],))
        conn.execute("DELETE FROM obsidian_exports WHERE id = ?", (export["id"],))
    return {"ok": True}
