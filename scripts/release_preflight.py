#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SEMVER_STABLE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
REQUIRED_FILES = (
    "VERSION",
    "CHANGELOG.md",
    "README.md",
    "SECURITY.md",
    "SUPPORT.md",
    "UPGRADING.md",
    "RELEASE_CHECKLIST.md",
    "backend/requirements.lock",
    "frontend/package-lock.json",
    "docs/openapi.json",
    "docs/sbom.cdx.json",
    "docs/disaster-recovery.md",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=300)


def check(name: str, operation: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        detail = operation()
        return {"id": name, "status": "pass", **detail}
    except Exception as exc:
        return {"id": name, "status": "fail", "error": str(exc)}


def check_version() -> dict[str, Any]:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not SEMVER_STABLE.fullmatch(version):
        raise ValueError(f"VERSION is not a stable semantic version: {version}")
    return {"version": version}


def check_changelog() -> dict[str, Any]:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## {version} " not in text and f"## {version}\n" not in text:
        raise ValueError(f"CHANGELOG.md does not contain a {version} section")
    return {"section": version}


def check_required_files() -> dict[str, Any]:
    missing = [item for item in REQUIRED_FILES if not (ROOT / item).is_file()]
    if missing:
        raise ValueError(f"Missing required stable release files: {', '.join(missing)}")
    return {"files": len(REQUIRED_FILES)}


def check_python_lock() -> dict[str, Any]:
    path = ROOT / "backend" / "requirements.lock"
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    unpinned = [line for line in lines if not line.startswith("-") and "==" not in line]
    if not lines or unpinned:
        raise ValueError(f"Python lock is empty or contains unpinned entries: {unpinned[:5]}")
    return {"packages": len(lines), "sha256": sha256(path)}


def check_node_lock() -> dict[str, Any]:
    path = ROOT / "frontend" / "package-lock.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if int(payload.get("lockfileVersion") or 0) < 3:
        raise ValueError("frontend/package-lock.json must use lockfileVersion 3 or newer")
    packages = payload.get("packages") if isinstance(payload.get("packages"), dict) else {}
    return {"packages": max(0, len(packages) - 1), "sha256": sha256(path)}


def check_secret_scan(output_dir: Path) -> dict[str, Any]:
    output = output_dir / "secret-scan.json"
    result = run([sys.executable, "scripts/scan_secrets.py", "--output", str(output)])
    if result.returncode:
        raise ValueError(result.stdout + result.stderr)
    payload = json.loads(output.read_text(encoding="utf-8"))
    return {"scanned_files": payload.get("scanned_files", 0), "findings": len(payload.get("findings", []))}


def check_contracts(output_dir: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ai-novel-contracts-") as temp_name:
        temp = Path(temp_name)
        generated_openapi = temp / "openapi.json"
        generated_sbom = temp / "sbom.cdx.json"
        openapi = run([sys.executable, "scripts/generate_openapi.py", "--output", str(generated_openapi)])
        if openapi.returncode:
            raise ValueError(openapi.stdout + openapi.stderr)
        sbom = run([
            sys.executable,
            "scripts/generate_sbom.py",
            "--python-lock", "backend/requirements.lock",
            "--node-lock", "frontend/package-lock.json",
            "--output", str(generated_sbom),
            "--version", (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        ])
        if sbom.returncode:
            raise ValueError(sbom.stdout + sbom.stderr)
        committed_openapi = ROOT / "docs" / "openapi.json"
        committed_sbom = ROOT / "docs" / "sbom.cdx.json"
        if generated_openapi.read_bytes() != committed_openapi.read_bytes():
            raise ValueError("Committed docs/openapi.json does not match the generated application contract")
        if generated_sbom.read_bytes() != committed_sbom.read_bytes():
            raise ValueError("Committed docs/sbom.cdx.json does not match dependency locks")
        shutil.copy2(generated_openapi, output_dir / "openapi.json")
        shutil.copy2(generated_sbom, output_dir / "SBOM.cdx.json")
        return {
            "openapi_sha256": sha256(generated_openapi),
            "sbom_sha256": sha256(generated_sbom),
        }


def check_release_artifacts(output_dir: Path) -> dict[str, Any]:
    built = run([sys.executable, "scripts/build_release.py", "--output", str(output_dir)])
    if built.returncode:
        raise ValueError(built.stdout + built.stderr)
    verified = run([sys.executable, "scripts/build_release.py", "--output", str(output_dir), "--verify"])
    if verified.returncode:
        raise ValueError(verified.stdout + verified.stderr)
    result = json.loads((output_dir / "release-result.json").read_text(encoding="utf-8"))
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    if manifest.get("release_channel") != "stable":
        raise ValueError("Release manifest is not marked stable")
    return {
        "archive": Path(result["archive"]).name,
        "archive_sha256": result["archive_sha256"],
        "file_count": result["file_count"],
    }


def preflight(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    checks = [
        check("version", check_version),
        check("changelog", check_changelog),
        check("required-files", check_required_files),
        check("python-lock", check_python_lock),
        check("node-lock", check_node_lock),
        check("secret-scan", lambda: check_secret_scan(output_dir)),
        check("contracts", lambda: check_contracts(output_dir)),
        check("release-artifacts", lambda: check_release_artifacts(output_dir)),
    ]
    failed = [item for item in checks if item["status"] != "pass"]
    result = {
        "status": "pass" if not failed else "fail",
        "version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "checks": checks,
        "failed_checks": [item["id"] for item in failed],
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the complete AI Novel stable release preflight")
    parser.add_argument("--output", default=str(ROOT / "release-dist" / "release-preflight.json"))
    args = parser.parse_args(argv)
    output = Path(args.output).expanduser().resolve()
    result = preflight(output.parent)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
