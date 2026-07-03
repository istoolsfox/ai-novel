"""工作流层 · LLM 客户端封装。

从 main.py 迁出，包含：
- system_prompt_for_workflow：从 YAML 提示词包渲染系统提示词
- _format_bridge_directive：把上一章衔接包格式化为强约束指令
- local_proxy_timeout_detail：本地代理超时提示
- resolve_model_config：解析项目的模型配置
- run_model_or_stub：调用远程模型，失败回退到本地 stub
- test_model_connection：测试远程模型连接（供路由调用）
"""
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ..application.context_builder import (
    compact_generation_context,
    compact_payload_for_remote,
    max_tokens_for_config,
    request_timeout_for_workflow,
)
from ..domain.models import AiWorkflowIn, ModelConnectionTestIn
from ..engine.prompt_loader import render_system_prompt
from ..infrastructure.database import connect, row_to_dict, rows_to_dicts
from .generation import build_stub_ai_output, parse_structured_ai_text


# 工作流名 → YAML 提示词包名映射
_WORKFLOW_TO_PACKAGE = {
    "generate_chapter_draft": "generate_chapter_draft",
    "revise_selection": "generate_chapter_draft",
    "generate_outline": "generate_chapter_brief",
    "generate_chapter_brief": "generate_chapter_brief",
    "generate_chapter_bridge": "generate_chapter_bridge",
}


# ---------------------------------------------------------------------------
# 系统提示词渲染
# ---------------------------------------------------------------------------
def system_prompt_for_workflow(workflow: str, emotion_seed: dict | None = None, prev_bridge: dict | None = None) -> str:
    """从 YAML 提示词包渲染系统提示词。找不到包时返回通用默认。"""
    package_name = _WORKFLOW_TO_PACKAGE.get(workflow)
    if not package_name:
        return render_system_prompt(workflow)  # 回退通用默认

    context: dict[str, Any] = {}
    if emotion_seed:
        seed = emotion_seed.get("emotion_seed", emotion_seed)
        if isinstance(seed, dict):
            context["emotion_seed"] = seed
    if prev_bridge:
        is_draft = workflow in {"generate_chapter_draft", "revise_selection"}
        context["bridge_directive"] = _format_bridge_directive(prev_bridge, is_draft=is_draft)
        context["prev_bridge"] = prev_bridge

    return render_system_prompt(package_name, context)


def _format_bridge_directive(prev_bridge: dict, is_draft: bool) -> str:
    """把上一章衔接包格式化为强约束指令。"""
    bridge_json = prev_bridge.get("bridge_json")
    if isinstance(bridge_json, str):
        try:
            bridge_json = json.loads(bridge_json)
        except json.JSONDecodeError:
            bridge_json = {}
    if not isinstance(bridge_json, dict):
        bridge_json = {}

    ending = bridge_json.get("ending_state", {})
    hooks = bridge_json.get("open_hooks", [])
    residue = bridge_json.get("emotional_residue", [])
    seeds = bridge_json.get("next_chapter_seeds", [])
    revealed = bridge_json.get("info_revealed", [])
    withheld = bridge_json.get("info_withheld", [])
    tension = bridge_json.get("unresolved_tension", "")

    prev_num = prev_bridge.get("chapter_number", "?")
    lines = [f"\n\n【上一章（第{prev_num}章）衔接包·本章必须承接，不可无视】"]

    if ending:
        lines.append(f"\n上一章末尾状态（本章开头必须从这里接起，不要跳跃时空）：")
        if isinstance(ending, dict):
            for k, v in ending.items():
                lines.append(f"  · {k}：{v}")
        else:
            lines.append(f"  · {ending}")

    if hooks:
        lines.append(f"\n上一章留下的未决钩子（本章必须回应至少一个，不要全部悬置）：")
        for h in hooks:
            if isinstance(h, dict):
                lines.append(f"  · {h.get('hook', '')}（紧迫度：{h.get('urgency', '中')}）")
            else:
                lines.append(f"  · {h}")

    if residue:
        lines.append(f"\n上一章末尾各角色情感余波（本章开头角色的情绪必须从这里起步，不要凭空切换）：")
        for r in residue:
            if isinstance(r, dict):
                lines.append(f"  · {r.get('character', '?')}：{r.get('emotion', '')}（强度{r.get('intensity', '?')}/10）{r.get('physical', '')}")
            else:
                lines.append(f"  · {r}")

    if revealed:
        lines.append(f"\n上一章已揭示的信息（不要重复揭示，要在其基础上推进）：")
        for info in revealed:
            lines.append(f"  · {info}")

    if withheld:
        lines.append(f"\n上一章故意没揭示的（本章可以触及但不一定要揭开，控制节奏）：")
        for info in withheld:
            lines.append(f"  · {info}")

    if seeds:
        lines.append(f"\n上一章为本章埋的种子（可选承接，让叙事有连续感）：")
        for s in seeds:
            lines.append(f"  · {s}")

    if tension:
        lines.append(f"\n未解张力：{tension}")

    lines.append(
        "\n【连贯性硬约束】"
        "\n1. 本章开头必须承接上一章末尾状态，不能突然跳到另一个时间/地点/情境。"
        "\n2. 角色情绪必须从上一章余波起步，要有过渡，不要凭空切换。"
        "\n3. 必须回应至少一个未决钩子，不能全部无视。"
        "\n4. 不要重复揭示已揭示的信息，要在其后果上推进。"
    )
    if is_draft:
        lines.append("5. 写正文时，前 2-3 段必须有明显的承接感（呼应上一章末尾的动作、情境或情绪）。")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 模型配置解析
# ---------------------------------------------------------------------------
def resolve_model_config(project_id: str, workflow: str) -> dict[str, Any] | None:
    with connect() as conn:
        route = row_to_dict(
            conn.execute(
                """
                SELECT * FROM model_task_routes
                WHERE project_id = ? AND (category = ? OR title = ?)
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (project_id, workflow, workflow),
            ).fetchone()
        )
        if route and route.get("content"):
            config = row_to_dict(
                conn.execute(
                    "SELECT * FROM model_configs WHERE project_id = ? AND id = ?",
                    (project_id, route["content"]),
                ).fetchone()
            )
            if config:
                return config
        configs = rows_to_dicts(
            conn.execute(
                "SELECT * FROM model_configs WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        )
        default_config = next(
            (
                config
                for config in configs
                if isinstance(config.get("payload"), dict) and config["payload"].get("is_default")
            ),
            None,
        )
        return default_config or (configs[0] if configs else None)


# ---------------------------------------------------------------------------
# 超时提示
# ---------------------------------------------------------------------------
def local_proxy_timeout_detail(base_url: str, model: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    host = parsed.hostname or ""
    port = parsed.port
    target = f"{host}:{port}" if port else host
    if host in {"127.0.0.1", "localhost", "::1"}:
        return (
            f"远程模型连接失败：本地模型代理 {target} 已接收测试请求，但等待上游模型响应超时。"
            f"当前模型：{model}。请检查 cli-proxy-api、mihomo/系统代理、节点稳定性，以及该代理是否支持此模型名。"
        )
    return (
        f"远程模型连接失败：请求 {base_url} 超时。当前模型：{model}。"
        "请检查 Base URL、网络代理、服务商状态和模型名。"
    )


# ---------------------------------------------------------------------------
# 远程模型调用
# ---------------------------------------------------------------------------
def run_model_or_stub(project_id: str, workflow: str, payload: AiWorkflowIn, context: dict[str, Any]) -> dict[str, Any]:
    config = resolve_model_config(project_id, workflow)
    if not config:
        return build_stub_ai_output(
            workflow,
            payload,
            context,
            f"当前使用本地占位模型：未找到可用于 {workflow} 的远程模型配置。请在设置中保存模型并设为默认，或在任务路由中为该任务选择模型。",
        )

    config_payload = config.get("payload") if isinstance(config.get("payload"), dict) else {}
    api_key = str(config_payload.get("api_key") or "")
    base_url = str(config_payload.get("base_url") or "https://api.openai.com/v1").rstrip("/")
    model = str(config_payload.get("model_name") or config.get("title") or "")
    if not api_key or not model:
        return build_stub_ai_output(
            workflow,
            payload,
            context,
            f'模型配置「{config.get("title") or "未命名模型"}」缺少 API Key 或 Model Name。',
        )

    remote_payload = compact_payload_for_remote(workflow, payload)
    remote_context = compact_generation_context(context)
    request_body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt_for_workflow(workflow, context.get("emotion_seed"), context.get("prev_chapter_bridge"))},
            {
                "role": "user",
                "content": (
                    f"工作流：{workflow}\n\n"
                    f"输入：{json.dumps(remote_payload, ensure_ascii=False)}\n\n"
                    f"llmwiki 与写作上下文：{json.dumps(remote_context, ensure_ascii=False)}"
                ),
            },
        ],
        "temperature": float(config_payload.get("temperature") or 0.7),
        "max_tokens": max_tokens_for_config(config_payload),
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    timeout_seconds = request_timeout_for_workflow(workflow)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"]
        return {
            "workflow": workflow,
            "model": model,
            "text": text,
            "score": 0,
            "structured": parse_structured_ai_text(text),
            "status": "success",
            "error": "",
            "items": [{"title": workflow, "content": text}],
        }
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:1000].strip()
        summary = f"HTTP {exc.code}: {detail or exc.reason}"
        fallback = build_stub_ai_output(workflow, payload, context, "远程模型调用失败。")
        fallback["status"] = "fallback"
        fallback["error"] = summary
        return fallback
    except TimeoutError as exc:
        fallback = build_stub_ai_output(workflow, payload, context, "远程模型调用超时。")
        fallback["status"] = "fallback"
        fallback["error"] = (
            f"远程模型仍可能在生成，但 {timeout_seconds} 秒内暂未返回结果。"
            "这通常不是提示词或网络配置错误；可稍后重试，或通过 AI_NOVEL_GENERATION_TIMEOUT_SECONDS 继续放宽等待时间。"
            f"原始错误：{exc}"
        )
        return fallback
    except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
        fallback = build_stub_ai_output(workflow, payload, context, "远程模型调用失败。")
        fallback["status"] = "fallback"
        fallback["error"] = str(exc)
        return fallback


# ---------------------------------------------------------------------------
# 模型连接测试
# ---------------------------------------------------------------------------
def test_remote_model_connection(payload: ModelConnectionTestIn) -> dict[str, Any]:
    """测试远程模型连接。成功返回 {ok: True}，失败抛 HTTPException。"""
    from fastapi import HTTPException

    api_key = payload.api_key.strip()
    model = payload.model_name.strip()
    base_url = (payload.base_url or "https://api.openai.com/v1").rstrip("/")
    if not api_key or not model:
        raise HTTPException(status_code=400, detail="缺少 API Key 或 Model Name，无法测试远程模型连接。")

    request_body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是模型连接测试程序。"},
            {"role": "user", "content": "请只回复 OK。"},
        ],
        "temperature": payload.temperature,
        "max_tokens": max(1, min(payload.max_tokens or 16, 64)),
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        _ = data["choices"][0]["message"]["content"]
        return {"ok": True, "model": model, "message": "远程模型连接成功。"}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:400]
        raise HTTPException(status_code=502, detail=f"远程模型连接失败：HTTP {exc.code} {detail}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise HTTPException(status_code=502, detail=local_proxy_timeout_detail(base_url, model)) from exc
    except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail=f"远程模型连接失败：{exc}") from exc
