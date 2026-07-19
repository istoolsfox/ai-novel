from typing import Any, Callable

from .story_graph_store import json_text, persist_story_graph_layers


def graph_prompt_suffix(current_memory: dict[str, Any]) -> str:
    current_graph = {
        "story_threads": current_memory.get("story_threads", []),
        "story_nodes": current_memory.get("story_nodes", []),
        "story_edges": current_memory.get("story_edges", []),
        "story_focus": current_memory.get("story_focus", []),
        "stalled_threads": current_memory.get("stalled_threads", []),
    }
    return (
        "\n同时把本章对多线剧情图谱造成的实际变化编译出来。沿用当前图谱中的稳定 key；"
        "不要因为同一条线换了表达就创建新线程。章节可以同时推进多条线程。"
        "线程类型只能是 main_plot、character_arc、romance、mystery、faction、world_change、"
        "foreshadowing、theme、subplot；线程状态只能是 active、paused、blocked、resolved、abandoned。"
        "节点类型只能是 event、scene、decision、reveal、conflict、foreshadowing、payoff、"
        "turning_point、goal、obstacle；节点状态只能是 planned、active、completed、blocked、cancelled。"
        "边类型只能是 causes、depends_on、blocks、reveals、plants、pays_off、conflicts_with、"
        "continues、alternative_to。推进类型只能是 introduced、advanced、paused、blocked、resolved、regressed。"
        "返回 JSON 时在原结构中增加："
        '"story_thread_changes":[{"thread_key":"","title":"","thread_type":"main_plot",'
        '"status":"active","priority":0.0,"current_stage":"","current_goal":"",'
        '"next_target":"","stall_tolerance":3}],'
        '"story_node_changes":[{"node_key":"","thread_key":"","node_type":"event",'
        '"title":"","description":"","status":"planned","importance":0.0,'
        '"planned_chapter":0,"actual_chapter":0}],'
        '"story_edge_changes":[{"edge_key":"","source_node_key":"","target_node_key":"",'
        '"relation_type":"continues","status":"active","weight":1.0}],'
        '"story_progress":[{"thread_key":"","progress_type":"advanced",'
        '"progress_summary":"","before_stage":"","after_stage":"",'
        '"progress_score":0.0,"source_node_keys":[]}].'
        "只有正文真实发生变化时才写 progress；单纯提及不算推进。"
        f"\n当前剧情图谱：{json_text(current_graph)}"
    )


def wrap_layered_prompt(base_prompt: Callable[..., str]) -> Callable[..., str]:
    def layered_prompt(contract: dict[str, Any], current_memory: dict[str, Any], draft: str) -> str:
        return base_prompt(contract, current_memory, draft) + graph_prompt_suffix(current_memory)

    return layered_prompt


def _dict_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def wrap_normalizer(base_normalizer: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    def normalize(result: dict[str, Any], chapter: dict[str, Any]) -> dict[str, Any]:
        memory = base_normalizer(result, chapter)
        structured = result.get("structured") if isinstance(result.get("structured"), dict) else {}
        memory.update(
            {
                "story_thread_changes": _dict_items(structured.get("story_thread_changes")),
                "story_node_changes": _dict_items(structured.get("story_node_changes")),
                "story_edge_changes": _dict_items(structured.get("story_edge_changes")),
                "story_progress": _dict_items(structured.get("story_progress")),
            }
        )
        return memory

    return normalize


def wrap_persist_compiled_memory(base_persist: Callable[..., None]) -> Callable[..., None]:
    def persist(conn, step: dict[str, Any], memory: dict[str, Any], *, model: str = "") -> None:
        base_persist(conn, step, memory, model=model)
        persist_story_graph_layers(conn, step, memory)

    return persist


def wrap_draft_prompt(base_prompt: Callable[..., str]) -> Callable[..., str]:
    def prompt(contract: dict[str, Any], chapter_number: int) -> str:
        graph = {
            "story_focus": contract.get("story_focus", []),
            "story_threads": contract.get("story_threads", []),
            "story_nodes": contract.get("story_nodes", []),
            "story_edges": contract.get("story_edges", []),
            "stalled_threads": contract.get("stalled_threads", []),
        }
        return (
            base_prompt(contract, chapter_number)
            + "\n\n以下剧情图谱用于控制多条线的并行推进。优先推进 story_focus 中的线程；"
            "本章不必平均照顾全部线程，但不能把已完成节点重新当成首次事件。"
            "如果线程处于 blocked，正文必须尊重其阻碍；如果线程已 resolved，不得无理由重新打开。"
            f"\n剧情图谱约束：{json_text(graph)}"
        )

    return prompt
