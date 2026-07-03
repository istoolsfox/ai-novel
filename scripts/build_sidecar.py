"""用 PyInstaller 把 FastAPI 后端打包为 sidecar 单文件可执行程序。

用法：
    python scripts/build_sidecar.py

产物：
    desktop/binaries/ai-novel-backend[.exe]
"""
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
DIST = ROOT / "desktop" / "binaries"
WORK = ROOT / "build" / "pyi"

HIDDEN_IMPORTS = [
    "uvicorn.logging",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "fastapi.templating",
    "fastapi.staticfiles",
    "fastapi.middleware.cors",
    "starlette.formparsers",
    "starlette.responses",
    "pydantic",
    "pydantic._internal._fields",
    "ebooklib",
    "ebooklib.epub",
    "reportlab",
    "reportlab.pdfgen",
    "reportlab.lib",
    "docx",
    "sqlite3",
    "multipart",
    # Backend package modules
    "backend",
    "backend.app",
    "backend.app.main",
    "backend.app.interfaces",
    "backend.app.interfaces.main",
    "backend.app.interfaces.routes",
    "backend.app.application",
    "backend.app.engine",
    "backend.app.domain",
    "backend.app.workflows",
    "backend.app.infrastructure",
]

COLLECT_DATA = ["ebooklib", "reportlab"]


def build() -> int:
    DIST.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)

    binary_name = "ai-novel-backend"
    if platform.system() == "Windows":
        binary_name = "ai-novel-backend.exe"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "ai-novel-backend",
        "--distpath", str(DIST),
        "--workpath", str(WORK),
        "--specpath", str(WORK),
        "--noconfirm",
        "--clean",
    ]

    for hidden in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", hidden])

    for data in COLLECT_DATA:
        cmd.extend(["--collect-data", data])

    # PyInstaller 6 的 --collect-submodules 更彻底
    for pkg in ["uvicorn", "fastapi", "starlette", "pydantic"]:
        cmd.extend(["--collect-submodules", pkg])

    # Include backend source tree as data (so backend.app.* can be imported at runtime)
    sep = ";" if platform.system() == "Windows" else ":"
    cmd.extend(["--add-data", f"{BACKEND}{sep}backend"])

    # Include prompt_packages YAML files
    prompt_dir = BACKEND / "app" / "prompt_packages"
    if prompt_dir.exists():
        cmd.extend(["--add-data", f"{prompt_dir}{sep}backend/app/prompt_packages"])

    cmd.append(str(BACKEND / "sidecar_entry.py"))

    print(f"[build_sidecar] ROOT={ROOT}")
    print(f"[build_sidecar] DIST={DIST}")
    print(f"[build_sidecar] running PyInstaller...")

    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print(f"[build_sidecar] FAILED: PyInstaller exit {result.returncode}")
        return result.returncode

    out = DIST / binary_name
    if not out.exists():
        print(f"[build_sidecar] FAILED: 产物未找到 {out}")
        return 1

    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"[build_sidecar] OK: {out}  ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(build())
