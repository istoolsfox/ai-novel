"""Re-export shim — 实际实现已迁移到 infrastructure/storage.py。

保留此文件是为了向后兼容现有导入路径（`from .storage import ...`）。
"""
from .infrastructure.storage import *  # noqa: F401,F403
from .infrastructure.storage import (  # noqa: F401
    data_root,
    ensure_project_dirs,
    project_or_none,
    project_root,
    require_project,
    safe_wiki_path,
)
