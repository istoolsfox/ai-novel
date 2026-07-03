# PDR · AI 小说情感深度增强功能

| 项 | 值 |
|---|---|
| 文档版本 | v2.0（情感考古架构） |
| 创建日期 | 2026-07-01 |
| 状态 | 待实施 |
| 项目 | AI 小说创作平台（FastAPI + SQLite + Vue 前端） |
| 方案代号 | Emotion Archaeology（情感考古） |
| 前置文档 | `docs/情感深度解决方案v2-情感考古架构.md`（设计原理） |

---

## 1. 背景与目标

### 1.1 问题陈述

AI 生成的小说文本缺乏情感深度，表现为：程式化、按部就班、机械式平铺直叙，无法生成具有强烈情感表达力和文学感染力的文字。

### 1.2 根因

现有生成管线把情感当"模型自由发挥的副产物"，而非"被显式建模、传递、注入、挖掘的一等公民"。具体表现为：

- system prompt 通篇是事实约束，没有一句情感引导
- character-profiles 的 voice 字段存了但生成时未使用
- score_chapter 只评事实一致性，不评情感深度
- 无写后深度阅读机制，情感质量零反馈

### 1.3 设计原则（v2 核心认知）

> **情感不是被规划出来的，是被发现和加深的。**

基于此，v2 采用"挖掘式"而非"规划式"：

1. **种子而非蓝图**：写前只给模糊入口，不规定节拍/技法/张力目标
2. **自由生长**：最少情感指令，允许偏离
3. **情感考古**（核心）：写后多视角深度阅读，发现文字里已藏着的隐藏层
4. **加深·藏回**：做减法 > 做加法
5. **跨章回溯**：后面发现的线索可回溯加深前面章节

### 1.4 目标

| 目标 | 度量 |
|------|------|
| 正文生成有情感方向感 | system prompt 注入情感种子引导 |
| 写后能发现隐藏情感层 | 情感考古工作流产出隐藏层地图 |
| 可定向加深而不破坏原文 | deepen_and_bury 工作流做减法优先 |
| 情感跨章连续 | emotional_leads 表 + 回溯加深机制 |
| 意象含义自然生长 | image_growth 追踪表，不预设含义 |

---

## 2. 功能需求

### 2.1 功能清单

| ID | 功能 | 类型 | 优先级 |
|----|------|------|--------|
| F1 | 情感种子生成 `generate_emotion_seed` | 新工作流 | P1 |
| F2 | 正文生成 prompt 注入种子 | 改造现有 | P1 |
| F3 | 情感考古 `emotion_archaeology` | 新工作流 | P0（MVP核心） |
| F4 | 加深·藏回 `deepen_and_bury` | 新工作流 | P1 |
| F5 | 意象生长追踪 `trace_image_growth` | 新工作流 | P2 |
| F6 | 跨章回溯加深 `retrospect_deepen` | 新工作流 | P2 |
| F7 | 情感考古记录查询 API | 新接口 | P0 |
| F8 | 隐藏层地图查看 API | 新接口 | P0 |

### 2.2 F1：情感种子生成

**时机**：`generate_chapter_brief`（章节大纲）之后、`generate_chapter_draft`（正文）之前。

**输入**：chapter_id + 章节大纲内容 + 角色列表 + 前序章节摘要

**输出**：JSON

```json
{
  "emotion_seed": {
    "core_tension": "一个人在被需要和被看见之间的裂缝",
    "scene_temperature": "湿冷的等待，时间在流走",
    "open_question": "她留下来的理由，是责任还是恐惧？"
  }
}
```

**设计约束**：
- `core_tension`：模糊的、有人性歧义的命题，不是具体情绪
- `scene_temperature`：感官性氛围暗示，不是指令
- `open_question`：本章可触及但不一定要回答的问题
- **禁止**出现 must / target / technique / tension_level 等规划式字段

**完整 Prompt**：

```
你是一位资深小说编辑。你的任务不是规划情节，而是为即将写作的章节提供一个"情感入口"——一个模糊的、有歧义的、可以往任何方向生长的种子。

参考以下信息：
- 章节大纲：{brief}
- 主要角色：{characters}
- 前章摘要：{recent_summaries}

只返回 JSON，包含三个字段：
1. core_tension：本章核心的情感张力命题。不是具体情绪（如"愤怒""悲伤"），而是一个人性层面的裂缝或困境，角色自己也说不清楚的那种。
2. scene_temperature：一个感官性的氛围暗示，用一句话描述场景的"温度"。
3. open_question：一个本章可能触及但不一定要回答的问题。它像一颗没有解开的结。

要求：
- 模糊优于精确。给方向不给答案。
- 感官优于抽象。温度要能被感觉到。
- 问题要无解或延迟解答，不要设计成可以被一句话回答的。
- 不要指定文学技法、不要规定情绪节拍、不要设张力目标。
```

### 2.3 F2：正文生成 prompt 注入种子

**改造对象**：`system_prompt_for_workflow`（main.py L1558）

**改造前**（现有）：

```python
def system_prompt_for_workflow(workflow: str) -> str:
    if workflow in {"generate_chapter_draft", "revise_selection"}:
        return (
            "你是专业的中文长篇小说创作助手。当前任务是生成或改写小说正文。"
            "只返回可直接放入章节编辑器的中文正文，不要返回 JSON、Markdown 标题。"
            "必须参考上下文中的记忆、角色、大纲、时间线、伏笔、雷点。"
            "尤其要读取 volume_memory 和 anti_repetition_notes，避免重复。"
        )
```

**改造后**：

```python
def system_prompt_for_workflow(workflow: str, emotion_seed: dict | None = None) -> str:
    if workflow in {"generate_chapter_draft", "revise_selection"}:
        base = (
            "你是专业的中文长篇小说创作助手。当前任务是生成或改写小说正文。"
            "只返回可直接放入章节编辑器的中文正文，不要返回 JSON、Markdown 标题。"
            "必须参考上下文中的记忆、角色、大纲、时间线、伏笔、雷点。"
            "尤其要读取 volume_memory 和 anti_repetition_notes，避免重复。"
        )
        if emotion_seed:
            seed = emotion_seed.get("emotion_seed", emotion_seed)
            base += (
                f"\n\n【本章的情感入口·不是约束，是你可以往任何方向生长的土壤】\n"
                f"核心张力：{seed.get('core_tension', '')}\n"
                f"场景温度：{seed.get('scene_temperature', '')}\n"
                f"一个可能触及的问题：{seed.get('open_question', '')}\n"
                f"你不必回答这个问题，也不必围绕张力来写。让角色活在场景里，"
                f"让情感从动作和细节里自己长出来。如果角色偏离了预期，允许它偏离。"
            )
        return base
    if workflow in {"generate_outline", "generate_chapter_brief"}:
        return (
            "你是专业的中文长篇小说大纲编辑。当前任务是生成结构化章节大纲，只返回 JSON，不要包裹解释。"
            "必须围绕当前章节标题展开，章节目标、冲突、关键事件、伏笔和结尾钩子都要服务于该标题。"
            "返回字段 chapter_title 必须包含章节数，格式使用"第 N 章 · 章节名"。"
            "必须先检查输入与 llmwiki 上下文中的 outlines、timeline、wiki_pages、foreshadowings。"
            "尤其要读取 volume_memory 和 anti_repetition_notes，避免重复本卷已发生事件、信息揭示、冲突解决方式。"
            "不得生成与已有大纲、时间线或 llmwiki 页面相同或高度相似的事件；如果已有事件出现过，要设计新的推进、反转或后果。"
            "多章大纲必须让每章事件相互区分，不能用同一发现、追查、争执或反转重复填充。"
        )
    return "你是专业的中文长篇小说创作助手。需要结构化工作流时，只返回 JSON，不要包裹解释。"
```

**改造点**：
- 函数签名增加 `emotion_seed` 参数
- 正文生成分支增加柔软的情感种子引导
- 最后一句"允许它偏离"是灵魂

**调用方改造**：`run_model_or_stub`（main.py L1580）需在调用 `system_prompt_for_workflow` 时传入 emotion_seed。emotion_seed 来源：
1. 优先从 `build_generation_context` 返回的 `emotion_seed` 字段获取
2. 若无（未生成种子），则不注入，退回现有行为

### 2.4 F3：情感考古（核心）

**时机**：`generate_chapter_draft` 之后。可手动触发，也可在章节定稿前自动触发。

**输入**：chapter_id + 章节正文 + 角色列表 + 前序章节摘要（用于母题回响）

**输出**：JSON（隐藏层地图）

**核心机制**：对同一段正文做三次独立的深度阅读，每次切换一个视角，最后汇合。

#### 2.4.1 完整 Prompt

```
你是一位文学评论家，正在对一段小说正文做"情感考古"——不是评估好坏，而是深度阅读，发现文字里已经藏着但还没被充分挖掘的隐藏层。

你会从三个独立视角依次阅读同一段文字，每个视角只关注自己该看的东西，不交叉。

=== 章节正文 ===
{chapter_draft}

=== 角色信息 ===
{characters}

=== 前序章节摘要（仅供母题回响视角参考）===
{recent_summaries}

=== 视角一：角色潜意识考古 ===
不分析情节，不评价文笔。只做一件事：盯着角色的动作、停顿、回避、反常行为，追问"这个角色自己都没意识到的，是什么？"

例如：
- "她擦了三遍桌子"——为什么是三遍？她在控制什么？
- "她没接话"——她回避的到底是什么？
- "她突然笑了"——这个笑是真的吗？如果不是，她在掩饰什么？

输出 subconscious_leads 数组，每项包含：
- position：在文字里的大致位置（第几段/引用关键句）
- detail：你注意到的细节
- inferred：你推断的潜意识内容
- why：为什么这么推断
- depth：already_deep（已经够深）/ can_deepen（可以再压深）

=== 视角二：读者体感考古 ===
切换到读者第一人称。不分析，不评价。逐段读下去，记录你"读到哪儿时心里动了一下"。

那个"动了一下"可能是：突然心疼、突然屏住呼吸、突然想骂人、突然觉得哪里不对但说不上来、突然觉得这句话有重量但不知道为什么。

输出 reader_felt_map 对象，包含：
- resonance_points：情感共振点数组（position / felt / why）
- rupture_points：情感断裂点数组（position / issue——该动但没动，或情绪转折太突然）
- silence_points：沉默点数组（position / note——读者会停下来想一下的地方，这是好的留白，不要动它）

=== 视角三：母题回响考古 ===
跳出本章，站在全书高度看反复出现的东西。参考前序章节摘要。

- 有没有某个意象、动作、句子在前面章节也出现过？现在意思变了吗？
- 本章有没有自然长出新的、可能在后面回响的种子？
- 全书有没有反复出现的"未解之结"？

输出 motif_echoes 对象，包含：
- existing_motifs：已有母题在本章的回响数组（motif / chapter_touch / can_deepen）
- new_seeds：本章新生的意象种子数组（image / first_appearance / potential）
- open_knots：全书未解之结数组（knot / chapter_bumped / resolved）

=== 最终汇合 ===
将三个视角的发现汇合成一份"隐藏层地图"。最后附加 deepen_opportunities 数组：列出 3-5 个"最值得加深"的位置，每个用一句话说明怎么加深（做减法还是藏回）。

返回完整 JSON，结构如下：
{
  "subconscious_leads": [...],
  "reader_felt_map": {...},
  "motif_echoes": {...},
  "deepen_opportunities": [...]
}
```

#### 2.4.2 隐藏层地图数据结构

```json
{
  "chapter_id": "...",
  "archaeology_date": "2026-07-01T12:00:00Z",
  "subconscious_leads": [
    {
      "position": "第2段",
      "detail": "擦三遍桌子",
      "inferred": "用控制小动作压抑失控感",
      "why": "三遍是过度的，整齐的抹布是控制欲的投射",
      "depth": "can_deepen"
    }
  ],
  "reader_felt_map": {
    "resonance_points": [
      {"position": "第3段末", "felt": "心疼", "why": "动作太整齐了，整齐得像在撑着"}
    ],
    "rupture_points": [
      {"position": "第6段", "issue": "该动但没动，情绪转折太突然"}
    ],
    "silence_points": [
      {"position": "第4段", "note": "读者会停一下但不知道为什么——好的留白，不要动"}
    ]
  },
  "motif_echoes": {
    "existing_motifs": [
      {"motif": "留下/被需要", "chapter_touch": "第5段触及但浮在表面", "can_deepen": true}
    ],
    "new_seeds": [
      {"image": "方形", "first_appearance": true, "potential": "可能长成控制欲的象征"}
    ],
    "open_knots": [
      {"knot": "她留下来的理由", "chapter_bumped": true, "resolved": false}
    ]
  },
  "deepen_opportunities": [
    "第2段的'擦三遍'已经是好种子，可以再压深——不要加字，反而删一个解释性的词",
    "第5段的回避可以藏得更深——让她的回避看起来像别的理由",
    "第6段断裂处不需要补情绪，需要在前面多留一个伏笔"
  ]
}
```

### 2.5 F4：加深·藏回

**时机**：情感考古之后，用户审阅隐藏层地图后决定哪些位置要加深。

**输入**：chapter_id + 章节正文 + 隐藏层地图（或用户选定的 deepen_opportunities 子集）

**输出**：修改后的完整正文 + 修改说明

**完整 Prompt**：

```
你拿到一份章节正文和一份"隐藏层地图"。地图指出了这段文字里已经藏着但可以再深的潜力点。

你的任务不是重写，是加深。原则：

1. 做减法优先于做加法。能删一个解释性词语解决的，不要加一整句。
2. 把浮在表面的潜台词压下去。已经说出来的潜台词不算潜台词。
3. 保留留白点。地图标注的 silence_points 是好的，不要填满。
4. 不要追求"更动人"，追求"更藏"。越藏读者越能自己感到。
5. 只修改地图指出的位置（deepen_opportunities），其他地方一个字不动。

=== 章节正文 ===
{chapter_draft}

=== 隐藏层地图·加深机会 ===
{deepen_opportunities}

返回 JSON：
{
  "revised_text": "修改后的完整正文",
  "changes": [
    {
      "position": "第2段",
      "before": "她在发麻。手指是机械的。",
      "after": "手指是机械的。",
      "reason": "删掉'她在发麻'，让动作本身的机械感传递麻木——做减法"
    }
  ]
}
```

### 2.6 F5：意象生长追踪

**时机**：章节定稿时（与 extract_memory / summarize_chapter 同批次）。

**输入**：chapter_id + 章节正文 + 已有意象记录

**输出**：意象出现史更新

**完整 Prompt**：

```
扫描以下章节正文，识别可能成为意象的重复元素（动作、物件、声音、天气、颜色等）。

=== 章节正文 ===
{chapter_draft}

=== 已有意象记录 ===
{existing_images}

规则：
1. 如果是已有意象的新一次出现：记录本次情境，不主动赋义。
2. 如果是新意象第一次出现：登记为种子，暂不赋义。
3. 不指定含义。含义由考古视角来回望总结。

返回 JSON：
{
  "tracked_images": [
    {
      "image": "雨声",
      "is_new": false,
      "chapter_number": 7,
      "context": "他走后那天下大雨",
      "felt_meaning_hint": "（可选，留空也行）开始和'失去'绑定"
    }
  ]
}
```

### 2.7 F6：跨章回溯加深

**时机**：情感考古发现强线索后，用户决定回溯加深前序章节。

**输入**：lead_id（情感线索ID）+ 候选回溯章节列表

**机制**：
1. 根据 lead 内容，用向量检索（或全文检索）在已写章节里找"已触及但未展开"的位置
2. 对选中章节调用 `deepen_and_bury` 工作流
3. 标记该线索为已回溯加深

**Prompt**：复用 F4 的加深·藏回 prompt，context 换为被回溯章节的正文和该线索对应的 deepen_opportunity。

---

## 3. 数据模型

### 3.1 新增表

在 `database.py` 的 `init_db()` 中新增以下建表语句：

```sql
-- 情感种子（每章一条，写前生成）
CREATE TABLE IF NOT EXISTS emotion_seeds (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    core_tension TEXT DEFAULT '',
    scene_temperature TEXT DEFAULT '',
    open_question TEXT DEFAULT '',
    payload TEXT DEFAULT '{}',
    status TEXT DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

-- 情感考古记录（每章可多条，每次考古一条）
CREATE TABLE IF NOT EXISTS emotion_archaeology (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    hidden_layer_map TEXT DEFAULT '{}',
    view_mode TEXT DEFAULT 'triple',
    payload TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

-- 跨章情感线索（考古发现的、可回溯加深的线索）
CREATE TABLE IF NOT EXISTS emotional_leads (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    discovered_in_chapter TEXT NOT NULL,
    lead_content TEXT NOT NULL,
    lead_type TEXT DEFAULT 'subconscious',
    source_chapters_can_deepen TEXT DEFAULT '[]',
    deepened_chapters TEXT DEFAULT '[]',
    status TEXT DEFAULT 'discovered',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

-- 意象生长记录（每意象每章一条）
CREATE TABLE IF NOT EXISTS image_growth (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    image_name TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    chapter_number INTEGER DEFAULT 0,
    context TEXT DEFAULT '',
    felt_meaning_hint TEXT DEFAULT '',
    is_new INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);
```

### 3.2 复用现有机制

character-profiles 的 payload 扩展（无需改表，payload 是 JSON）：

```json
{
  "name": "沈照夜",
  "voice": "短句、克制、少用感叹",
  "emotional_baseline": {
    "default_emotion": "警惕性克制",
    "trigger_map": {
      "被质疑动机": "压抑的愤怒 → 短句变碎句"
    },
    "defense_mechanism": "用反问挡回直白情绪",
    "unspoken_rules": "从不说'我害怕'"
  }
}
```

暂不强制要求所有角色都有 emotional_baseline——它是可选的增量字段，有则用，无则不影响现有流程。

---

## 4. 接口设计

### 4.1 工作流接口（复用现有）

所有新工作流复用现有路由：

```
POST /api/projects/{project_id}/ai/{workflow}
```

新增 workflow 值：

| workflow 值 | 功能 | 对应F |
|-------------|------|-------|
| `generate_emotion_seed` | 生成情感种子 | F1 |
| `emotion_archaeology` | 情感考古 | F3 |
| `deepen_and_bury` | 加深·藏回 | F4 |
| `trace_image_growth` | 意象追踪 | F5 |
| `retrospect_deepen` | 回溯加深 | F6 |

请求体复用 `AiWorkflowIn`：

```python
class AiWorkflowIn(BaseModel):
    model_config = ConfigDict(extra="allow")
    chapter_id: str = ""
    prompt: str = ""
    content: str = ""
    count: int = 2
    payload: dict[str, Any] = Field(default_factory=dict)
```

不同工作流通过 `payload` 字段传递差异化参数：
- `emotion_archaeology`：payload 可含 `view_mode`（triple/subconscious/reader/motif）
- `deepen_and_bury`：payload 可含 `selected_opportunities`（用户选定的加深项）
- `retrospect_deepen`：payload 含 `lead_id` + `target_chapter_ids`

### 4.2 查询接口（新增）

```
GET  /api/projects/{project_id}/chapters/{chapter_id}/emotion-seed
GET  /api/projects/{project_id}/chapters/{chapter_id}/archaeology
GET  /api/projects/{project_id}/chapters/{chapter_id}/archaeology/{archaeology_id}
GET  /api/projects/{project_id}/emotional-leads?status=discovered
GET  /api/projects/{project_id}/emotional-leads/{lead_id}
PATCH /api/projects/{project_id}/emotional-leads/{lead_id}  # 更新状态
GET  /api/projects/{project_id}/image-growth
GET  /api/projects/{project_id}/image-growth/{image_name}  # 某意象的完整出现史
```

返回格式遵循现有项目风格（直接返回 dict 或 list）。

### 4.3 持久化时机

| 工作流 | 完成后持久化 |
|--------|-------------|
| generate_emotion_seed | 写入 emotion_seeds 表 |
| emotion_archaeology | 写入 emotion_archaeology 表；强线索写入 emotional_leads 表 |
| deepen_and_bury | 更新 chapters.draft（覆盖正文）；修改说明存入 ai_runs |
| trace_image_growth | 写入 image_growth 表 |
| retrospect_deepen | 更新对应 chapters.draft；更新 emotional_leads.deepened_chapters |

---

## 5. 代码改造点清单

### 5.1 database.py

- `init_db()` 新增 4 张表的 CREATE TABLE
- 新增 CRUD 辅助函数：`create_emotion_seed` / `get_emotion_seed` / `create_archaeology` / `list_archaeology` / `create_emotional_lead` / `list_leads` / `update_lead` / `create_image_growth` / `list_image_growth`

### 5.2 main.py

| 改造点 | 位置 | 内容 |
|--------|------|------|
| `system_prompt_for_workflow` | L1558 | 增加 emotion_seed 参数（F2） |
| `build_generation_context` | L764 | 返回值增加 emotion_seed 字段（查询当前章节的种子） |
| `structured_output_for_workflow` | L1330 | 新增 5 个工作流的 stub 结构化输出 |
| `build_stub_ai_output` | L1501 | titles 字典新增 5 个工作流标题 |
| `run_ai_workflow` | L1177 | 新增 5 个工作流的持久化分支（类比现有 score_chapter 分支） |
| `compact_payload_for_remote` | L924 | 新工作流的 payload 压缩规则 |
| 新增 API 路由 | 文件末尾 | 6 个查询接口（4.2 节） |

### 5.3 改造优先级

```
P0（MVP）：
  1. database.py 新增 emotion_archaeology 表 + CRUD
  2. main.py 新增 emotion_archaeology 工作流（prompt + stub + 路由 + 持久化）
  3. main.py 新增查询接口
  → 效果：写完一章后可以跑情感考古，产出隐藏层地图

P1：
  4. database.py 新增 emotion_seeds 表
  5. main.py 新增 generate_emotion_seed 工作流
  6. system_prompt_for_workflow 注入种子
  7. build_generation_context 聚合种子
  8. main.py 新增 deepen_and_bury 工作流
  → 效果：写前有种子入口，写后可定向加深

P2：
  9. database.py 新增 emotional_leads + image_growth 表
  10. main.py 新增 trace_image_growth + retrospect_deepen 工作流
  → 效果：跨章连续，意象生长
```

---

## 6. Stub 输出设计（无远程模型时的占位）

在 `structured_output_for_workflow` 中为 5 个新工作流添加 stub：

```python
if workflow == "generate_emotion_seed":
    return {
        "emotion_seed": {
            "core_tension": "一个人在被需要和被看见之间的裂缝",
            "scene_temperature": "湿冷的等待，时间在流走",
            "open_question": "她留下来的理由，是责任还是恐惧？"
        }
    }

if workflow == "emotion_archaeology":
    return {
        "subconscious_leads": [
            {
                "position": "第2段",
                "detail": "（stub）角色重复某个动作",
                "inferred": "用控制小动作压抑内在波动",
                "why": "重复是过度的，整齐是控制欲的投射",
                "depth": "can_deepen"
            }
        ],
        "reader_felt_map": {
            "resonance_points": [{"position": "第3段末", "felt": "隐隐心疼", "why": "（stub）动作太整齐"}],
            "rupture_points": [],
            "silence_points": [{"position": "第4段", "note": "（stub）好的留白"}]
        },
        "motif_echoes": {
            "existing_motifs": [],
            "new_seeds": [{"image": "（stub）某物件", "first_appearance": True, "potential": "可能长成象征"}],
            "open_knots": []
        },
        "deepen_opportunities": ["（stub）第2段可以做减法加深"]
    }

if workflow == "deepen_and_bury":
    return {
        "revised_text": payload.content or "（stub）加深后的正文",
        "changes": [
            {"position": "第2段", "before": "（原文）", "after": "（修改后）", "reason": "做减法"}
        ]
    }

if workflow == "trace_image_growth":
    return {
        "tracked_images": [
            {"image": "（stub）雨声", "is_new": True, "chapter_number": 1, "context": "（stub）", "felt_meaning_hint": ""}
        ]
    }

if workflow == "retrospect_deepen":
    return {
        "revised_text": "（stub）回溯加深后的正文",
        "changes": [{"position": "（stub）", "before": "（原文）", "after": "（修改后）", "reason": "回溯加深"}],
        "lead_id": payload.payload.get("lead_id", "")
    }
```

---

## 7. build_generation_context 改造

在 `build_generation_context`（main.py L764）的返回值中新增字段：

```python
def build_generation_context(project_id: str, chapter_id: str = "") -> dict[str, Any]:
    # ... 现有逻辑不变 ...
    
    # 新增：查询当前章节的情感种子
    emotion_seed = None
    if chapter_id:
        with connect() as conn:
            seed_row = conn.execute(
                "SELECT * FROM emotion_seeds WHERE project_id = ? AND chapter_id = ? ORDER BY updated_at DESC LIMIT 1",
                (project_id, chapter_id)
            ).fetchone()
            if seed_row:
                emotion_seed = row_to_dict(seed_row)
    
    return {
        # ... 现有字段不变 ...
        "emotion_seed": emotion_seed,  # 新增
    }
```

`run_model_or_stub` 调用 `system_prompt_for_workflow` 时传入：

```python
request_body = {
    "model": model,
    "messages": [
        {"role": "system", "content": system_prompt_for_workflow(workflow, context.get("emotion_seed"))},
        # ...
    ],
}
```

---

## 8. 验收标准

### 8.1 P0（MVP）验收

| 验收项 | 标准 |
|--------|------|
| 数据库 | emotion_archaeology 表创建成功，CRUD 正常 |
| 工作流路由 | POST /api/projects/{id}/ai/emotion_archaeology 返回隐藏层地图 JSON |
| Stub | 无远程模型时返回合法 stub JSON |
| 远程模型 | 有远程模型时传入三视角 prompt，返回结构化隐藏层地图 |
| 持久化 | 考古记录写入 emotion_archaeology 表 |
| 查询接口 | GET archaeology 接口返回历史记录 |
| 不破坏现有 | 现有工作流全部正常，无回归 |

### 8.2 P1 验收

| 验收项 | 标准 |
|--------|------|
| 情感种子 | generate_emotion_seed 返回三字段 JSON |
| prompt 注入 | 正文生成 system prompt 含种子引导，含"允许偏离" |
| 种子持久化 | emotion_seeds 表读写正常 |
| 加深·藏回 | deepen_and_bury 返回修改后正文 + changes 说明 |
| 正文更新 | 加深后 chapters.draft 被更新 |

### 8.3 P2 验收

| 验收项 | 标准 |
|--------|------|
| 意象追踪 | trace_image_growth 写入 image_growth 表 |
| 线索管理 | emotional_leads 表 CRUD 正常 |
| 回溯加深 | retrospect_deepen 可对前序章节做加深 |

---

## 9. 风险与对策

| 风险 | 等级 | 对策 |
|------|------|------|
| 考古 prompt 太长导致 token 超限 | 中 | 正文超长时分段考古；compact_value 已有截断机制 |
| 模型返回的隐藏层地图格式不规范 | 中 | parse_structured_ai_text 已有容错；stub 兜底 |
| 加深·藏回破坏原文叙事 | 中 | 只改指定位置；返回 changes 供用户审阅；不自动覆盖，需用户确认 |
| 意象追踪误判 | 低 | 人工可编辑 image_growth 记录；不影响正文 |
| 回溯加深改坏前序章节 | 中 | 回溯前自动创建 chapter_versions 备份 |

---

## 10. 实施顺序

```
Phase 0（MVP，先跑通考古）：
  database.py: 新增 emotion_archaeology 表 + CRUD
  main.py: 新增 emotion_archaeology 工作流（prompt + stub + 路由 + 持久化）
  main.py: 新增查询接口
  → 验收 P0

Phase 1（种子 + 加深）：
  database.py: 新增 emotion_seeds 表
  main.py: generate_emotion_seed 工作流
  main.py: system_prompt_for_workflow 注入种子
  main.py: build_generation_context 聚合种子
  main.py: deepen_and_bury 工作流
  → 验收 P1

Phase 2（跨章 + 意象）：
  database.py: 新增 emotional_leads + image_growth 表
  main.py: trace_image_growth 工作流
  main.py: retrospect_deepen 工作流
  → 验收 P2
```

---

## 附录 A：现有代码关键位置索引

| 文件 | 行号 | 函数/结构 | 改造内容 |
|------|------|----------|---------|
| main.py | L87 | AiWorkflowIn | 不改（复用 payload 字段） |
| main.py | L764 | build_generation_context | 增加 emotion_seed 字段 |
| main.py | L924 | compact_payload_for_remote | 新工作流压缩规则 |
| main.py | L1177 | run_ai_workflow | 新工作流持久化分支 |
| main.py | L1330 | structured_output_for_workflow | 5 个新工作流 stub |
| main.py | L1501 | build_stub_ai_output | titles 字典新增 5 项 |
| main.py | L1558 | system_prompt_for_workflow | 增加 emotion_seed 参数 |
| main.py | L1580 | run_model_or_stub | 传入 emotion_seed |
| database.py | L56 | init_db | 新增 4 张表 |
| database.py | L170 | GENERIC_TABLES | 不改（新表独立管理） |

## 附录 B：不做什么（v2 明确排除）

- ❌ 不做情感蓝图（5节拍张力曲线）——这是 v1 的错误
- ❌ 不做硬约束 prompt（必须命中/必须达到）
- ❌ 不做情感达标审查（打分 + 薄弱节拍）
- ❌ 不做情感强化改写（做加法）
- ❌ 不预设意象含义
- ❌ 不改现有 score_chapter（保留事实评分，情感维度另走考古）
- ❌ 不强制所有角色都有 emotional_baseline（可选增量）
