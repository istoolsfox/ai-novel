#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    ".git",
    ".github-cache",
    ".pytest_cache",
    ".runtime",
    ".venv",
    "__pycache__",
    "backups",
    "data",
    "dist",
    "node_modules",
    "projects",
    "release-dist",
}
EXCLUDED_SUFFIXES = {".db", ".key", ".pyc", ".pyo", ".sqlite", ".sqlite3"}
EXCLUDED_NAMES = {".env", ".DS_Store"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def git_commit() -> str:
    configured = os.getenv("GITHUB_SHA", "").strip() or os.getenv("AI_NOVEL_BUILD_COMMIT", "").strip()
    if configured:
        return configured
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def release_timestamp() -> tuple[int, str]:
    epoch_text = os.getenv("SOURCE_DATE_EPOCH", "").strip()
    epoch = int(epoch_text) if epoch_text else int(time.time())
    value = datetime.fromtimestamp(epoch, timezone.utc).replace(microsecond=0).isoformat()
    return epoch, value


def included_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.name in EXCLUDED_NAMES or path.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        files.append(relative)
    return sorted(files, key=lambda item: item.as_posix())


def zip_timestamp(epoch: int) -> tuple[int, int, int, int, int, int]:
    # ZIP cannot encode dates before 1980.
    stamp = datetime.fromtimestamp(max(epoch, 315532800), timezone.utc)
    return stamp.year, stamp.month, stamp.day, stamp.hour, stamp.minute, stamp.second


def build(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    release_version = version()
    epoch, created_at = release_timestamp()
    root_name = f"ai-novel-workbench-{release_version}"
    archive_path = output_dir / f"{root_name}-source.zip"
    manifest_path = output_dir / f"{root_name}-manifest.json"
    checksums_path = output_dir / "SHA256SUMS"
    files = included_files()

    manifest = {
        "name": "AI Novel Workbench",
        "version": release_version,
        "release_channel": "release-candidate" if "-rc" in release_version else "stable",
        "schema_version": 4,
        "commit": git_commit(),
        "created_at": created_at,
        "python": "3.12",
        "node": "22",
        "files": [
            {
                "path": relative.as_posix(),
                "size_bytes": (ROOT / relative).stat().st_size,
                "sha256": sha256(ROOT / relative),
            }
            for relative in files
        ],
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)

    timestamp = zip_timestamp(epoch)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in files:
            info = zipfile.ZipInfo(f"{root_name}/{relative.as_posix()}", date_time=timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, (ROOT / relative).read_bytes())
        info = zipfile.ZipInfo(f"{root_name}/release-manifest.json", date_time=timestamp)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, manifest_bytes)

    checksums = {
        archive_path.name: sha256(archive_path),
        manifest_path.name: sha256(manifest_path),
    }
    checksums_path.write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(checksums.items())),
        encoding="utf-8",
    )
    result = {
        "version": release_version,
        "archive": str(archive_path),
        "manifest": str(manifest_path),
        "checksums": str(checksums_path),
        "archive_sha256": checksums[archive_path.name],
        "file_count": len(files),
    }
    (output_dir / "release-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def verify(output_dir: Path) -> dict:
    result_path = output_dir / "release-result.json"
    if not result_path.is_file():
        raise ValueError("release-result.json not found")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    archive = Path(result["archive"])
    manifest = Path(result["manifest"])
    if not archive.is_file() or not manifest.is_file():
        raise ValueError("Release archive or manifest is missing")
    if sha256(archive) != result["archive_sha256"]:
        raise ValueError("Release archive checksum mismatch")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if payload.get("version") != version():
        raise ValueError("Release manifest version does not match VERSION")
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        root_name = f"ai-novel-workbench-{version()}"
        if f"{root_name}/release-manifest.json" not in names:
            raise ValueError("Embedded release manifest is missing")
        if f"{root_name}/VERSION" not in names:
            raise ValueError("VERSION is missing from release archive")
    return {"status": "verified", **result}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic AI Novel Workbench release artifacts")
    parser.add_argument("--output", default=str(ROOT / "release-dist"))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    try:
        output = Path(args.output).expanduser().resolve()
        result = verify(output) if args.verify else build(output)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
