from typing import Any

from .continuity_prompts import draft_chunks, normalize_memory
from .continuity_store import json_text, latest_contract, require_chapter
from .memory_store import begin_compilation, memory_context, persist_extended_layers


def layered_memory_prompt(
    contract: dict[str, Any],
    current_memory: dict[str, Any],
    draft: str,
) -> str:
    return (
        "你是长篇小说的记忆编译器。阅读本章正文，把实际发生的变化编译成结构化状态。"
        "只返回 JSON，不要输出 Markdown 或解释。不得把推测写成确认事实；"
        "沿用 current_memory 中已有的稳定 key，只有真正的新对象才创建新 key。"
        "关系 value 使用 -1 到 1；priority 和 confidence 使用 0 到 1。"
        "叙事债务状态只能是 open、progressed、resolved、cancelled；"
        "伏笔状态只能是 planted、deepened、paid_off、abandoned。"
        "返回结构："
        '{"summary":"","ending_state":{"time":"","location":"","weather":"",'
        '"current_action":"","current_danger":""},'
        '"hard_facts":[{"fact_key":"","fact_text":"","fact_status":"confirmed|disputed|retracted",'
        '"confidence":0.0}],'
        '"character_states":[{"character_id":"","character_name":"","location":"",'
        '"physical_state":"","emotional_state":"","current_goal":"",'
        '"alive_status":"alive","visibility_status":"public"}],'
        '"knowledge_changes":[{"character_id":"","character_name":"","fact_key":"",'
        '"fact_text":"","knowledge_status":"unknown|suspected|believed|confirmed|disbelieved|forgotten|misinformed",'
        '"confidence":0.0}],'
        '"relationship_changes":[{"source_character_id":"","source_character_name":"",'
        '"target_character_id":"","target_character_name":"","relation_type":"",'
        '"value":0.0,"status":"active|ended","reason":""}],'
        '"item_changes":[{"item_key":"","item_name":"","description":"",'
        '"item_status":"active|lost|destroyed|consumed","change_type":"created|transferred|lost|destroyed|consumed",'
        '"owner_type":"character|location|organization|unknown","owner_id":"","owner_name":"",'
        '"location":"","ownership_status":"held|lost|destroyed|consumed"}],'
        '"narrative_debt_changes":[{"debt_key":"","debt_type":"open_question|promise|emotional_response|'
        'unfinished_action|interrupted_dialogue|mystery|countdown|goal","description":"",'
        '"status":"open|progressed|resolved|cancelled","priority":0.0,"deadline_chapter":0}],'
        '"foreshadowing_changes":[{"foreshadowing_key":"","title":"","description":"",'
        '"status":"planted|deepened|paid_off|abandoned","setup_chapter":0,"payoff_chapter":0,'
        '"priority":0.0}],'
        '"open_actions":[],"open_hooks":[],"emotional_residue":[],'
        '"forbidden_repetition":[],"next_chapter_seeds":[]}。'
        f"\n章节执行合同：{json_text(contract)}"
        f"\n当前有效记忆：{json_text(current_memory)}"
        f"\n正文分段：{json_text(draft_chunks(draft))}"
    )


def _dict_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def normalize_layered_memory(
    result: dict[str, Any],
    chapter: dict[str, Any],
) -> dict[str, Any]:
    base = normalize_memory(result, chapter)
    structured = result.get("structured") if isinstance(result.get("structured"), dict) else {}
    base.update(
        {
            "hard_facts": _dict_items(structured.get("hard_facts")),
            "relationship_changes": _dict_items(structured.get("relationship_changes")),
            "item_changes": _dict_items(structured.get("item_changes")),
            "narrative_debt_changes": _dict_items(structured.get("narrative_debt_changes")),
            "foreshadowing_changes": _dict_items(structured.get("foreshadowing_changes")),
        }
    )
    return base


def compile_chapter_memory(
    project_id: str,
    chapter_id: str,
    _chapter_number: int | None = None,
) -> dict[str, Any]:
    from . import main

    chapter = require_chapter(project_id, chapter_id)
    contract_row = latest_contract(project_id, chapter_id)
    contract = contract_row.get("payload") if contract_row and isinstance(contract_row.get("payload"), dict) else {}
    current = memory_context(project_id)
    draft = str(chapter.get("draft") or "")
    output = main.run_ai_workflow(
        project_id,
        "extract_memory",
        main.AiWorkflowIn(
            chapter_id=chapter_id,
            prompt=layered_memory_prompt(contract, current, draft),
            payload={
                "contract": contract,
                "current_memory": current,
                "draft_chunks": draft_chunks(draft),
            },
        ),
    )
    memory = normalize_layered_memory(output, chapter)
    return {
        "workflow": "compile_chapter_memory",
        "model": output.get("model", ""),
        "status": "success",
        "text": json_text(memory),
        "structured": memory,
    }


def enhanced_draft_prompt(contract: dict[str, Any], chapter_number: int) -> str:
    from .continuity_prompts import draft_prompt as base_draft_prompt

    base = base_draft_prompt(contract, chapter_number)
    layered = {
        "hard_facts": contract.get("hard_facts", []),
        "relationship_states": contract.get("relationship_states", []),
        "item_ownership": contract.get("item_ownership", []),
        "narrative_debts": contract.get("narrative_debts", []),
        "active_foreshadowings": contract.get("active_foreshadowings", []),
    }
    return (
        f"{base}\n\n"
        "以下结构化记忆同样属于强约束：物品不能无理由转移，关系变化必须有过渡；"
        "尚未解决的叙事债务不能被遗忘，已埋伏笔不得被当成首次出现。"
        f"\n分层记忆：{json_text(layered)}"
    )


def persist_compiled_memory(
    conn,
    step: dict[str, Any],
    memory: dict[str, Any],
    *,
    model: str = "",
) -> None:
    from .continuity_store import persist_bridge_and_memory as base_persist

    compilation_id, now = begin_compilation(conn, step, memory, model=model)
    conn.execute(
        "DELETE FROM character_states WHERE project_id = ? AND chapter_id = ?",
        (step["project_id"], step["chapter_id"]),
    )
    conn.execute(
        "DELETE FROM character_knowledge WHERE project_id = ? AND source_chapter_id = ?",
        (step["project_id"], step["chapter_id"]),
    )
    base_persist(conn, step, memory)
    persist_extended_layers(conn, step, memory, compilation_id, now)
