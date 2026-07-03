"""引擎内核 · 提示词加载器。

从 YAML 配置加载提示词包，支持：
- 条件指令（directives）：根据上下文动态拼接
- 模板渲染：{field.subfield} 替换为上下文值
- 模型参数：temperature/top_p/max_tokens
- 题材目录：_base 为默认，可按题材覆写
"""
import json
from pathlib import Path
from typing import Any

import yaml

_PROMPT_PACKAGES_DIR = Path(__file__).resolve().parent.parent / "prompt_packages"
_PROMPT_CACHE: dict[str, dict] = {}


def load_prompt_package(workflow: str, genre: str = "_base") -> dict:
    """加载提示词包。优先从题材目录加载，回退到 _base。

    Args:
        workflow: 工作流名称（如 generate_chapter_draft）
        genre: 题材目录名，默认 _base

    Returns:
        提示词包字典，结构同 YAML。找不到返回空 dict。
    """
    cache_key = f"{genre}/{workflow}"
    if cache_key in _PROMPT_CACHE:
        return _PROMPT_CACHE[cache_key]

    # 优先题材目录，回退 _base
    for dir_name in (genre, "_base"):
        path = _PROMPT_PACKAGES_DIR / dir_name / f"{workflow}.yaml"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data:
                _PROMPT_CACHE[cache_key] = data
                return data

    _PROMPT_CACHE[cache_key] = {}
    return {}


def _evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    """在上下文中求值条件表达式。

    安全限制：只用 context 中的变量，不访问内置函数。
    """
    if not condition or condition.strip() == "always":
        return True
    try:
        return bool(eval(condition, {"__builtins__": {}}, context))
    except Exception:
        return False


def _render_template(template: str, context: dict[str, Any]) -> str:
    """渲染模板，把 {field.subfield} 替换为上下文值。

    支持：
    - {name} → context["name"]
    - {obj.attr} → context["obj"]["attr"]
    - 找不到的占位符保留原样
    """
    if not template:
        return template

    result = template
    # 处理 {a.b.c} 形式的占位符
    import re
    placeholders = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_.]*)\}", result)
    for ph in placeholders:
        value = _resolve_path(ph, context)
        if value is not None:
            result = result.replace(f"{{{ph}}}", str(value))
    return result


def _resolve_path(path: str, context: dict[str, Any]) -> Any:
    """解析 a.b.c 路径，从 context 中取值。"""
    parts = path.split(".")
    current: Any = context
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return None
        if current is None:
            return None
    return current


def render_system_prompt(
    workflow: str,
    context: dict[str, Any] | None = None,
    genre: str = "_base",
) -> str:
    """渲染系统提示词：base + 满足条件的 directives。

    Args:
        workflow: 工作流名称
        context: 上下文字典，用于条件判断和模板渲染
        genre: 题材目录名

    Returns:
        渲染后的系统提示词字符串。找不到包时返回通用默认。
    """
    ctx = context or {}
    pkg = load_prompt_package(workflow, genre)
    if not pkg:
        return "你是专业的中文长篇小说创作助手。需要结构化工作流时，只返回 JSON，不要包裹解释。"

    base = pkg.get("system_prompt", "")

    for directive in pkg.get("directives", []):
        condition = directive.get("condition", "always")
        if _evaluate_condition(condition, ctx):
            template = directive.get("template", "")
            rendered = _render_template(template, ctx)
            base = base + rendered

    return base


def get_model_params(workflow: str, genre: str = "_base") -> dict[str, Any]:
    """获取模型参数。

    Returns:
        {"temperature": float, "top_p": float, "max_tokens": int}
        找不到包时返回默认值。
    """
    pkg = load_prompt_package(workflow, genre)
    return pkg.get("model_params", {
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 2048,
    })


def list_available_workflows(genre: str = "_base") -> list[str]:
    """列出某题材下所有可用的工作流名称。"""
    dir_path = _PROMPT_PACKAGES_DIR / genre
    if not dir_path.exists():
        return []
    return sorted(p.stem for p in dir_path.glob("*.yaml"))
