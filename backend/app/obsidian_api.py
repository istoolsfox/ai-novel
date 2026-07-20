from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .obsidian_exporter import (
    export_obsidian_vault,
    get_obsidian_export,
    remove_obsidian_export,
    require_obsidian_export,
)
from .storage import project_root, require_project

router = APIRouter(prefix="/api/projects/{project_id}/obsidian", tags=["obsidian"])


class ObsidianExportIn(BaseModel):
    include_drafts: bool = True
    force_rebuild: bool = False
    create_archive: bool = True


def _call(operation, *args, **kwargs):
    try:
        return operation(*args, **kwargs)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message) from exc


@router.post("/export")
def create_obsidian_export(project_id: str, payload: ObsidianExportIn) -> dict[str, Any]:
    require_project(project_id)
    return _call(
        export_obsidian_vault,
        project_id,
        include_drafts=payload.include_drafts,
        force_rebuild=payload.force_rebuild,
        create_archive=payload.create_archive,
    )


@router.get("/status")
def obsidian_export_status(project_id: str) -> dict[str, Any]:
    require_project(project_id)
    export = get_obsidian_export(project_id)
    return export or {
        "project_id": project_id,
        "status": "not_exported",
        "files": [],
        "file_count": 0,
    }


@router.get("/manifest")
def obsidian_export_manifest(project_id: str) -> dict[str, Any]:
    require_project(project_id)
    export = _call(require_obsidian_export, project_id)
    return export.get("manifest") if isinstance(export.get("manifest"), dict) else {}


@router.get("/download")
def download_obsidian_export(project_id: str):
    require_project(project_id)
    export = _call(require_obsidian_export, project_id)
    raw_path = str(export.get("archive_path") or "")
    if not raw_path:
        raise HTTPException(status_code=404, detail="Obsidian archive was not created")
    archive = Path(raw_path).resolve()
    try:
        archive.relative_to(project_root(project_id).resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Obsidian archive path") from exc
    if not archive.is_file():
        raise HTTPException(status_code=404, detail="Obsidian archive not found")
    return FileResponse(
        archive,
        media_type="application/zip",
        filename=archive.name,
    )


@router.delete("/export")
def delete_obsidian_export(project_id: str) -> dict[str, bool]:
    require_project(project_id)
    return _call(remove_obsidian_export, project_id)
