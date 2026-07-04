"""Application: autopilot story asset preparation.

This module prepares the connected assets needed by hosted novel generation:
outline -> characters -> relationships -> emotional constraints -> llmwiki pages.
It is intentionally deterministic as a safe fallback, while still leaving the
records editable in the workbench and reusable by model-driven workflows.
"""
from __future__ import annotations

import json
from typing import Any

from .memory_service import (
    create_structured_record,
    list_records_for_context,
    record_payload,
    upsert_wiki_page,
)
from ..workflows.generation import CHARACTER_STUBS


def prepare_autopilot_story_assets(
    project_id: str,
    project: dict[str, Any],
    start_chapter: int,
    count: int,
) -> dict[str, Any]:
    """Prepare all linked story assets for one-click hosted generation.

    The preparation order is deliberate:
    1. story-level workflow notes in llmwiki
    2. characters
    3. relationships + canvas graph
    4. chapter outlines
    5. emotional automation constraints
    6. prompt-skill records and safety rules
    """
    count = max(1, int(count or 1))
    start_chapter = max(1, int(start_chapter or 1))
    characters = ensure_characters(project_id, project)
    relationships = ensure_relationships(project_id, characters)
    outlines = ensure_chapter_outlines(project_id, project, characters, start_chapter, count)
    emotional_system = ensure_emotional_system(project_id, project)
    prompt_skills = ensure_prompt_skills(project_id)
    taboo_rules = ensure_taboo_rules(project_id)
    canvas = sync_relationship_canvas(project_id)
    workflow_page = sync_autopilot_workflow_wiki(project_id, project, start_chapter, count)

    return {
        "characters": len(characters),
        "relationships": len(relationships),
        "outlines": len(outlines),
        "emotional_system": emotional_system,
        "prompt_skills": len(prompt_skills),
        "taboo_rules": len(taboo_rules),
        "relationship_canvas": canvas,
        "workflow_page": workflow_page,
    }


def ensure_characters(project_id: str, project: dict[str, Any]) -> list[dict[str, Any]]:
    existing = list_records_for_context(project_id, "character-profiles", 100)
    if existing:
        return existing

    title = project.get("title") or "未命名小说"
    theme = _story_theme(project)
    created: list[dict[str, Any]] = []
    for index, stub in enumerate(CHARACTER_STUBS[:4]):
        payload = {
            **stub,
            "function": ["叙事发动机", "关系张力", "信息钥匙", "价值观压力"][index],
            "emotional_wound": _character_wound(index, theme),
            "emotional_need": _character_need(index, theme),
            "memory_role": "必须写入 llmwiki，用于后续章节保持动机、声纹和关系连续性。",
            "notes": f"{stub.get('notes', '')} 自动托管生成准备于《{title}》：{theme}",
        }
        created.append(
            create_structured_record(
                project_id=project_id,
                resource="character-profiles",
                title=payload["name"],
                category=payload.get("role", "角色"),
                content=(
                    f"{payload['name']}承担{payload['function']}。"
                    f"外在目标：{payload.get('desire', '')}；内在伤口：{payload['emotional_wound']}。"
                ),
                payload=payload,
                status="active",
            )
        )
    return created


def ensure_relationships(project_id: str, characters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = list_records_for_context(project_id, "character-relationships", 100)
    if existing:
        return existing
    names = [_record_name(character) for character in characters]
    names = [name for name in names if name]
    if len(names) < 2:
        return existing

    templates = [
        (names[0], names[1], "隐秘同盟", 7, "彼此需要，却都不愿完全交出底牌。"),
        (names[0], names[2] if len(names) > 2 else names[1], "信息互补", 6, "一方保存事实，一方承担行动后果。"),
        (names[0], names[3] if len(names) > 3 else names[1], "追捕 / 对手", 8, "价值观冲突强，后期可能转为临时合作。"),
    ]
    created: list[dict[str, Any]] = []
    for source, target, relation_type, strength, conflict in templates:
        title = f"{source} ↔ {target}"
        payload = {
            "name": title,
            "from": source,
            "to": target,
            "source_character": source,
            "target_character": target,
            "type": relation_type,
            "relationship_type": relation_type,
            "relation": relation_type,
            "strength": strength,
            "conflict": conflict,
            "change_history": "托管生成时由章节衔接包和时间线持续更新。",
            "related_chapters": "全书",
            "description": conflict,
        }
        created.append(
            create_structured_record(
                project_id=project_id,
                resource="character-relationships",
                title=title,
                category=relation_type,
                content=conflict,
                payload=payload,
                status="active",
            )
        )
    return created


def ensure_chapter_outlines(
    project_id: str,
    project: dict[str, Any],
    characters: list[dict[str, Any]],
    start_chapter: int,
    count: int,
) -> list[dict[str, Any]]:
    existing = list_records_for_context(project_id, "outlines", 500)
    by_number = {
        str(record_payload(record).get("chapter_number") or ""): record
        for record in existing
        if record_payload(record).get("chapter_number")
    }
    protagonist = _record_name(characters[0]) if characters else "主角"
    title = project.get("title") or "未命名小说"
    theme = _story_theme(project)
    end_chapter = start_chapter + count - 1
    created_or_existing: list[dict[str, Any]] = []
    for chapter_number in range(start_chapter, end_chapter + 1):
        key = str(chapter_number)
        if key in by_number:
            created_or_existing.append(by_number[key])
            continue
        stage = _chapter_stage(chapter_number, start_chapter, end_chapter)
        chapter_title = f"第 {chapter_number} 章 · {stage['title']}"
        goal = f"{stage['goal']}；围绕《{title}》的核心主题“{theme}”推进一层，不重复前章事件。"
        payload = {
            "volume": "第一卷",
            "chapter_number": str(chapter_number),
            "chapter_title": chapter_title,
            "chapter_goal": goal,
            "main_conflict": f"{protagonist}必须推进本章目标，但会付出一项情感或关系代价。",
            "key_events": stage["events"],
            "emotional_rhythm": stage["emotion"],
            "foreshadowing": stage["foreshadowing"],
            "hook": "终章完成主要冲突收束。" if chapter_number == end_chapter else "章末生成衔接包，明确下一章必须承接的状态、钩子和情感余波。",
            "related_characters": "、".join(_record_name(c) for c in characters[:4] if _record_name(c)),
            "completion_status": "draft",
        }
        created_or_existing.append(
            create_structured_record(
                project_id=project_id,
                resource="outlines",
                title=chapter_title,
                category="chapter_outline",
                content=goal,
                payload=payload,
                status="active",
            )
        )
    return created_or_existing


def ensure_emotional_system(project_id: str, project: dict[str, Any]) -> dict[str, Any]:
    existing = [r for r in list_records_for_context(project_id, "style-profiles", 100) if r.get("title") == "情感托管约束"]
    if existing:
        return existing[0]
    theme = _story_theme(project)
    payload = {
        "name": "情感托管约束",
        "core": "情感表达不依赖用户手动说明，由托管流程自动生成情感种子、考古、加深和藏回。",
        "theme": theme,
        "rules": [
            "正文先写动作、场景和选择，再让读者感到情绪。",
            "禁止把情绪解释成口号，优先使用身体反应、物象、沉默和未说出口的话。",
            "每章至少留下一个可追踪的情感余波，并写入章节衔接包。",
            "下一章开头必须承接上一章衔接包中的 ending_state、emotional_residue 和 open_hooks。",
        ],
    }
    return create_structured_record(
        project_id=project_id,
        resource="style-profiles",
        title="情感托管约束",
        category="autopilot-emotion",
        content="托管生成时自动执行：情感种子 → 情感考古 → 加深藏回 → 章节衔接包。",
        payload=payload,
        status="active",
    )


def ensure_prompt_skills(project_id: str) -> list[dict[str, Any]]:
    existing = list_records_for_context(project_id, "prompt-templates", 100)
    existing_titles = {r.get("title") for r in existing}
    skill_specs = [
        (
            "skill/故事资产生成",
            "先生成总纲，再生成角色、关系、章节大纲，并同步到 llmwiki。所有资产必须有交叉引用。",
        ),
        (
            "skill/情感托管生成",
            "用户不需要逐章说明情绪。每章自动生成情感种子，正文后做情感考古，再执行加深藏回。",
        ),
        (
            "skill/章节衔接记忆",
            "每章定稿后生成衔接包，记录末尾状态、未决钩子、情感余波、已揭示信息和下一章种子。",
        ),
        (
            "skill/llmwiki 自动记忆",
            "所有角色、关系、大纲、章节正文、章节衔接包、时间线和关键记忆都要进入 llmwiki。",
        ),
    ]
    created_or_existing = list(existing)
    for title, content in skill_specs:
        if title in existing_titles:
            continue
        created_or_existing.append(
            create_structured_record(
                project_id=project_id,
                resource="prompt-templates",
                title=title,
                category="autopilot-skill",
                content=content,
                payload={"trigger": title, "instruction": content, "enabled": True},
                status="active",
            )
        )
    return created_or_existing


def ensure_taboo_rules(project_id: str) -> list[dict[str, Any]]:
    existing = list_records_for_context(project_id, "taboo-rules", 100)
    existing_titles = {r.get("title") for r in existing}
    specs = [
        ("禁止烂尾式结局", "终章必须回收主线冲突，不得只抛出下一章钩子或写成未完待续。"),
        ("禁止情绪直白说明", "避免用“他很悲伤/她很痛苦”替代场景、动作和选择。"),
        ("禁止章节断裂", "新章节开头必须承接上一章衔接包，不得突然跳场。"),
    ]
    created_or_existing = list(existing)
    for title, content in specs:
        if title in existing_titles:
            continue
        created_or_existing.append(
            create_structured_record(
                project_id=project_id,
                resource="taboo-rules",
                title=title,
                category="全书",
                content=content,
                payload={"severity": "high", "scope": "全书"},
                status="active",
            )
        )
    return created_or_existing


def sync_relationship_canvas(project_id: str) -> dict[str, Any]:
    characters = list_records_for_context(project_id, "character-profiles", 100)
    relationships = list_records_for_context(project_id, "character-relationships", 200)
    nodes = []
    for record in characters:
        payload = record_payload(record)
        name = payload.get("name") or record.get("title") or "未命名角色"
        nodes.append({"id": name, "name": name, "role": payload.get("role") or record.get("category") or "角色"})
    links = []
    for record in relationships:
        payload = record_payload(record)
        source = payload.get("from") or payload.get("source_character") or ""
        target = payload.get("to") or payload.get("target_character") or ""
        if not source or not target:
            continue
        links.append({
            "source": source,
            "target": target,
            "type": payload.get("type") or payload.get("relationship_type") or record.get("category") or "关系",
            "strength": payload.get("strength") or 5,
            "conflict": payload.get("conflict") or record.get("content") or "",
        })
    mermaid_lines = ["graph LR"]
    for link in links:
        mermaid_lines.append(f"    { _mermaid_id(link['source']) }[{link['source']}] -- {link['type']} --> { _mermaid_id(link['target']) }[{link['target']}]")
    content = "\n".join([
        "# 角色关系画布",
        "",
        "这个页面由托管生成流程自动维护。前端的角色关系图也会读取同一批角色与关系记录。",
        "",
        "## Mermaid 画布",
        "",
        "```mermaid",
        *(mermaid_lines or ["graph LR"]),
        "```",
        "",
        "## Graph JSON",
        "",
        "```json",
        json.dumps({"nodes": nodes, "links": links}, ensure_ascii=False, indent=2),
        "```",
        "",
    ])
    return upsert_wiki_page(project_id, "relationships/canvas.md", content)


def sync_autopilot_workflow_wiki(project_id: str, project: dict[str, Any], start_chapter: int, count: int) -> dict[str, Any]:
    title = project.get("title") or "未命名小说"
    content = f"""# 托管生成流程

项目：{title}

## 自动化顺序

1. 生成或补齐总纲 / 章节大纲。
2. 生成角色档案，并写入 `characters.md` 与单角色页面。
3. 生成角色关系，并同步 `relationships/canvas.md` 作为关系画布数据源。
4. 写入“情感托管约束”，后续章节自动执行情感种子、情感考古、加深藏回。
5. 托管生成第 {start_chapter} 章到第 {start_chapter + count - 1} 章。
6. 每章定稿后写入章节全文、时间线、关键记忆和章节衔接包。
7. 下一章生成时读取上一章衔接包，承接末尾状态、情感余波和未决钩子。

## 连续性规则

- 先有大纲，再有角色与关系，再开始正文。
- 角色关系不是孤立记录，必须参与大纲、正文和章节衔接包。
- 情感表达由托管流程自动完成，用户不需要逐章描述人物应该怎么难过或怎么纠结。
- 每章结尾的衔接包是下一章的硬约束，防止章节断裂。
"""
    return upsert_wiki_page(project_id, "autopilot/workflow.md", content)


def _story_theme(project: dict[str, Any]) -> str:
    return str(
        project.get("logline")
        or project.get("topic")
        or project.get("synopsis")
        or "一个人在目标、代价和关系之间做出选择"
    )


def _record_name(record: dict[str, Any]) -> str:
    payload = record_payload(record)
    return str(payload.get("name") or record.get("title") or "").strip()


def _character_wound(index: int, theme: str) -> str:
    wounds = [
        f"害怕自己推进{theme}时失去重要关系",
        "害怕信任再次被利用",
        "害怕知道真相却没有能力保存它",
        "害怕秩序本身只是另一种谎言",
    ]
    return wounds[min(index, len(wounds) - 1)]


def _character_need(index: int, theme: str) -> str:
    needs = [
        f"承认自己不是只为{theme}而存在，也需要被理解",
        "学会把保护从控制变成坦白",
        "从记录者变成行动者",
        "从维护规则转向承担真相",
    ]
    return needs[min(index, len(needs) - 1)]


def _chapter_stage(chapter_number: int, start: int, end: int) -> dict[str, str]:
    total = max(1, end - start + 1)
    pos = (chapter_number - start) / max(1, total - 1)
    if chapter_number == start:
        return {
            "title": "入口与第一道裂缝",
            "goal": "建立主角目标、核心异常、第一组关系张力",
            "events": "主角进入核心场景；发现异常；与关键角色发生第一次有效碰撞。",
            "emotion": "压抑开场 → 疑问升高 → 结尾留下不安。",
            "foreshadowing": "埋下终章会回收的物件、句子或选择。",
        }
    if chapter_number == end:
        return {
            "title": "代价落地",
            "goal": "回收主线冲突、完成情感债务结算、给出明确收束",
            "events": "主角完成最终选择；主要伏笔回收；关系状态落地。",
            "emotion": "紧绷 → 坦白/失去 → 清醒收束。",
            "foreshadowing": "不再新增主线伏笔，只回收关键伏笔。",
        }
    if pos < 0.34:
        return {
            "title": "线索外溢",
            "goal": "扩展线索范围，让角色关系产生第一轮真实变化",
            "events": "线索扩大；同盟出现裂痕；反派或压力源显形。",
            "emotion": "困惑 → 逼近 → 被迫做小选择。",
            "foreshadowing": "埋下关系反转或信任危机的前兆。",
        }
    if pos < 0.67:
        return {
            "title": "中段反噬",
            "goal": "让前面获得的线索反过来伤害主角或关系",
            "events": "已知信息被重新解释；角色做出会留下债务的决定。",
            "emotion": "短暂确定 → 失控 → 沉默或误解。",
            "foreshadowing": "提示真正的代价不是外部失败，而是关系与自我认知的改变。",
        }
    return {
        "title": "低谷与选择",
        "goal": "把外部冲突推向低谷，逼出角色真正想保护的东西",
        "events": "主角失去一个安全选项；关系进入不可回避的坦白或决裂。",
        "emotion": "压抑 → 爆发边缘 → 做出不可撤回的选择。",
        "foreshadowing": "准备终章回收的关键证据或情感答案。",
    }


def _mermaid_id(value: str) -> str:
    return "N" + "".join(str(ord(ch)) for ch in value)[:18]
