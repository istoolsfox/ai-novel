import os
from pathlib import Path


def version_file() -> Path:
    return Path(__file__).resolve().parents[2] / "VERSION"


def application_version() -> str:
    override = os.getenv("AI_NOVEL_VERSION", "").strip()
    if override:
        return override
    try:
        return version_file().read_text(encoding="utf-8").strip() or "0.0.0-dev"
    except OSError:
        return "0.0.0-dev"


def release_channel(version: str | None = None) -> str:
    value = (version or application_version()).lower()
    if "-rc" in value:
        return "release-candidate"
    if any(marker in value for marker in ("-alpha", "-beta", "-dev")):
        return "development"
    return "stable"


def build_metadata() -> dict[str, str]:
    version = application_version()
    return {
        "version": version,
        "release_channel": release_channel(version),
        "commit": os.getenv("AI_NOVEL_BUILD_COMMIT", "").strip(),
        "built_at": os.getenv("AI_NOVEL_BUILD_DATE", "").strip(),
        "image_revision": os.getenv("AI_NOVEL_IMAGE_REVISION", "").strip(),
    }
