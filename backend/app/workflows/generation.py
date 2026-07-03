"""工作流层 · 生成类工作流逻辑。

从 main.py 迁出，包含：
- 工作流前置校验
- 角色存根数据（CHARACTER_STUBS）
- 结构化输出 stub（structured_output_for_workflow）
- 本地草稿生成（build_local_chapter_draft）
- stub 输出封装（build_stub_ai_output）
- AI 文本解析（parse_structured_ai_text）
- 各类辅助函数（章节标题清洗、主角名提取、大纲聚焦等）
"""
import json
import re
from typing import Any

from fastapi import HTTPException

from ..domain.models import AiWorkflowIn


# ---------------------------------------------------------------------------
# 工作流前置校验
# ---------------------------------------------------------------------------
def validate_workflow_prerequisites(workflow: str, context: dict[str, Any]) -> None:
    if workflow != "generate_chapter_draft":
        return
    missing: list[str] = []
    if not context.get("characters"):
        missing.append("先生成并保存角色")
    if not context.get("outlines"):
        missing.append("再生成并保存大纲")
    if missing:
        detail = "生成正文前需要按顺序准备素材：" + "，".join(missing) + "。"
        raise HTTPException(status_code=409, detail=detail)


# ---------------------------------------------------------------------------
# 角色存根数据
# ---------------------------------------------------------------------------
CHARACTER_STUBS: list[dict[str, str]] = [
    {
        "name": "沈照夜",
        "role": "前朝公主",
        "faction": "流亡旧臣",
        "appearance": "二十岁上下，常穿素色斗篷，眼神克制。",
        "traits": "冷静、警惕、重诺",
        "desire": "夺回被篡改的记忆与王朝真相",
        "fear": "再次失去重要之人的记忆",
        "mainline_relation": "围绕改写记忆古籍推进主线",
        "arc": "从被动流亡到主动承担改写历史的代价",
        "voice": "短句、克制、少用感叹",
        "related_chapters": "",
        "notes": "核心主角，可承接记忆古籍主线。",
    },
    {
        "name": "顾临舟",
        "role": "旧朝密探",
        "faction": "流亡情报网",
        "appearance": "三十岁左右，常戴灰色手套，左眼下有旧疤。",
        "traits": "谨慎、讽刺、守口如瓶",
        "desire": "找出出卖旧朝密档的人",
        "fear": "自己保护的人再次成为牺牲品",
        "mainline_relation": "掌握古籍上一次现世的线索，推动主角接近幕后势力。",
        "arc": "从只交换情报到愿意暴露身份保护同伴",
        "voice": "话少，常用反问和冷幽默试探对方。",
        "related_chapters": "",
        "notes": "用于补足情报线和行动线。",
    },
    {
        "name": "苏晚",
        "role": "禁书馆抄录员",
        "faction": "市立旧书馆",
        "appearance": "身形单薄，袖口常有墨渍，随身带铜边笔记本。",
        "traits": "敏锐、胆小但不懦弱、记忆力惊人",
        "desire": "证明禁书馆失踪案不是意外",
        "fear": "被人发现她能记住被改写前的片段",
        "mainline_relation": "能察觉记忆改写后的缝隙，帮助主角校验真相。",
        "arc": "从旁观记录者成长为主动保存真相的人",
        "voice": "语速快，细节多，紧张时会重复关键词。",
        "related_chapters": "",
        "notes": "适合承担知识库、记忆校验和悬疑线索。",
    },
    {
        "name": "谢无咎",
        "role": "现朝监察使",
        "faction": "监察司",
        "appearance": "黑衣金扣，站姿端正，目光像审讯灯。",
        "traits": "强势、克制、相信秩序",
        "desire": "阻止古籍造成更大范围的记忆污染",
        "fear": "秩序只是另一种被编造的谎言",
        "mainline_relation": "与主角立场相冲，却可能在关键章节成为临时同盟。",
        "arc": "从追捕者转为共同承担真相代价的见证者",
        "voice": "句子规整，不轻易承诺，一旦承诺必执行。",
        "related_chapters": "",
        "notes": "适合制造外部压力和价值观冲突。",
    },
]


def collect_existing_character_names(payload: AiWorkflowIn, context: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    extra = getattr(payload, "model_extra", {}) or {}
    for name in extra.get("existing_character_names") or []:
        if isinstance(name, str) and name.strip():
            names.add(name.strip())
    for record in extra.get("existing_characters") or []:
        if not isinstance(record, dict):
            continue
        record_payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        name = record_payload.get("name") or record.get("title")
        if isinstance(name, str) and name.strip():
            names.add(name.strip())
    for record in context.get("characters") or []:
        if not isinstance(record, dict):
            continue
        record_payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        name = record_payload.get("name") or record.get("title")
        if isinstance(name, str) and name.strip():
            names.add(name.strip())
    return names


def character_stub_for_payload(payload: AiWorkflowIn, context: dict[str, Any]) -> dict[str, str]:
    existing_names = collect_existing_character_names(payload, context)
    character = next((item for item in CHARACTER_STUBS if item["name"] not in existing_names), CHARACTER_STUBS[-1])
    return {
        **character,
        "notes": f"{character['notes']} 根据提示生成：{payload.prompt or '新角色'}",
    }


# ---------------------------------------------------------------------------
# 结构化输出 stub
# ---------------------------------------------------------------------------
def structured_output_for_workflow(workflow: str, payload: AiWorkflowIn, context: dict[str, Any]) -> Any:
    if workflow == "generate_characters":
        return character_stub_for_payload(payload, context)
    if workflow in {"generate_outline", "generate_chapter_brief"}:
        chapter = context.get("chapter") or {}
        chapter_number = int(chapter.get("chapter_number") or 0)
        title = clean_chapter_title(chapter)
        focus = title or payload.prompt or "记忆古籍"
        protagonist = primary_character_name(context)
        generation_contract = context.get("generation_contract") if isinstance(context.get("generation_contract"), dict) else {}
        is_final_chapter = bool(generation_contract.get("is_final_chapter") or generation_contract.get("ending_required"))

        # 解析上一章衔接包
        prev_bridge = context.get("prev_chapter_bridge") or {}
        bridge_json = prev_bridge.get("bridge_json")
        if isinstance(bridge_json, str):
            try:
                bridge_json = json.loads(bridge_json)
            except json.JSONDecodeError:
                bridge_json = {}
        if not isinstance(bridge_json, dict):
            bridge_json = {}

        open_hooks = bridge_json.get("open_hooks", []) or []
        unresolved = bridge_json.get("unresolved_tension", "")
        prev_ending = bridge_json.get("ending_state", {})
        prev_location = ""
        prev_situation = ""
        if isinstance(prev_ending, dict):
            prev_location = prev_ending.get("location", "")
            prev_situation = prev_ending.get("situation", "")

        # 根据衔接包构建本章目标
        if open_hooks:
            first_hook = open_hooks[0] if isinstance(open_hooks[0], dict) else {"hook": str(open_hooks[0])}
            hook_text = first_hook.get("hook", focus)
            chapter_goal = f"承接上一章（{prev_location or '前文'}）的{prev_situation or '压力'}，推进{hook_text}的后续。"
            main_conflict = f"{protagonist}必须面对{hook_text}带来的直接后果，同时{unresolved or '暗处的对手也在调整布局'}。"
        else:
            arc = local_arc_for_chapter(chapter_number or 1)
            chapter_goal = f"围绕{focus}推进主线，并承接{arc}"
            main_conflict = f"{protagonist}必须追查{focus}，但每推进一步都会让既有记忆和同盟信任出现缺口。"

        return {
            "volume": "第一卷",
            "chapter_title": chapter.get("title") or f"第 {chapter_number or '?'} 章 · {focus}",
            "chapter_goal": chapter_goal,
            "main_conflict": main_conflict,
            "key_events": (
                f"{protagonist}在{focus}中取得本章独有线索；"
                f"线索触发与第 {chapter_number or '?'} 章阶段目标相关的新阻碍；"
                "角色做出会改变后续关系的选择；"
                + (
                    f"结尾回收{focus}的主要后果，给出明确收束。"
                    if is_final_chapter
                    else f"结尾把{focus}的后果留到下一章继续偿还。"
                )
            ),
            "emotional_rhythm": f"以承接上一章余波开场（{bridge_json.get('unresolved_tension', '压抑') if bridge_json else '不安'}），中段升高外部压力，结尾留下具体代价。",
            "foreshadowing": f"{focus}背后的代价尚未完全揭示，但已经影响后续走向",
            "hook": (
                f"{protagonist}确认{focus}的核心代价，并让本卷主要冲突落地。"
                if is_final_chapter
                else f"{protagonist}发现{focus}留下的痕迹指向一个更早被抹去的决定。"
            ),
            "related_characters": protagonist,
            "completion_status": "草稿",
        }
    if workflow == "extract_timeline_events":
        return [
            {
                "event_time": "当前章节",
                "chapter": (context.get("chapter") or {}).get("title") or "",
                "characters": "主角",
                "cause": payload.content or payload.prompt,
                "status": "待确认",
            }
        ]
    if workflow == "check_taboo_rules":
        return {"risk_level": "低", "issues": [], "suggestion": "未发现明显雷点，可继续人工复核。"}

    # ===== 情感深度增强 v4 stubs（五层分析 + 对话潜台词 + 追读力 + Anti-AI）=====
    if workflow == "generate_emotion_seed":
        return {
            "emotion_seed": {
                "core_tension": "一个人在被需要和被看见之间的裂缝",
                "scene_temperature": "湿冷的等待，时间在流走",
                "open_question": "她留下来的理由，是责任还是恐惧？",
            }
        }
    if workflow == "emotion_archaeology":
        # v4 升级：三视角 + 五层分析
        return {
            "layer_analysis": {
                "surface": {
                    "text": "她擦了三遍桌子，把抹布叠成方形",
                    "status": "presented",
                    "advice": "",
                },
                "emotional": {
                    "text": "手指是机械的",
                    "status": "too_explicit",
                    "advice": "过于直白，建议藏回：删掉此句，让动作本身的机械感传递麻木",
                },
                "intention": {
                    "text": "（未说出）如果那时拦了他一下",
                    "status": "missing",
                    "advice": "可通过一个不相关的动作泄露：如她突然停下手，看了一眼门口，然后继续擦桌子",
                },
                "subconscious": {
                    "text": "用'还有用'证明自己有资格留下",
                    "status": "can_deepen",
                    "advice": "可加深：让她在擦桌子时特意把某个有用的东西摆正",
                },
                "resonance": {
                    "text": "留下/被需要——全书母题",
                    "status": "touched",
                    "advice": "已触及但浮在表面，可再压深：不要点明，让读者自己感到",
                },
            },
            "subconscious_leads": [
                {
                    "position": "第2段",
                    "detail": "擦三遍桌子",
                    "inferred": "用控制小动作压抑失控感",
                    "why": "重复是过度的，整齐是控制欲的投射",
                    "depth": "can_deepen",
                },
                {
                    "position": "第5段",
                    "detail": "没接话",
                    "inferred": "回避承认自己需要被需要",
                    "why": "沉默比回答更说明问题",
                    "depth": "can_deepen",
                },
            ],
            "reader_felt_map": {
                "resonance_points": [
                    {"position": "第3段末", "felt": "隐隐心疼", "why": "动作太整齐了，整齐得像在撑着"}
                ],
                "rupture_points": [
                    {"position": "第6段", "issue": "该动但没动，情绪转折太突然"}
                ],
                "silence_points": [
                    {"position": "第4段", "note": "好的留白，读者会停一下但不知道为什么——不要动"}
                ],
            },
            "motif_echoes": {
                "existing_motifs": [
                    {"motif": "留下/被需要", "chapter_touch": "第5段触及但浮在表面", "can_deepen": True}
                ],
                "new_seeds": [
                    {"image": "方形", "first_appearance": True, "potential": "可能长成控制欲的象征"}
                ],
                "open_knots": [
                    {"knot": "她留下来的理由", "chapter_bumped": True, "resolved": False}
                ],
            },
            "deepen_opportunities": [
                "第2段的'擦三遍'已经是好种子，可以再压深——不要加字，反而删一个解释性的词",
                "第5段的回避可以藏得更深——让她的回避看起来像别的理由",
                "第6段断裂处不需要补情绪，需要在前面多留一个伏笔",
            ],
        }
    if workflow == "dialogue_subtext_excavation":
        # v4 新增：对话潜台词四层挖掘
        return {
            "dialogue_map": [
                {
                    "position": "第3段",
                    "speaker": "守夜人",
                    "line": "你找到想要的了吗？",
                    "layers": {
                        "surface": "你找到想要的了吗？",
                        "tone": "声音压得很低（已呈现）",
                        "unsaid": "他知道她找不到，也不是真的在问",
                        "motive_leak": "试探她是否已经接近真相",
                    },
                    "issues": [],
                    "subtext": "试探",
                    "emotional_debt": "守夜人隐瞒了关键信息",
                    "fix_direction": "无需修改",
                },
                {
                    "position": "第4段",
                    "speaker": "主角",
                    "line": "还没有。",
                    "layers": {
                        "surface": "还没有。",
                        "tone": "（缺失）",
                        "unsaid": "她其实找到了，但不想让他知道",
                        "motive_leak": "自我保护——不暴露弱点",
                    },
                    "issues": ["missing_tone"],
                    "subtext": "隐瞒",
                    "emotional_debt": "主角对守夜人的不信任在累积",
                    "fix_direction": "补语气层：加一个动作，如'她没有回头'或'她把抽屉推回去'",
                },
                {
                    "position": "第5段",
                    "speaker": "主角",
                    "line": "那它们为什么在我的抽屉里？",
                    "layers": {
                        "surface": "那它们为什么在我的抽屉里？",
                        "tone": "转过身，看着他（已呈现）",
                        "unsaid": "（无——潜台词被说破了）",
                        "motive_leak": "直接质问",
                    },
                    "issues": ["said_subtext"],
                    "subtext": "质问（已说破）",
                    "emotional_debt": "",
                    "fix_direction": "藏回：把直接质问改为通过动作泄露——如把抽屉里的东西推到他面前，不说话",
                },
            ],
            "summary": {
                "total_dialogues": 3,
                "issues_found": {"said_subtext": 1, "missing_tone": 1, "voice_mismatch": 0, "rhythm_flat": 0},
                "emotional_debt_accumulated": 2,
            },
        }
    if workflow == "analyze_reader_pull":
        # v4 新增：追读力分析
        return {
            "hook": {
                "type": "emotional",
                "strength": 7,
                "description": "她在等一个她还没想清楚的决定——情感悬念比情节悬念更抓人",
            },
            "emotional_debt": {
                "new": [
                    {"character": "主角", "debt": "对守夜人的不信任", "source": "第4段隐瞒"},
                    {"character": "主角", "debt": "未表达的需要", "source": "第5段质问"},
                ],
                "paid": [],
                "suspended": [
                    {"character": "主角", "debt": "她留下来的理由", "since": "第1章"},
                ],
            },
            "payoff_assessment": {
                "should_erupt": False,
                "erupted": False,
                "premature": False,
                "note": "本章是积压章，不需要兑现，债务在正常累积",
            },
            "pull_score": 7,
            "advice": "追读力良好。情感钩子已建立（未想清楚的决定）。建议下一章给一个微光（情感微推进），不要急着兑现。",
        }
    if workflow == "deepen_and_bury":
        # v4 升级：融合三份产出的加深
        content = payload.content or ""
        if not content:
            content = "雨声落在档案柜上，主角把纸页压平，终于看清名单背后被刮掉的旧签名。"
        # 模拟做减法：删掉一些解释性词语
        revised = content
        for phrase in ["她心中一阵酸楚", "不禁", "缓缓", "涌上心头", "一丝"]:
            revised = revised.replace(phrase, "")
        return {
            "revised_text": revised,
            "changes": [
                {
                    "position": "第2段",
                    "before": "她在发麻。手指是机械的。",
                    "after": "（删掉'她在发麻'，只留动作）",
                    "reason": "做减法：删掉解释性词语，让动作本身的机械感传递麻木",
                    "type": "deepen",
                },
                {
                    "position": "第5段",
                    "before": "如果那时拦了他一下。哪怕只是喊一声。",
                    "after": "她突然停下手，看了一眼门口，然后继续擦桌子。",
                    "reason": "藏回：把说破的潜台词改为通过动作泄露",
                    "type": "bury",
                },
                {
                    "position": "第6段",
                    "before": "（无需修改）",
                    "after": "（保留留白）",
                    "reason": "留白：silence_points 不要动",
                    "type": "leave",
                },
            ],
            "word_count_before": len(content),
            "word_count_after": len(revised),
            "subtraction_ratio": round(1 - len(revised) / max(len(content), 1), 2),
        }
    if workflow == "anti_ai_polish":
        # v4 新增：Anti-AI 终检
        content = payload.content or ""
        cliche_hits = []
        ai_cliches = ["不禁", "缓缓", "一丝", "涌上心头", "嘴角上扬", "眼中闪过", "深吸一口气", "默默无言", "心中一动"]
        for cliche in ai_cliches:
            if cliche in content:
                cliche_hits.append(cliche)
        # 模拟做减法
        revised = content
        for cliche in cliche_hits:
            revised = revised.replace(cliche, "")
        return {
            "revised_text": revised,
            "cliche_count": len(cliche_hits),
            "cliche_hits": cliche_hits,
            "over_explain_count": 0,
            "over_explains": [],
            "summary": f"扫描到 {len(cliche_hits)} 处 AI 套路表达，已做减法删除。过度解释性语句 0 处。",
        }
    if workflow == "trace_image_growth":
        return {
            "tracked_images": [
                {"image": "雨声", "is_new": True, "chapter_number": 1, "context": "档案室外的雨声反复出现", "felt_meaning_hint": ""}
            ]
        }
    if workflow == "retrospect_deepen":
        return {
            "revised_text": "她回头重读那一页，才明白自己早已在第一场雨里错过答案。",
            "changes": [{"position": "第2段", "before": "原句过于直白", "after": "改为动作和物象承载情绪", "reason": "回溯加深"}],
            "lead_id": payload.payload.get("lead_id", ""),
        }
    if workflow == "generate_chapter_bridge":
        chapter = context.get("chapter") or {}
        generation_contract = context.get("generation_contract") if isinstance(context.get("generation_contract"), dict) else {}
        if generation_contract.get("is_final_chapter") or generation_contract.get("ending_required"):
            return {
                "ending_state": {
                    "time": "终章夜明",
                    "location": "灰塔出口",
                    "characters_present": "主角、见证者",
                    "situation": "核心冲突已结算，角色带着代价离开",
                    "last_action": "主角合上档案，把名字留在纸上",
                },
                "open_hooks": [],
                "emotional_residue": [
                    {"character": "主角", "emotion": "疲惫但清醒", "intensity": 5, "physical": "掌心仍有纸页压痕"},
                ],
                "info_revealed": ["停摆的根源已经确认"],
                "info_withheld": [],
                "next_chapter_seeds": [],
                "unresolved_tension": "",
                "_chapter_id": chapter.get("id", ""),
                "_chapter_number": chapter.get("chapter_number", 0),
            }
        return {
            "ending_state": {
                "time": "深夜",
                "location": "档案层入口",
                "characters_present": "主角、守夜人",
                "situation": "主角刚发现关键线索，守夜人在门外",
                "last_action": "她把抽屉推回去，没有关上",
            },
            "open_hooks": [
                {"hook": "签名被篡改的真相", "urgency": "高"},
                {"hook": "守夜人的真实身份", "urgency": "中"},
            ],
            "emotional_residue": [
                {"character": "主角", "emotion": "压抑的愤怒", "intensity": 7, "physical": "手指发麻"},
            ],
            "info_revealed": ["签名与原件不符"],
            "info_withheld": ["谁篡改了签名"],
            "next_chapter_seeds": ["主角离开时会遇到关键见证者"],
            "unresolved_tension": "她需要盟友但不敢信任任何人",
            "_chapter_id": chapter.get("id", ""),
            "_chapter_number": chapter.get("chapter_number", 0),
        }
    return None


# ---------------------------------------------------------------------------
# 长篇弧线 + 章节辅助函数
# ---------------------------------------------------------------------------
LONG_FORM_ARCS = [
    "开端卷：建立主角目标、核心代价和第一批关键同盟。",
    "扩展卷：让线索外溢到更大的城市系统，旧胜利开始反噬。",
    "中段卷：揭示敌我双方都在利用同一套记忆规则。",
    "低谷卷：主角为保住同伴主动承担更沉重的遗忘。",
    "收束卷：所有伏笔回到主线，真相、代价和选择同时结算。",
]


def local_arc_for_chapter(chapter_number: int) -> str:
    index = min(len(LONG_FORM_ARCS) - 1, max(0, (chapter_number - 1) // 20))
    return LONG_FORM_ARCS[index]


def clean_chapter_title(chapter: dict[str, Any]) -> str:
    chapter_number = chapter.get("chapter_number") or 0
    raw_title = str(chapter.get("title") or f"第 {chapter_number} 章")
    prefixes = [
        f"第{chapter_number}章",
        f"第 {chapter_number} 章",
        f"第{chapter_number} 章",
        f"第 {chapter_number}章",
    ]
    for prefix in prefixes:
        if raw_title.startswith(prefix):
            return raw_title[len(prefix) :].lstrip(" ·:：-—").strip() or raw_title
    return raw_title


def recent_chapter_line(context: dict[str, Any]) -> str:
    """优先用衔接包描述上一章末尾状态，没有衔接包则退化到摘要。"""
    prev_bridge = context.get("prev_chapter_bridge")
    if isinstance(prev_bridge, dict):
        bridge_json = prev_bridge.get("bridge_json")
        if isinstance(bridge_json, str):
            try:
                bridge_json = json.loads(bridge_json)
            except json.JSONDecodeError:
                bridge_json = {}
        if isinstance(bridge_json, dict):
            ending = bridge_json.get("ending_state", {})
            tension = bridge_json.get("unresolved_tension", "")
            if isinstance(ending, dict) and ending:
                location = ending.get("location", "")
                situation = ending.get("situation", "")
                last_action = ending.get("last_action", "")
                parts = []
                if location:
                    parts.append(f"上一章末尾在{location}")
                if situation:
                    parts.append(situation)
                if last_action:
                    parts.append(f"最后一个动作是{last_action}")
                if tension:
                    parts.append(f"未解的张力：{tension}")
                if parts:
                    return "；".join(parts) + "。"
    # 退化：用摘要
    recent = [item for item in context.get("recent_chapters") or [] if isinstance(item, dict)]
    if not recent:
        return "前文尚未定型，主角只能依靠最初的目标继续向前。"
    latest = sorted(recent, key=lambda item: item.get("chapter_number") or 0, reverse=True)[0]
    title = latest.get("title") or f"第 {latest.get('chapter_number') or '?'} 章"
    summary = latest.get("summary") or latest.get("brief") or "前文留下了未解决的压力。"
    return f"上一章《{title}》留下的后果仍在发酵：{summary}"


def narrative_focus_from_brief(brief: str, title: str) -> str:
    stripped = brief.strip().strip("。")
    outline_markers = ["推进主线", "埋下", "回收", "建立：", "扩展：", "中段：", "低谷：", "收束："]
    if not stripped:
        return f"一份与“{title}”有关的旧档案正在灰塔深处苏醒"
    if any(marker in stripped for marker in outline_markers):
        quoted = re.search(r"“([^”]+)”", stripped)
        focus = quoted.group(1) if quoted else title
        return f"一份与“{focus}”有关的旧档案正在灰塔深处苏醒"
    return stripped


def primary_character_name(context: dict[str, Any]) -> str:
    characters = [item for item in context.get("characters") or [] if isinstance(item, dict)]
    if not characters:
        return "主角"
    for character in characters:
        payload = character.get("payload") if isinstance(character.get("payload"), dict) else {}
        marker_text = " ".join(
            str(value)
            for value in [character.get("category"), character.get("content"), payload.get("role"), payload.get("notes")]
            if value
        )
        if "主角" in marker_text or "protagonist" in marker_text.lower():
            return str(payload.get("name") or character.get("title") or "主角")
    ordered = sorted(characters, key=lambda item: str(item.get("created_at") or item.get("updated_at") or ""))
    payload = ordered[0].get("payload") if isinstance(ordered[0].get("payload"), dict) else {}
    return str(payload.get("name") or ordered[0].get("title") or "主角")


def outline_focus_for_chapter(context: dict[str, Any], chapter_number: int, title: str) -> str:
    outlines = [item for item in context.get("outlines") or [] if isinstance(item, dict)]
    for outline in outlines:
        payload = outline.get("payload") if isinstance(outline.get("payload"), dict) else {}
        if str(payload.get("chapter_number") or "") == str(chapter_number):
            return str(payload.get("chapter_goal") or outline.get("content") or "")
        outline_title = str(payload.get("chapter_title") or outline.get("title") or "")
        if title and title in outline_title:
            return str(payload.get("chapter_goal") or outline.get("content") or "")
    return ""


# ---------------------------------------------------------------------------
# 本地草稿生成
# ---------------------------------------------------------------------------
def build_local_chapter_draft(payload: AiWorkflowIn, context: dict[str, Any]) -> str:
    """本地 stub 正文生成。根据衔接包和情感种子动态生成，不再硬编码。"""
    chapter = context.get("chapter") if isinstance(context.get("chapter"), dict) else {}
    generation_contract = context.get("generation_contract") if isinstance(context.get("generation_contract"), dict) else {}
    is_final_chapter = bool(generation_contract.get("is_final_chapter") or generation_contract.get("ending_required"))
    chapter_number = int(chapter.get("chapter_number") or 1)
    title = clean_chapter_title(chapter)
    protagonist = primary_character_name(context)
    outline_focus = outline_focus_for_chapter(context, chapter_number, title)
    brief = narrative_focus_from_brief(
        str(outline_focus or chapter.get("brief") or payload.prompt or f"{protagonist}继续追查记忆古籍的代价。"),
        title,
    )
    previous = recent_chapter_line(context)

    # 解析衔接包
    prev_bridge = context.get("prev_chapter_bridge") or {}
    bridge_data = prev_bridge.get("bridge_json") if isinstance(prev_bridge.get("bridge_json"), dict) else {}
    if isinstance(prev_bridge.get("bridge_json"), str):
        try:
            bridge_data = json.loads(prev_bridge["bridge_json"])
        except json.JSONDecodeError:
            bridge_data = {}

    ending_state = bridge_data.get("ending_state", {}) if isinstance(bridge_data, dict) else {}
    open_hooks = bridge_data.get("open_hooks", []) if isinstance(bridge_data, dict) else []
    emotional_residue = bridge_data.get("emotional_residue", []) if isinstance(bridge_data, dict) else []

    # 解析情感种子
    emotion_seed = context.get("emotion_seed") or {}
    seed_data = emotion_seed.get("emotion_seed", emotion_seed) if isinstance(emotion_seed, dict) else {}
    if isinstance(emotion_seed, dict) and isinstance(emotion_seed.get("emotion_seed"), dict):
        seed_data = emotion_seed["emotion_seed"]
    core_tension = seed_data.get("core_tension", "一个人在被需要和被看见之间的裂缝") if isinstance(seed_data, dict) else "一个人在被需要和被看见之间的裂缝"
    scene_temperature = seed_data.get("scene_temperature", "湿冷的等待") if isinstance(seed_data, dict) else "湿冷的等待"

    # 根据衔接包决定开场
    if ending_state and isinstance(ending_state, dict):
        prev_location = ending_state.get("location", "上一个场景")
        prev_situation = ending_state.get("situation", "前文留下了未解决的压力")
        prev_action = ending_state.get("last_action", "")
        prev_time = ending_state.get("time", "")
        opening = (
            f"{prev_time}的{prev_location}还留着上一章的气息。{prev_situation}。"
            f"{protagonist}没有立刻离开——{prev_action}这个动作还挂在手上，像没说完的话。"
            f"空气里有种凝固的东西，不是冷，是某种还没落地的预感。"
            f"她把外套的湿袖子往上卷了卷，站在原地多停了三秒。这三秒里，她听见自己的呼吸，"
            f"听见远处管道里水流动的声音，听见这座建筑在夜里的骨架吱呀作响。"
            f"{previous}"
        )
    else:
        # 第一章或无衔接包
        opening = (
            f"{scene_temperature}。{protagonist}站在{title}的入口前，"
            f"知道一旦进去就回不了头。"
            f"她把手贴在墙上，墙面的温度透过掌心传上来——不是冷，是那种老建筑才有的、"
            f"积了很多年的、说不清是什么的凉。她想起上一次站在类似的位置，"
            f"那时候她还有退路。现在没有了。"
            f"{previous}"
        )

    # 根据情感余波决定角色情绪起点
    if emotional_residue and isinstance(emotional_residue, list) and len(emotional_residue) > 0:
        first_residue = emotional_residue[0] if isinstance(emotional_residue[0], dict) else {}
        char_emotion = first_residue.get("emotion", "压抑的不安")
        char_physical = first_residue.get("physical", "")
        emotion_line = (
            f"{first_residue.get('character', protagonist)}的{char_emotion}还没散"
            + (f"，{char_physical}" if char_physical else "")
            + "。她试着活动手指，发现关节比想象中僵硬——不是因为冷，"
            f"是因为她在上一章末尾握了太久的拳头，自己却没察觉。"
            f"这种事后才浮现的身体反应让她意识到，她比表面看起来更在意刚才发生的事。"
        )
    else:
        emotion_line = (
            f"{protagonist}心里压着一团说不清的东西——{core_tension}。"
            f"她分不清这是恐惧还是责任，两种情绪搅在一起，像两根缠住的线，"
            f"她越想拆开越紧。于是她不拆了，把那团东西整个按进胸腔里，"
            f"用呼吸把它压平，像压一张皱了的纸。"
        )

    # 根据未决钩子决定本章推进方向
    if open_hooks and isinstance(open_hooks, list) and len(open_hooks) > 0:
        first_hook = open_hooks[0] if isinstance(open_hooks[0], dict) else {"hook": str(open_hooks[0])}
        hook_text = first_hook.get("hook", brief)
        urgency = first_hook.get("urgency", "中")
        push_line = (
            f"那个没解开的结——{hook_text}——像根刺一样扎在意识底下。"
            f"她不是不想绕开它，是绕不开。每次她试着想别的，那根刺就往里钻一点。"
        )
        if urgency == "高":
            push_line += "它等不了了。她知道再拖一夜，有些东西就会自己消失——被人清理，被人改写，被人假装从未存在过。"
        else:
            push_line += "它还能再等等。但等待是有代价的，每多等一天，她就多欠自己一笔账。"
    else:
        hook_text = brief
        push_line = (
            f"{brief}。这件事不解决，她走不出去。"
            f"不是因为外面有人拦她，是因为她自己会在门口停下来——她没法带着一个没回答的问题往前走。"
        )

    # 中段冲突
    conflict_line = (
        f"她往深处走了几步。{brief}的线索就摆在面前，可每动一下，"
        f"都有人在暗处跟着调整棋盘。她发现自己不是在追真相，"
        f"是在被真相引着走——而引她的那双手，比她更清楚她会在哪里犹豫、"
        f"在哪里心软、在哪里会停下来多看一眼。这让她发冷。不是外界的冷，"
        f"是被看透的冷。她第一次意识到，对手研究的不是她的能力，是她的弱点。"
        f"\n\n身后传来脚步声。守夜人靠在门框上，声音压得很低：“你找到想要的了吗？”"
        f"\n{protagonist}没有回头：“还没有。”"
        f"\n“那就别找了。”守夜人说，“有些东西不是给你看的。”"
        f"\n“那它们为什么在我的抽屉里？”她转过身，看着他。"
        f"\n守夜人沉默了几秒。“因为你比别人更擅长装作没看见。”"
    )

    # 选择与代价
    choice_line = (
        f"她做了一个选择。不是最聪明的，不是最安全的，"
        f"但是当下唯一能让她还觉得自己是自己的选择。"
        f"做完之后她没有轻松感，也没有悲壮感，只是觉得胸口那团压着的东西"
        f"松了一点点——不是解开，是换了个位置压着。"
        f"{core_tension}——这个问题没被回答，但被她的动作按住了，按得很重。"
        f"她知道它还会弹起来，但不是现在。"
    )

    # 钩子结尾 / 终章收束
    temp_word = scene_temperature.split("，")[0] if "，" in scene_temperature else scene_temperature
    if is_final_chapter:
        hook_ending = (
            f"章末，{protagonist}没有再等谁来替她确认答案。她把那样不该有的东西放回档案里，"
            f"也把自己的名字留在同一页上。这样做不会让失去变得轻一点，却让失去终于有了位置。"
            f"窗外的{temp_word}慢慢停了。灰塔的钟针重新向前挪动一格，声音很轻，"
            f"轻得像有人在远处合上一本书。她站了很久，直到街灯一盏一盏亮起来，"
            f"才转身离开。那些被保存下来的痛苦没有消失，但也不再追着她跑。"
            f"故事到这里停住，不是因为所有问题都变得容易，而是因为她终于能带着答案继续活下去。"
        )
    else:
        hook_ending = (
            f"章末，{protagonist}手里多了一样不该有的东西。她不知道该藏起来还是该交出去，"
            f"但她知道很快就会有人来找她要。她把那东西握紧，指节发白。"
            f"窗外的{temp_word}还没停。她在等——等的不是天亮，是一个她还没想清楚的决定。"
        )

    return "\n\n".join([
        f"第 {chapter_number} 章 · {title}",
        opening,
        emotion_line + "\n\n" + push_line,
        conflict_line,
        choice_line,
        hook_ending,
    ])


# ---------------------------------------------------------------------------
# stub 输出封装
# ---------------------------------------------------------------------------
def build_stub_ai_output(
    workflow: str,
    payload: AiWorkflowIn,
    context: dict[str, Any] | None = None,
    error: str = "当前使用本地占位模型。",
) -> dict[str, Any]:
    context = context or {}
    titles = {
        "generate_setting": "小说设定",
        "generate_characters": "人物卡",
        "generate_outline": "总纲",
        "generate_chapter_directory": "章节目录",
        "generate_chapter_brief": "本章大纲",
        "generate_chapter_draft": "章节正文",
        "summarize_chapter": "章节摘要",
        "extract_memory": "记忆提取",
        "extract_timeline_events": "时间线提取",
        "extract_relationships": "关系变化",
        "check_consistency": "一致性检查",
        "check_taboo_rules": "雷点检查",
        "analyze_style_sample": "风格分析",
        "revise_selection": "改写结果",
        "score_chapter": "章节评分",
        "generate_emotion_seed": "情感种子",
        "emotion_archaeology": "情感考古",
        "deepen_and_bury": "加深·藏回",
        "trace_image_growth": "意象追踪",
        "retrospect_deepen": "回溯加深",
        "generate_chapter_bridge": "章节衔接包",
    }
    title = titles.get(workflow, workflow)
    structured = structured_output_for_workflow(workflow, payload, context)
    if workflow == "generate_chapter_draft":
        text = build_local_chapter_draft(payload, context)
    elif structured is not None:
        text = json.dumps(structured, ensure_ascii=False, indent=2)
    else:
        text = f"## {title}\n\n这是本地 MVP 的可编辑 AI 占位结果。输入提示：{payload.prompt or payload.content or '无'}"
    score = 82 if workflow == "score_chapter" else 0
    return {
        "workflow": workflow,
        "model": "local-stub",
        "text": text,
        "score": score,
        "structured": structured,
        "status": "local",
        "error": error,
        "items": [{"title": title, "content": text}],
    }


# ---------------------------------------------------------------------------
# AI 文本解析
# ---------------------------------------------------------------------------
def parse_structured_ai_text(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None
