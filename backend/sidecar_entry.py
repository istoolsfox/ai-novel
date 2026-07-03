"""PyInstaller 打包入口。启动 uvicorn 服务，供 Tauri 作为 sidecar 拉起。

环境变量（由 Tauri 注入）：
    AI_NOVEL_PORT        —— 监听端口（默认 8000）
    AI_NOVEL_HOST        —— 监听地址（默认 127.0.0.1）
    AI_NOVEL_DATABASE_URL —— SQLite 路径
    AI_NOVEL_DATA_DIR    —— 数据根目录
    AI_NOVEL_LOG_LEVEL   —— 日志级别（默认 warning）
"""
import os
import sys
from pathlib import Path


def _bootstrap_path() -> None:
    """PyInstaller 打包后修正 sys.path，保证 backend.app 可导入。"""
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后，_MEIPASS 是临时解压目录
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            sys.path.insert(0, str(Path(meipass)))
        # exe 同级目录（可能放有 backend/ 包）
        base_dir = Path(sys.executable).resolve().parent
        sys.path.insert(0, str(base_dir))
        # 仓库根目录（开发模式 exe 在 desktop/binaries/ 下）
        root = base_dir.parent.parent
        if (root / "backend").exists():
            sys.path.insert(0, str(root))
    else:
        # 开发模式下，把仓库根目录加入 path
        root = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(root))


def main() -> None:
    _bootstrap_path()

    port = int(os.environ.get("AI_NOVEL_PORT", "8000"))
    host = os.environ.get("AI_NOVEL_HOST", "127.0.0.1")
    log_level = os.environ.get("AI_NOVEL_LOG_LEVEL", "warning")

    # 直接导入 app 对象（而非用字符串路径，避免 PyImporter 解析失败）
    from backend.app.main import app

    import uvicorn

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=False,
        timeout_keep_alive=30,
    )


if __name__ == "__main__":
    main()
