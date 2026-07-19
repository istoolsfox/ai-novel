import hashlib
import json
import re
from typing import Any


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def parse_json(value: Any, default: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str) or not value.strip():
        return default
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return default
    return parsed


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def safe_name(value: Any, fallback: str = "未命名") -> str:
    text = re.sub(r"[\\/:*?\"<>|#^\[\]]+", "-", str(value or "").strip())
    text = re.sub(r"\s+", " ", text).strip(" .-")
    return (text or fallback)[:100]


def yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return "null"
    return json.dumps(str(value), ensure_ascii=False)


def frontmatter(values: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in values.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {yaml_scalar(item)}" for item in value)
        else:
            lines.append(f"{key}: {yaml_scalar(value)}")
    lines.extend(["---", ""])
    return "\n".join(lines)


def bullet_lines(values: list[Any], empty: str = "暂无") -> str:
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    return "\n".join(f"- {value}" for value in cleaned) if cleaned else f"- {empty}"


def wikilink(path: str, alias: str = "") -> str:
    normalized = path.replace("\\", "/").removesuffix(".md")
    return f"[[{normalized}|{alias}]]" if alias else f"[[{normalized}]]"


def latest_by(rows: list[dict[str, Any]], key_fields: tuple[str, ...], number_field: str) -> list[dict[str, Any]]:
    latest: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in rows:
        key = tuple(str(row.get(field) or "") for field in key_fields)
        current = latest.get(key)
        if current is None or int(row.get(number_field) or 0) >= int(current.get(number_field) or 0):
            latest[key] = row
    return list(latest.values())
