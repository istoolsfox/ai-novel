#!/usr/bin/env python3
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generate(output: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="ai-novel-openapi-") as temporary:
        temp = Path(temporary)
        os.environ["AI_NOVEL_DATABASE_URL"] = f"sqlite:///{temp / 'openapi.db'}"
        os.environ["AI_NOVEL_DATA_DIR"] = str(temp / "projects")
        os.environ["AI_NOVEL_BACKUP_DIR"] = str(temp / "backups")
        os.environ["AI_NOVEL_MASTER_KEY_FILE"] = str(temp / "master.key")
        os.environ["AI_NOVEL_AUTO_MIGRATE"] = "1"
        os.environ["AI_NOVEL_RUNTIME_SYNC"] = "1"
        os.environ.pop("AI_NOVEL_ADMIN_TOKEN", None)
        os.environ.pop("AI_NOVEL_MASTER_KEY", None)

        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from backend.app.main import app, init_app

        init_app()
        document = app.openapi()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "status": "generated",
        "output": str(output),
        "title": document.get("info", {}).get("title", ""),
        "version": document.get("info", {}).get("version", ""),
        "paths": len(document.get("paths", {})),
        "schemas": len(document.get("components", {}).get("schemas", {})),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the committed AI Novel OpenAPI contract")
    parser.add_argument("--output", default=str(ROOT / "docs" / "openapi.json"))
    args = parser.parse_args(argv)
    try:
        result = generate(Path(args.output).expanduser().resolve())
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
