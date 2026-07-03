"""向后兼容 shim。

实际的 FastAPI app 已迁移到 interfaces/main.py。
此文件保留是为了不破坏现有导入路径：
- `uvicorn backend.app.main:app` 仍然可用
- `from backend.app.main import xxx`（测试中可能用到）通过 re-export 保持兼容
- 测试中 monkeypatch.setattr(main.urllib.request, "urlopen", ...) 仍然可用
"""
import json  # noqa: F401
import os  # noqa: F401
import socket  # noqa: F401
import urllib.error  # noqa: F401
import urllib.parse  # noqa: F401
import urllib.request  # noqa: F401
from io import BytesIO  # noqa: F401
from pathlib import Path  # noqa: F401

# urllib 作为模块属性暴露（测试用 main.urllib.request）
import urllib  # noqa: F401

# === FastAPI app + 装配 ===
from .interfaces.main import app, health  # noqa: F401

# === 请求模型（domain 层 re-export）===
from .domain.models import (  # noqa: F401
    AiWorkflowIn,
    ChapterIn,
    DeleteProjectIn,
    GenericIn,
    ModelConnectionTestIn,
    ProjectIn,
    VersionIn,
    WikiWriteIn,
)

# === 上下文工具（application 层 re-export）===
from .application.context_builder import (  # noqa: F401
    build_generation_context,
    compact_chapter_for_prompt,
    compact_generation_context,
    compact_payload_for_remote,
    compact_record,
    compact_value,
    max_tokens_for_config,
    request_timeout_for_workflow,
    trim_text,
)

# === 工作流（workflows 层 re-export）===
from .workflows.generation import (  # noqa: F401
    CHARACTER_STUBS,
    LONG_FORM_ARCS,
    build_local_chapter_draft,
    build_stub_ai_output,
    character_stub_for_payload,
    clean_chapter_title,
    collect_existing_character_names,
    local_arc_for_chapter,
    narrative_focus_from_brief,
    outline_focus_for_chapter,
    parse_structured_ai_text,
    primary_character_name,
    recent_chapter_line,
    structured_output_for_workflow,
    validate_workflow_prerequisites,
)
from .workflows.llm_client import (  # noqa: F401
    _format_bridge_directive,
    _WORKFLOW_TO_PACKAGE,
    local_proxy_timeout_detail,
    resolve_model_config,
    run_model_or_stub,
    system_prompt_for_workflow,
    test_remote_model_connection,
)

# === 记忆服务（application 层 re-export）===
from .application.memory_service import (  # noqa: F401
    auto_generate_bridge,
    chapter_memory_summary,
    create_structured_record,
    delete_record_from_wiki,
    delete_wiki_page,
    list_records_for_context,
    rebuild_volume_memory,
    sync_chapter_memory_to_wiki,
    table_for_resource,
    upsert_wiki_page,
    volume_memory_path,
    volume_name_for_chapter,
    write_chapter_snapshot,
)

# === 接口层辅助（interfaces 层 re-export）===
from .interfaces.dependencies import require_chapter  # noqa: F401


# === 基础设施层 re-export ===
from .infrastructure.database import (  # noqa: F401
    GENERIC_TABLES,
    connect,
    create_archaeology,
    create_chapter_bridge,
    create_emotion_seed,
    create_emotional_lead,
    create_image_growth,
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
from .infrastructure.storage import (  # noqa: F401
    ensure_project_dirs,
    project_root,
    require_project,
    safe_wiki_path,
)


def init_app() -> None:
    """初始化数据库（兼容旧调用）。"""
    init_db()
