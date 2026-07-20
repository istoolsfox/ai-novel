from typing import Any

from .continuity_store import json_text


def draft_chunks(text: str, chunk_size: int = 1300, max_chunks: int = 10) -> list[str]:
    clean = text.strip()
    if not clean:
        return []
    chunks = [clean[index : index + chunk_size] for index in range(0, len(clean), chunk_size)]
    if len(chunks) <= max_chunks:
        return chunks
    head_count = max_chunks // 2
    return chunks[:head_count] + chunks[-(max_chunks - head_count) :]


def draft_prompt(contract: dict[str, Any], chapter_number: int) -> str:
    compact = {
        "must_continue_from": contract.get("must_continue_from", {}),
        "character_constraints": contract.get("character_constraints", []),
        "open_actions": contract.get("open_actions", []),
        "open_hooks": contract.get("open_hooks", []),
        "emotional_residue": contract.get("emotional_residue", []),
        "forbidden_repetition": contract.get("forbidden_repetition", []),
        "next_chapter_seeds": contract.get("next_chapter_seeds", []),
        "chapter_goal": contract.get("chapter_goal", ""),
    }
    return (
        f"生成第 {chapter_number} 章完整正文。必须严格承接以下章节执行合同。"
        "开头必须解释时间、地点或动作如何从上一章延续；人物伤势、情绪、目标和知识边界不得重置。"
        "角色不能说出其尚未知晓的事实，不能重复已经完成的信息揭示。"
        "如果旧大纲与已定稿正文冲突，以合同中的实际状态为准。\n\n"
        f"章节执行合同：{json_text(compact)}"
    )


def check_prompt(contract: dict[str, Any], bridge: dict[str, Any], draft: str, *, recheck: bool) -> str:
    stage = "修复后复检" if recheck else "初次检查"
    return (
        f"你正在执行章节连续性{stage}。只返回 JSON，不要输出解释性前后缀。"
        "逐项检查时间、地点、正在进行的动作、人物身体状态、人物情绪、人物目标、人物知识边界、"
        "关系变化、未完成钩子和重复事件。必须提供可定位、可修复的问题。"
        "返回结构："
        '{"status":"pass|warning|fail","score":0,'
        '"issues":[{"type":"time|location|character_state|knowledge|emotion|plot|repetition",'
        '"severity":"low|medium|high|critical","description":"","evidence":"","suggestion":""}],'
        '"continuity_summary":""}。'
        f"\n章节合同：{json_text(contract)}"
        f"\n上一章衔接包：{json_text(bridge)}"
        f"\n正文分段：{json_text(draft_chunks(draft))}"
    )


def normalize_check(result: dict[str, Any], *, stage: str) -> dict[str, Any]:
    structured = result.get("structured") if isinstance(result.get("structured"), dict) else None
    if not structured:
        return {
            "status": "fail",
            "score": 0,
            "issues": [
                {
                    "type": "system",
                    "severity": "high",
                    "description": "连续性检查结果不是有效 JSON。",
                    "evidence": str(result.get("text") or "")[:300],
                    "suggestion": "重试连续性检查步骤。",
                }
            ],
            "continuity_summary": "检查结果无法解析。",
            "stage": stage,
        }
    issues = structured.get("issues") if isinstance(structured.get("issues"), list) else []
    try:
        score = max(0.0, min(float(structured.get("score", 0)), 100.0))
    except (TypeError, ValueError):
        score = 0.0
    status = str(structured.get("status") or "warning").lower()
    if status not in {"pass", "warning", "fail"}:
        status = "warning"
    return {
        "status": status,
        "score": score,
        "issues": [item for item in issues if isinstance(item, dict)],
        "continuity_summary": str(structured.get("continuity_summary") or ""),
        "stage": stage,
    }


def blocking_issues(check: dict[str, Any]) -> list[dict[str, Any]]:
    blocking = []
    for issue in check.get("issues") or []:
        severity = str(issue.get("severity") or "").lower()
        if severity in {"high", "critical", "高", "严重", "致命"}:
            blocking.append(issue)
    if check.get("status") == "fail" and not blocking:
        blocking.append({"description": "连续性检查未通过。", "severity": "high"})
    return blocking


def repair_prompt(check: dict[str, Any], contract: dict[str, Any]) -> str:
    return (
        "只修复下列连续性问题，保留原章节中不相关的情节、文风、信息密度和结尾钩子。"
        "不要把正文改成大纲，不要添加解释性说明。修复后只返回完整章节正文。"
        f"\n问题：{json_text(check.get('issues') or [])}"
        f"\n章节执行合同：{json_text(contract)}"
    )


def memory_prompt(contract: dict[str, Any], draft: str) -> str:
    return (
        "阅读本章正文并编译下一章需要的结构化记忆。只返回 JSON，不要包裹 Markdown。"
        "不得把推测写成已确认事实；人物知识变化必须区分 unknown、suspected、believed、confirmed、"
        "disbelieved、forgotten、misinformed。返回结构："
        '{"summary":"","ending_state":{"time":"","location":"","weather":"",'
        '"current_action":"","current_danger":""},'
        '"character_states":[{"character_id":"","character_name":"","location":"",'
        '"physical_state":"","emotional_state":"","current_goal":"",'
        '"alive_status":"alive","visibility_status":"public"}],'
        '"knowledge_changes":[{"character_id":"","character_name":"","fact_key":"",'
        '"fact_text":"","knowledge_status":"suspected","confidence":0.0}],'
        '"relationship_changes":[],"open_actions":[],"open_hooks":[],"emotional_residue":[], '
        '"forbidden_repetition":[],"next_chapter_seeds":[]}。'
        f"\n章节执行合同：{json_text(contract)}"
        f"\n正文分段：{json_text(draft_chunks(draft))}"
    )


def fallback_memory(chapter: dict[str, Any]) -> dict[str, Any]:
    draft = str(chapter.get("draft") or "")
    summary = str(chapter.get("summary") or chapter.get("brief") or draft[-400:] or "本章已完成。")
    return {
        "summary": summary,
        "ending_state": {
            "time": "",
            "location": "",
            "weather": "",
            "current_action": draft[-300:],
            "current_danger": "",
        },
        "character_states": [],
        "knowledge_changes": [],
        "relationship_changes": [],
        "open_actions": [],
        "open_hooks": [],
        "emotional_residue": [],
        "forbidden_repetition": [summary],
        "next_chapter_seeds": [draft[-300:] or summary],
    }


def normalize_memory(result: dict[str, Any], chapter: dict[str, Any]) -> dict[str, Any]:
    structured = result.get("structured") if isinstance(result.get("structured"), dict) else None
    if not structured:
        return fallback_memory(chapter)
    fallback = fallback_memory(chapter)
    ending = structured.get("ending_state") if isinstance(structured.get("ending_state"), dict) else {}
    return {
        "summary": str(structured.get("summary") or fallback["summary"]),
        "ending_state": {
            "time": str(ending.get("time") or ""),
            "location": str(ending.get("location") or ""),
            "weather": str(ending.get("weather") or ""),
            "current_action": str(ending.get("current_action") or fallback["ending_state"]["current_action"]),
            "current_danger": str(ending.get("current_danger") or ""),
        },
        "character_states": [item for item in (structured.get("character_states") or []) if isinstance(item, dict)],
        "knowledge_changes": [item for item in (structured.get("knowledge_changes") or []) if isinstance(item, dict)],
        "relationship_changes": [item for item in (structured.get("relationship_changes") or []) if isinstance(item, dict)],
        "open_actions": list(structured.get("open_actions") or []),
        "open_hooks": list(structured.get("open_hooks") or []),
        "emotional_residue": list(structured.get("emotional_residue") or []),
        "forbidden_repetition": list(structured.get("forbidden_repetition") or fallback["forbidden_repetition"]),
        "next_chapter_seeds": list(structured.get("next_chapter_seeds") or fallback["next_chapter_seeds"]),
    }
