#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATTERN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s;]+)")


def normalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def python_components(lock_path: Path) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for raw in lock_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = LOCK_PATTERN.match(line)
        if not match:
            continue
        name, version = match.groups()
        normalized = normalize_name(name)
        components.append({
            "type": "library",
            "name": name,
            "version": version,
            "bom-ref": f"pkg:pypi/{normalized}@{version}",
            "purl": f"pkg:pypi/{normalized}@{version}",
            "properties": [{"name": "ai-novel:ecosystem", "value": "python"}],
        })
    return components


def node_components(lock_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    packages = payload.get("packages", {}) if isinstance(payload, dict) else {}
    components: list[dict[str, Any]] = []
    for package_path, record in packages.items():
        if not package_path or not isinstance(record, dict):
            continue
        name = str(record.get("name") or package_path.rsplit("node_modules/", 1)[-1])
        version = str(record.get("version") or "")
        if not name or not version:
            continue
        encoded_name = name.replace("@", "%40").replace("/", "%2F")
        component: dict[str, Any] = {
            "type": "library",
            "name": name,
            "version": version,
            "bom-ref": f"pkg:npm/{encoded_name}@{version}",
            "purl": f"pkg:npm/{encoded_name}@{version}",
            "properties": [
                {"name": "ai-novel:ecosystem", "value": "node"},
                {"name": "ai-novel:development", "value": str(bool(record.get("dev"))).lower()},
            ],
        }
        integrity = str(record.get("integrity") or "")
        if integrity.startswith("sha512-"):
            component["hashes"] = [{"alg": "SHA-512", "content": integrity.removeprefix("sha512-")}]
        components.append(component)
    return components


def generate(python_lock: Path, node_lock: Path, output: Path, version: str) -> dict[str, Any]:
    components = python_components(python_lock) + node_components(node_lock)
    components.sort(key=lambda item: (str(item.get("purl", "")), str(item.get("name", ""))))
    serial_seed = "\n".join(str(item["purl"]) for item in components).encode("utf-8")
    serial = hashlib.sha256(serial_seed).hexdigest()
    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{serial[:8]}-{serial[8:12]}-{serial[12:16]}-{serial[16:20]}-{serial[20:32]}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "ai-novel-workbench",
                "version": version,
                "bom-ref": f"pkg:github/wlxb625/ai-novel@{version}",
                "purl": f"pkg:github/wlxb625/ai-novel@{version}",
            },
            "properties": [
                {"name": "ai-novel:python-lock-sha256", "value": file_hash(python_lock)},
                {"name": "ai-novel:node-lock-sha256", "value": file_hash(node_lock)},
            ],
        },
        "components": components,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": "generated",
        "output": str(output),
        "components": len(components),
        "python_components": sum(1 for item in components if "pkg:pypi/" in item["purl"]),
        "node_components": sum(1 for item in components if "pkg:npm/" in item["purl"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a deterministic CycloneDX SBOM")
    parser.add_argument("--python-lock", default=str(ROOT / "backend" / "requirements.lock"))
    parser.add_argument("--node-lock", default=str(ROOT / "frontend" / "package-lock.json"))
    parser.add_argument("--output", default=str(ROOT / "docs" / "sbom.cdx.json"))
    parser.add_argument("--version", default=(ROOT / "VERSION").read_text(encoding="utf-8").strip())
    args = parser.parse_args(argv)
    try:
        result = generate(
            Path(args.python_lock).expanduser().resolve(),
            Path(args.node_lock).expanduser().resolve(),
            Path(args.output).expanduser().resolve(),
            args.version,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
