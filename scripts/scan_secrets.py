#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "node_modules", "dist", "release-dist", "__pycache__", ".pytest_cache"}
TEXT_SUFFIXES = {
    ".bat", ".cmd", ".conf", ".css", ".env", ".example", ".html", ".ini", ".js", ".json", ".jsx",
    ".md", ".mjs", ".ps1", ".py", ".sh", ".toml", ".ts", ".tsx", ".txt", ".yaml", ".yml",
}
FORBIDDEN_TRACKED_NAMES = {".env", ".ai-novel-master.key", "id_rsa", "id_ed25519"}
FORBIDDEN_SUFFIXES = {".db", ".key", ".pem", ".p12", ".pfx", ".sqlite", ".sqlite3"}
PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
    "aws-access-key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "openai-project-key": re.compile(r"\bsk-proj-[A-Za-z0-9_-]{32,}\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}
ALLOW_PATH_PREFIXES = (
    "backend/tests/",
    "frontend/src/components/",
    "docs/",
)
ALLOW_LITERAL_MARKERS = (
    "example",
    "test",
    "fake",
    "placeholder",
    "[REDACTED]",
    "<token>",
    "<随机长令牌>",
)


def relative_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        yield relative, path


def likely_example(relative: str, line: str) -> bool:
    lowered = line.lower()
    return relative.startswith(ALLOW_PATH_PREFIXES) and any(marker.lower() in lowered for marker in ALLOW_LITERAL_MARKERS)


def scan(root: Path) -> dict:
    findings: list[dict] = []
    scanned = 0
    for relative_path, path in relative_files(root):
        relative = relative_path.as_posix()
        scanned += 1
        if path.name in FORBIDDEN_TRACKED_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append({"type": "forbidden-file", "path": relative, "line": 0, "match": path.name})
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"Dockerfile", "VERSION", "CHANGELOG.md", "README.md"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for kind, pattern in PATTERNS.items():
                match = pattern.search(line)
                if not match or likely_example(relative, line):
                    continue
                findings.append({
                    "type": kind,
                    "path": relative,
                    "line": line_number,
                    "match": f"{match.group(0)[:6]}…{match.group(0)[-4:]}",
                })
    return {"status": "pass" if not findings else "fail", "scanned_files": scanned, "findings": findings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan source files for high-confidence credentials and runtime data")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)
    result = scan(Path(args.root).expanduser().resolve())
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
