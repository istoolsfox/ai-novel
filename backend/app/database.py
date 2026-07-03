"""Re-export shim — 实际实现已迁移到 infrastructure/database.py。

保留此文件是为了向后兼容现有导入路径（`from .database import ...`）。
后续可逐步更新所有导入路径后删除此文件。
"""
from .infrastructure.database import *  # noqa: F401,F403
from .infrastructure.database import (  # noqa: F401  (显式导出 * 可能遗漏的符号)
    GENERIC_TABLES,
    connect,
    create_archaeology,
    create_chapter_bridge,
    create_emotion_seed,
    create_emotional_lead,
    create_image_growth,
    database_path,
    get_archaeology,
    get_chapter_bridge,
    get_emotion_seed,
    get_emotional_lead,
    get_previous_chapter_bridge,
    init_db,
    list_archaeology,
    list_chapter_bridges,
    list_emotional_leads,
    list_image_growth,
    new_id,
    row_to_dict,
    rows_to_dicts,
    update_emotional_lead,
    utc_now,
)
