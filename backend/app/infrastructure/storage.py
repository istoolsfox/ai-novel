import os
from pathlib import Path

from .database import connect, row_to_dict


def data_root() -> Path:
    return Path(os.environ.get("AI_NOVEL_DATA_DIR", "data")).resolve()


def ensure_project_dirs(project_id: str) -> Path:
    root = data_root() / "projects" / project_id
    for relative in (
        "manuscript",
        "memory/raw_sources",
        "memory/wiki",
        "memory/index",
        "exports",
        "backups",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)
    return root


def project_or_none(project_id: str) -> dict | None:
    with connect() as conn:
        return row_to_dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())


def require_project(project_id: str) -> dict:
    project = project_or_none(project_id)
    if not project:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Project not found")
    return project


def project_root(project_id: str) -> Path:
    project = require_project(project_id)
    return Path(project["project_root_path"]).resolve()


def safe_wiki_path(project_id: str, relative_path: str) -> Path:
    from fastapi import HTTPException

    cleaned = relative_path.replace("\\", "/").strip("/")
    if not cleaned or cleaned.startswith("../") or "/../" in cleaned or cleaned == "..":
        raise HTTPException(status_code=400, detail="Invalid wiki path")
    root = project_root(project_id) / "memory" / "wiki"
    target = (root / cleaned).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Wiki path escapes project") from exc
    return target
