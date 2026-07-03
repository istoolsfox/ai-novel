# PDR v4 · 全流程托管 AI 小说生成平台（情感深度增强版）

| 项 | 值 |
|---|---|
| 文档版本 | 4.0 |
| 创建日期 | 2026-07-01 |
| 状态 | 待评审 → 待实施 |
| 项目代号 | ai-novel-workbench |
| 仓库根目录 | `G:\ai小说` |
| 参考项目 | [PlotPilot](https://github.com/shenminglinyi/PlotPilot)、[webnovel-writer](https://github.com/lingfengQAQ/webnovel-writer) |
| 前置文档 | `PDR-AI小说创作平台.md`、`PDR-桌面化改造.md`、`PDR-v3-参照PlotPilot架构.md`（已整合）、`情感深度解决方案v2-情感考古架构.md`（已整合） |

> **本版定位**：在 PDR v3 的工程架构基础上，**以情感感染力为第一性原理**重新整合两个参考项目的优点，把"情感考古架构"从辅助环节升级为管线心脏，并补齐 PDR v3 缺失的"对话情感深化"和"追读力系统"。最终交付一个**全流程托管、可独立分发、文字富含深意的桌面端应用**。

---

## 0. 为什么要做 v4（v3 的不足）

PDR v3 参照了 PlotPilot 的工程架构，但存在三个关键缺口：

1. **情感方案被弱化为管线的一个步骤**：v3 把情感考古放在七步管线的第 4 步，但考古产出（隐藏层地图）没有被充分反馈到生成端——它更像"质检报告"而非"生长引擎"。
2. **对话情感缺失**：v3 完全没有覆盖"角色对话如何注入真实细腻情感"。对话是小说情感的半壁江山，缺这块等于瘸腿。
3. **未吸收 webnovel-writer 的追读力系统**：v3 只对标 PlotPilot，漏掉了 webnovel-writer 在"爽点节奏 + 钩子债务"上的成熟实践。追读力和情感深度不矛盾——好的情感张力本身就是最强的追读力。

v4 的核心动作就是**补齐这三块**，同时解决 v3 遗留的 `main.py` 2428 行单文件巨石问题。

---

## 1. 两个参考项目的优劣分析

### 1.1 webnovel-writer（项目一）

| 维度 | 做法 | 评价 |
|---|---|---|
| 形态 | Claude Code 插件 | ❌ 依赖 Claude Code 生态，非独立应用，不利于分发 |
| 核心问题 | 长篇连载的"遗忘""幻觉" | ✅ 抓住了长篇创作的真问题 |
| Story System | 合同种子 + runtime contract + CHAPTER_COMMIT + 事件审计 | ✅ 事实入账机制严谨，值得借鉴 |
| 写章工作流 | 9 步：预检→contract→context-agent→起草→reviewer→润色→Anti-AI→data-agent→commit→备份 | ✅ 流程完整，Anti-AI 终检是亮点 |
| 审查维度 | 爽点、一致性、节奏、OOC、连贯性、追读力 | ⚠️ 偏网文爽感，文学性情感深度不足 |
| 追读力系统 | Hook / Cool-point / 微兑现 / 债务追踪 | ✅ **本项目最值得借鉴的部分**，情感张力需要追读力来兑现 |
| RAG | Embedding + Rerank，可回退 BM25 | ✅ 健壮的降级策略 |
| 题材模板 | 37 个网文题材 | ✅ 声明式题材切换思路好 |
| 断点恢复 | 可信断点检查，不重写已完成的产物 | ✅ 工程上成熟 |
| 情感表达 | 无专门的文学性情感策略 | ❌ **最大短板**，只管"不写崩"不管"写得动人" |

**一句话**：webnovel-writer 是"一致性工程"的优等生，"文学性情感"的差生。

### 1.2 PlotPilot（项目二）

| 维度 | 做法 | 评价 |
|---|---|---|
| 形态 | Tauri + FastAPI sidecar + Vue 3 独立桌面应用 | ✅ **本项目目标形态**，可独立分发 |
| 架构 | DDD 五层分层（domain/application/engine/infrastructure/interfaces） | ✅ 工程化标杆 |
| 十步管线 | 治理预算→剧本→上下文→LLM→策略验证→漂移检测→章末→向量→张力→落库 | ✅ 流程严密 |
| 质量监控 | 张力心电图、文风漂移、定向修写、陈词滥调扫描 | ✅ **量化叙事质量**是创新 |
| 提示词策略 | 20+ 接点 YAML 声明式配置 | ✅ 切换题材不改代码 |
| 声线锚点 | 每个提示包独立配置叙事声音 | ✅ 文学一致性的基础 |
| 定向修写 | 不回滚整章，只修偏离部分 | ✅ 节约生成成本 |
| 熔断保护 | 连续失败自动暂停 + 诊断 | ✅ 工程健壮 |
| 情感表达 | 通过张力评分、节拍约束间接保障 | ⚠️ **文学性策略不透明**，工程约束无法替代文学性本身 |
| 向量检索 | ChromaDB/FAISS + 三元组索引 | ✅ 但 MVP 可暂缓 |
| Python 3.14 | 硬依赖 | ❌ 门槛过高，本项目用 3.13 |

**一句话**：PlotPilot 是"工程架构"的优等生，但把文学性当工程问题解决——方向上有缺口。

### 1.3 本项目（旧方案）的优势

| 维度 | 现状 | 价值 |
|---|---|---|
| 情感考古架构（v2） | 种子→生长→考古→加深·藏回→回溯重构 | ✅ **本项目最大的创新资产**，两个参考项目都没有 |
| 垂直五层情感模型 | 表层→情感层→意层→潜层→韵层 | ✅ 真正触及"文学性"本质 |
| 意象生长系统 | 不指定含义，记录出现史 | ✅ 符合真实文学创作规律 |
| 做减法优先 | 加深·藏回，能删不补 | ✅ 区别于两个项目的"做加法修写" |
| FastAPI + React + Tauri 技术栈 | 已落地 | ✅ 不需要重写 |

**关键认知**：本项目的情感考古架构，是两个参考项目都缺失的"文学性心脏"。v4 的工作不是抛弃它另起炉灶，而是**给它配上一流的工程骨架**，让它真正运转起来。

---

## 2. 核心设计理念

### 2.1 一句话定位

> **用 PlotPilot 的工程骨架，驮着本项目的情感考古心脏，再装上 webnovel-writer 的追读力引擎——让 AI 写出既有文学感染力、又能让人追着读下去的长篇。**

### 2.2 三条不可动摇的原则

1. **情感是被发现和加深的，不是被规划出来的**（继承 v2）。任何试图在写前"规定第 3 段张力 8 分、用通感技法"的做法都已经被证明是精致的程式化。种子给方向，考古找矿藏，加深做减法。
2. **工程约束保障下限，文学性策略提升上限**（融合 PlotPilot）。张力评分、文风漂移检测、熔断保护负责"不写崩"；情感考古、对话潜台词、意象生长负责"写得动人"。两者分工，不互相替代。
3. **追读力是情感张力的兑现机制**（吸收 webnovel-writer）。没有追读力的情感是孤芳自赏，没有情感深度的追读力是廉价爽感。两者必须共生。

### 2.3 与两个参考项目的根本区别

| | webnovel-writer | PlotPilot | 本项目 v4 |
|---|---|---|---|
| 写后动作 | 审查缺陷 → 修写 | 检测漂移 → 定向修写 | **发现潜力 → 加深·藏回（做减法）** |
| 情感方向 | 爽点节奏 | 张力心电图 | **垂直五层 + 情感考古 + 意象生长** |
| 修改哲学 | 做加法 | 做加法（定向修写） | **做减法优先** |
| 对话处理 | 无专门机制 | POV 防火墙 | **对话潜台词分层挖掘** |
| 追读力 | Hook/债务追踪 | 无 | **吸收 + 与情感张力联动** |

---

## 3. 情感表达增强方案（四维度详细设计）

### 3.1 维度一：叙述文本的情感张力与文学性

#### 3.1.1 核心：情感考古架构（继承 v2，强化反馈闭环）

v2 的"种子→生长→考古→加深"流程保留，但 v4 修补 v3 的缺口——**让考古产出真正反哺生成**：

```
v3 的问题：考古产出隐藏层地图 → 只用于 deepen_and_bury（一次性消费）→ 知识流失
v4 的修补：考古产出 → 双向反馈
   ├─ 即时反馈：deepen_and_bury（本章加深）
   ├─ 纵向反馈：emotional_leads 回溯加深前序章节
   └─ 横向反馈：考古发现写入"叙事记忆"，注入下一章的 emotion_seed
```

**新增：考古发现注入下一章种子**。当第 N 章考古发现"角色的核心潜意识驱动是证明自己有资格留下"时，这条线索不只是回溯加深前文，还会成为第 N+1 章 emotion_seed 的 `core_tension` 候选之一——让情感线层层沉积而非各章孤立。

#### 3.1.2 增强：垂直五层情感模型（显式化）

v2 提出了五层但未工程化。v4 把它变成考古视角的输出结构：

```json
{
  "layer_analysis": {
    "surface": {"text": "她擦了三遍桌子，把抹布叠成方形", "status": "已呈现"},
    "emotional": {"text": "手指是机械的", "status": "已呈现，但过于直白，建议藏回"},
    "intention": {"text": "（未说出）如果那时拦了他一下", "status": "缺失，建议通过动作泄露"},
    "subconscious": {"text": "用'还有用'证明自己有资格留下", "status": "缺失，可加深"},
    "resonance": {"text": "留下/被需要——全书母题", "status": "已触及，可再压深"}
  }
}
```

考古视角一（角色潜意识）的输出从"线索清单"升级为"五层分析"，deepen_and_bury 据此决定在哪一层做减法。

#### 3.1.3 增强：意象生长系统（继承 v2，接入考古）

v2 的意象生长系统保留，v4 明确它与考古视角三（母题回响）的关系：

```
trace_image_growth（章末）→ 登记意象出现史
   ↓
emotion_archaeology 视角三 → 回望意象当前含义
   ↓
deepen_and_bury → 在已触及但浮在表面的意象处加深
```

意象不指定含义，但考古会回望含义，加深会让含义沉积——三者形成闭环。

#### 3.1.4 借鉴 PlotPilot：声线锚点 + 文风漂移检测

- **声线锚点**：每个提示包 YAML 配置 `voice_anchor` 字段，定义本题材/本作品的叙事声音特征（如"冷峻、克制、留白多于抒情"）。生成时注入 system prompt。
- **文风漂移检测**：章末用向量相似度对比风格基准，漂移超阈值触发告警。**但 v4 的处理不是 PlotPilot 的"定向修写（做加法）"，而是触发一次 emotion_archaeology 的"漂移视角"考古**——先理解为什么漂移，再决定是修正还是接纳（有时候漂移是角色情感变化的自然结果）。

#### 3.1.5 借鉴 webnovel-writer：Anti-AI 终检

在 deepen_and_bury 之后、summarize 之前，加一个轻量的 `anti_ai_polish` 步骤：
- 扫描 AI 高频套路表达（"不禁""缓缓""一丝""涌上心头"等）
- 扫描过度解释性语句（把潜台词说破的句子）
- **处理原则仍然是做减法**：能删则删，不能删则改写为更含蓄的表达

### 3.2 维度二：角色对话的真实细腻情感（v3 完全缺失，v4 新增）

这是 v4 相对 v3 最大的增量。对话是小说情感的半壁江山，必须有专门的机制。

#### 3.2.1 问题诊断

AI 生成的对话通病：
- **台词直白**：角色把潜台词直接说出来（"我很伤心"而非通过行为流露）
- **情绪扁平**：对话全程一个情绪基调，没有起伏和停顿
- **角色同质**：不同角色说话方式雷同，缺乏个人声纹
- **节奏单一**：没有沉默、打断、答非所问等真实对话的戏剧性

#### 3.2.2 对话情感分层模型

类比叙述文本的五层，对话也有四层：

```
表层台词    "我没事。"                          ← 说了什么
语气层      声音很轻，没看他。                   ← 怎么说的（动作/神态）
未尽之言    （其实想说你别走）                   ← 没说出口的
动机泄露    她说"没事"是为了让他放心离开         ← 自己都没意识到的
```

**好的对话**：表层最简，语气层有戏，未尽之言让读者感到，动机泄露藏得最深。AI 的通病是表层和动机泄露混在一起——角色把潜台词直接说出来了。

#### 3.2.3 新增工作流：dialogue_subtext_excavation（对话潜台词挖掘）

在 generate_chapter_draft 之后、emotion_archaeology 之前，插入专门处理对话的步骤：

```
输入：章节正文
任务：识别所有对话段落，对每段做潜台词分析
输出：对话潜台词地图
  - 哪句台词把潜台词说破了（需要藏回）
  - 哪段对话缺少语气层（需要补动作/神态）
  - 哪段对话角色声纹不一致（需要调整）
  - 哪段对话可以加入沉默/停顿增强戏剧性
```

这个步骤的产出交给 deepen_and_bury，在加深阶段一并处理对话。

#### 3.2.4 角色声纹库（Character Voice Print）

`characters` 表扩展 `voice_print` 字段：

```json
{
  "voice_print": {
    "speech_habits": ["常用短句", "很少用感叹号", "回避直接表达感情"],
    "vocabulary_tendency": ["偏书面", "会用文言词汇"],
    "avoid_words": ["绝对不会说'宝贝'这种词"],
    "emotional_tells": ["紧张时会重复别人的话", "撒谎时会看窗外"],
    "sample_dialogues": [
      {"context": "被质疑时", "line": "你说得对。", "subtext": "其实不认同但不想争"}
    ]
  }
}
```

生成对话时注入声纹库；考古时检查对话是否符合声纹；deepen 时修正偏离的对话。声纹库本身也是**生长的**——考古发现角色新的语言特征时，回写声纹库。

#### 3.2.5 对话节奏控制

借鉴戏剧对白理论，在提示词中加入节奏引导（非硬约束）：

```
对话节奏引导（柔软指令，非约束）：
- 允许沉默：不是每句都要回应，有时沉默比回答更有力
- 允许打断：真实对话会被打断、会跑题
- 允许答非所问：角色可以回避问题
- 允许重复：紧张时会重复别人的话
- 不要每段对话都"说透"，留一些让读者自己拼
```

### 3.3 维度三：情节推进的情感氛围与节奏控制

#### 3.3.1 情感气候图（卷级，柔软参考非硬约束）

v2 推翻了 v1 的"5 节拍张力曲线硬约束"，这是对的。但完全没有任何卷级情感走向参考，也会导致长篇情感线失控。v4 的折中：**情感气候图作为"气候参考"而非"天气预报"**。

```json
{
  "emotional_climate": {
    "shape": "rise-fall-rise",
    "segments": [
      {"range": "1-5", "climate": "湿冷·迷茫", "intensity_band": "3-4"},
      {"range": "6-10", "climate": "燥热·愤怒", "intensity_band": "5-7"},
      {"range": "11-15", "climate": "阴郁·动摇", "intensity_band": "6-8"},
      {"range": "16-20", "climate": "凛冽·决绝", "intensity_band": "7-9"}
    ]
  }
}
```

- `climate` 是氛围描述，不是具体情绪（不规定"第 3 章必须愤怒"）
- `intensity_band` 是区间不是定值（允许在区间内自由起伏）
- 生成时作为 emotion_seed 的参考输入之一，不是约束

**关键：这是气候不是天气。** 气候给大方向，天气（具体每章情感）由种子+自由生长决定。

#### 3.3.2 追读力系统（吸收 webnovel-writer，与情感联动）

这是 v4 相对 v3 的第二个大增量。引入 webnovel-writer 的追读力概念，但**与情感深度联动**：

| 追读力要素 | webnovel-writer 做法 | v4 改造 |
|---|---|---|
| Hook（钩子） | 章末埋钩子 | **情感钩子优先**：章末的情感悬念比情节悬念更强（"她到底会不会开口"比"他到底会不会死"更抓人） |
| Cool-point（爽点） | 爽点节奏 | **情感兑现点**：情感线的阶段性释放（积压数章的压抑终于爆发的那一刻） |
| 微兑现 | 小爽点 | **情感微光**：不是每章都大爆发，但每章给一点情感微光（一个细节、一句潜台词）让读者感到在推进 |
| 债务追踪 | 钩子开启/悬置/消费 | **情感债务**：角色未表达的情感是债务，积压越多爆发越强——和考古的"未尽之言"联动 |

新增工作流 `analyze_reader_pull`（追读力分析），在 archaeology 之后：

```
输入：章节正文 + 隐藏层地图
输出：追读力报告
  - 章末钩子强度（情感钩子 > 情节钩子）
  - 情感债务变化（新增/兑现/悬置）
  - 情感兑现点评估（该爆发的有没有爆发，不该爆发的有没有提前透支）
  - 追读力评分（1-10，结合情感与情节）
```

**追读力与情感的联动**：追读力低不一定是情节问题，可能是情感债务没有兑现。分析报告会区分"情节钩子不足"还是"情感兑现缺失"，给不同的加深建议。

#### 3.3.3 情感呼吸节奏（防疲劳）

借鉴 PlotPilot 的张力心电图，但 v4 强调**张弛有度**：

```
连续 3 章高张力 → 智能停检测提醒"需要一章低张力的缓冲"
连续 3 章低张力 → 智能停检测提醒"需要推进一个情感兑现点"
```

这不是硬约束，是智能停的触发条件之一（v3 已有智能停，v4 补充情感节奏条件）。

#### 3.3.4 整合：情感节奏控制全景

```
卷级  情感气候图（柔软参考）→ 注入 emotion_seed
        ↓
章级  emotion_seed（模糊种子）→ 自由生长
        ↓
章末  emotion_archaeology → 发现情感状态
        ↓
      analyze_reader_pull → 追读力评估
        ↓
      deepen_and_bury → 加深潜力 + 兑现/埋设情感债务
        ↓
跨章  emotional_leads 回溯 + 叙事记忆注入下一章种子
        ↓
卷级  情感呼吸节奏监控（智能停条件之一）
```

### 3.4 维度四：架构整合方案

见第 4 章架构设计。核心是解决 `main.py` 2428 行巨石问题，用 DDD 分层重新组织。

---

## 4. 架构设计（DDD 分层 + 九步管线）

### 4.1 分层架构（解决 main.py 巨石问题）

```
backend/app/
├── interfaces/              # 接口层：HTTP 路由
│   ├── main.py              # FastAPI app 装配（仅装配，不含业务）
│   ├── routes/
│   │   ├── projects.py      # 项目 CRUD
│   │   ├── chapters.py      # 章节 CRUD
│   │   ├── workflows.py     # AI 工作流调用
│   │   ├── blueprints.py    # 蓝图 CRUD
│   │   ├── jobs.py          # 任务 CRUD + SSE
│   │   └── exports.py       # 导出
│   └── dependencies.py      # 依赖注入
│
├── application/             # 应用层：用例编排
│   ├── job_service.py       # 生成任务用例
│   ├── blueprint_service.py # 蓝图用例
│   ├── context_builder.py   # 上下文装配（从 main.py 迁出）
│   └── export_service.py    # 导出用例
│
├── engine/                  # 引擎内核：生产运行时
│   ├── pipeline.py          # StoryPipeline 九步管线
│   ├── orchestrator.py      # Orchestrator 多章调度
│   ├── checkpoint.py        # 检查点 + 智能停
│   ├── circuit_breaker.py   # 熔断保护
│   └── prompt_loader.py     # YAML 提示词加载
│
├── domain/                  # 领域层：纯数据模型
│   ├── models.py            # Pydantic 模型
│   └── enums.py             # 枚举
│
├── workflows/               # 工作流实现（从 main.py 拆出）
│   ├── base.py              # 工作流基类
│   ├── generation.py        # brief/seed/draft 生成类
│   ├── archaeology.py       # 情感考古（三视角）
│   ├── dialogue.py          # 对话潜台词挖掘（新增）
│   ├── deepen.py            # 加深·藏回
│   ├── reader_pull.py       # 追读力分析（新增）
│   ├── image_growth.py      # 意象生长追踪
│   ├── summary.py           # 章节摘要
│   ├── bridge.py            # 章节衔接包
│   ├── anti_ai.py           # Anti-AI 终检（新增）
│   └── llm_client.py        # LLM 调用封装（从 main.py 迁出）
│
├── infrastructure/          # 基础设施层
│   ├── database.py          # SQLite（从 app/ 迁入）
│   ├── storage.py           # 文件系统（从 app/ 迁入）
│   └── repositories/        # 仓储实现
│
└── prompt_packages/         # 提示词策略层（YAML）
    ├── _base/               # 通用提示包
    ├── wuxia/               # 武侠题材
    ├── scifi/               # 科幻题材
    ├── romance/             # 言情题材
    └── suspense/            # 悬疑题材
```

**关键改造**：`main.py` 2428 行拆解为：
- 接口层 routes/（约 400 行，按资源拆分）
- 应用层 application/（约 300 行）
- 工作流层 workflows/（约 1200 行，按职责拆分）
- 基础设施层 infrastructure/（约 500 行，已有的 database.py + storage.py）

### 4.2 九步管线（v3 七步 + v4 两步）

v3 的七步管线保留，v4 插入两步变成九步：

```
Step 1: generate_chapter_brief      章节大纲
Step 2: generate_emotion_seed       情感种子
Step 3: generate_chapter_draft      正文初稿（自由生长）
Step 4: dialogue_subtext_excavation 对话潜台词挖掘【v4 新增】
Step 5: emotion_archaeology         情感考古（三视角）
Step 6: analyze_reader_pull         追读力分析【v4 新增】
Step 7: deepen_and_bury             加深·藏回（融合考古+对话+追读力产出）
Step 8: anti_ai_polish              Anti-AI 终检
Step 9: summarize_and_bridge        摘要 + 衔接包（合并 v3 两步）
```

**为什么这样排序**：

```
draft（自由生长，允许偏离）
   ↓
dialogue（专挖对话问题，产出对话潜台词地图）
   ↓
archaeology（三视角深度阅读，产出隐藏层地图）
   ↓
reader_pull（追读力分析，产出追读力报告）
   ↓
deepen（综合三份产出，统一做减法加深）
   ↓
anti_ai（扫描套路表达，继续做减法）
   ↓
summarize_and_bridge（定稿后产出摘要+衔接包）
```

- 对话挖掘在考古前：因为对话问题相对具体，先处理；考古是全局深度阅读
- 追读力在考古后：追读力需要参考考古的"未尽之言""情感债务"判断
- deepen 综合三者：避免分多次修改正文，一次加深到位
- anti_ai 在 deepen 后：deepen 可能引入新的套路表达，最后扫一遍

### 4.3 提示词包 YAML 结构（v4 增强）

```yaml
# prompt_packages/_base/generate_chapter_draft.yaml
name: generate_chapter_draft
description: 章节正文生成
category: generation

voice_anchor: |
  叙事声音：冷峻、克制、留白多于抒情。
  情感表达通过动作和细节，而非直接陈述。
  允许沉默，允许不解释。

system_prompt: |
  你是专业的中文长篇小说创作助手。当前任务是生成小说正文。
  只返回可直接放入章节编辑器的中文正文。
  必须参考上下文中的记忆、角色、大纲、时间线、伏笔、雷点。
  尤其要读取 volume_memory 和 anti_repetition_notes，避免重复。

model_params:
  temperature: 0.85
  top_p: 0.92
  max_tokens: 4096

directives:
  - name: emotion_seed
    condition: "emotion_seed is not None"
    template: |
      【本章的情感入口·不是约束，是你可以往任何方向生长的土壤】
      核心张力：{emotion_seed.core_tension}
      场景温度：{emotion_seed.scene_temperature}
      一个可能触及的问题：{emotion_seed.open_question}
      你不必回答这个问题。让角色活在场景里，让情感从动作和细节里自己长出来。
      如果角色偏离了预期，允许它偏离。

  - name: dialogue_rhythm
    condition: "always"
    template: |
      【对话节奏·柔软引导，非约束】
      - 允许沉默：不是每句都要回应
      - 允许打断：真实对话会被打断
      - 允许答非所问：角色可以回避问题
      - 不要每段对话都说透，留一些让读者自己拼

  - name: prev_bridge
    condition: "prev_chapter_bridge is not None"
    template: |
      【上一章衔接包·本章必须承接】
      末尾状态：{prev_bridge.ending_state}
      未决钩子：{prev_bridge.open_hooks}
      情感余波：{prev_bridge.emotional_residue}
      【连贯性硬约束】
      1. 开头必须承接上一章末尾状态
      2. 角色情绪必须从余波起步
      3. 必须回应至少一个未决钩子

  - name: emotional_climate
    condition: "blueprint is not None"
    template: |
      【卷级情感气候·参考非约束】
      当前气候段：{blueprint.current_climate_segment}
      强度区间：{blueprint.current_intensity_band}
      这是气候不是天气，你可以在区间内自由起伏。

  - name: narrative_memory
    condition: "narrative_memory is not None"
    template: |
      【叙事记忆·前章考古发现】
      {narrative_memory}
      这些是前章深度阅读发现的情感线索，供你参考，不是必须承接的。
```

### 4.4 数据模型扩展（v4 新增）

```sql
-- 角色声纹库（扩展现有 characters 表）
-- characters 表新增 voice_print TEXT 字段（JSON）

-- 对话潜台词地图（每章一条）
CREATE TABLE IF NOT EXISTS dialogue_maps (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    subtext_map TEXT NOT NULL,        -- JSON: 对话潜台词分析
    created_at TEXT
);

-- 追读力报告（每章一条）
CREATE TABLE IF NOT EXISTS reader_pull_reports (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    hook_strength INTEGER,            -- 章末钩子强度 1-10
    emotional_debt JSON,              -- 情感债务变化
    pull_score INTEGER,               -- 追读力评分 1-10
    report_json TEXT,                 -- 完整报告
    created_at TEXT
);

-- 叙事记忆（考古发现汇总，注入下一章种子）
CREATE TABLE IF NOT EXISTS narrative_memory (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    source_chapter_id TEXT NOT NULL,
    memory_type TEXT,                 -- subconscious / motif / reader_felt / debt
    memory_content TEXT,              -- 精炼后的记忆条目
    injected_into_seeds TEXT,         -- JSON: 注入了哪些后续章节的 seed
    status TEXT DEFAULT 'active',     -- active / archived
    created_at TEXT
);

-- 复用 v2/v3 已有表：emotion_seeds / emotion_archaeology / emotional_leads /
-- image_growth / chapter_bridges / volume_blueprints / generation_jobs /
-- chapter_generation_steps
```

---

## 5. 全流程托管设计

### 5.1 托管流程全景

```
用户视角：
  1. 创建项目 + 配置模型
  2. 初始化设定（世界观/角色/大纲）【可 AI 辅助】
  3. 生成/编辑卷蓝图（情感气候图 + 伏笔规划 + 角色弧线）【可 AI 辅助】
  4. 批准蓝图
  5. 启动托管任务（选蓝图 + 起始章 + 章数 + 检查点策略）
  6. **纯托管模式**：引擎自动跑九步管线 × N 章，全自动跑完
     ├─ 默认：全自动，不暂停（纯托管，最省人力）
     ├─ 检查点策略可选配（每 N 章暂停 / 仅熔断暂停 / 不暂停）
     ├─ 智能停触发时：自动暂停并推送诊断报告
     └─ 熔断时：自动暂停并推送错误
  7. 任务完成 → 可导出（docx/pdf/epub）
  8. 全程可手动单章编辑（fallback 模式）

> **托管决策（2026-07-02 用户确认）**：纯托管——启动后全自动跑完，仅检查点/熔断时暂停。核心目标是解放人力。

引擎视角（Orchestrator）：
  for each chapter in range:
    1. 检查暂停/检查点
    2. 创建章节
    3. 跑九步管线（每步成功后落库快照）
    4. 智能停检测
    5. 检查点策略（默认 none=不暂停）
    6. 自动定稿（默认开启）
    7. 更新进度 → SSE 推送
    8. 熔断检查
```

### 5.2 介入点设计（托管不等于放任）

| 介入点 | 触发方式 | 用户可操作 |
|---|---|---|
| 检查点 | 每 N 章（可配） | 预览本章 / 编辑后放行 / 中止 |
| 智能停 | 5 种条件自动触发 | 看诊断 / 编辑后继续 / 中止 |
| 熔断 | 连续失败 | 看错误 / 重试 / 中止 |
| 手动暂停 | 用户随时 | 暂停后可编辑已完成章节 |
| 蓝图偏离 | 情感气候严重偏离 | 看报告 / 调整蓝图 / 接纳偏离 |

### 5.3 检查点快照与断点恢复（吸收 webnovel-writer）

**自动保存策略（2026-07-02 用户确认）：检查点+关键步骤落库**

- **关键步骤落库**：`generate_chapter_draft`、`deepen_and_bury`、`summarize_and_bridge`（finalize）三个步骤成功后立即写入数据库 + 文件系统
- **非关键步骤可重跑**：`dialogue_subtext_excavation`、`emotion_archaeology`、`analyze_reader_pull`、`anti_ai_polish` 等分析步骤的产出存 `chapter_generation_steps` 表，中断后可从断点重跑
- **断点恢复**：任务中断后恢复时，检查已完成的可信步骤不重跑，从第一个未完成步骤继续
- **已完成产出保留**：draft/archaeology/对话地图等中间产出保留在 steps 表中

```
关键步骤（必须落库）：    draft → deepen → finalize
非关键步骤（可重跑）：    dialogue / archaeology / reader_pull / anti_ai
```

---

## 6. 桌面端形态（整合 PDR-桌面化改造）

v4 保留桌面化 PDR 的全部设计，这里只列要点：

### 6.1 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 桌面壳 | Tauri 2.0 | 参考 PlotPilot，比 Electron 轻 80% |
| 后端 | FastAPI（PyInstaller 打包为 sidecar） | 业务代码零改动，环境变量注入 |
| 前端 | **Vue 3 + Naive UI + ECharts + TypeScript + Vite** | 切换自 React，参考 PlotPilot 前端栈 |
| 数据库 | SQLite（WAL 模式） | 嵌入式，单写者 |
| 向量检索 | 暂不引入（MVP 用卷记忆 + 全文检索） | 后续可选升级 |

### 6.2 打包分发

- Windows: .msi + .exe（NSIS）
- macOS: .dmg（后续）
- Linux: .deb + .AppImage（后续）
- 安装包 < 100MB，用户无需开发环境

### 6.3 数据本地化

- 数据存用户数据目录（`%LOCALAPPDATA%\ai-novel-workbench\`）
- 配置 GUI（设置页面）
- 首次启动引导

---

## 7. 提示词包的"情感深度"专项设计

这是 v4 相对两个参考项目的核心差异化。所有提示词包遵循以下原则：

### 7.1 三条提示词铁律

1. **禁止规定具体情绪**：不写"本章表现愤怒"，写"核心张力：被忽视与自我价值之间的裂缝"
2. **禁止指定技法**：不写"用通感手法"，让模型自己选择
3. **允许偏离**：每个情感指令都带"允许偏离"的出口

### 7.2 考古三视角提示词（强化版）

**视角一：角色潜意识考古（输出五层分析）**
```
你是文学评论家。不要分析情节，只盯着角色"没说什么"。
对每个关键角色，输出五层分析：
- 表层：发生了什么（已呈现）
- 情感层：当下情绪（已呈现？过于直白需藏回？）
- 意层：没说出口的话（缺失？可通过动作泄露？）
- 潜层：自己都没意识到的动机（缺失？可加深？）
- 韵层：与全书母题的回响（已触及？可再压深？）
标注每层的状态，给出加深建议。
```

**视角二：读者体感考古**（同 v2）
**视角三：母题回响考古**（同 v2，整合意象生长）

### 7.3 对话潜台词挖掘提示词

```
你是戏剧对白导演。识别章节中所有对话段落，对每段分析：
1. 台词是否把潜台词说破了？（是→需要藏回，怎么藏）
2. 是否缺少语气层（动作/神态）？（是→建议补什么）
3. 角色声纹是否一致？（对照角色声纹库）
4. 哪里可以加入沉默/停顿/打断增强戏剧性？
5. 对话的情感债务：角色未表达的情感累积了多少？

输出对话潜台词地图，每段对话标注问题类型 + 修改方向。
```

### 7.4 追读力分析提示词

```
你是资深网文编辑 + 文学评论家的结合体。评估本章追读力：

1. 章末钩子：是情节钩子还是情感钩子？强度 1-10？
   （情感钩子 > 情节钩子，"她到底会不会开口"比"他到底会不会死"更抓人）
2. 情感债务变化：本章新增/兑现/悬置了哪些情感债务？
3. 情感兑现点：该爆发的是否爆发？不该爆发的是否提前透支？
4. 追读力评分 1-10（结合情感与情节）

如果追读力低，区分是"情节钩子不足"还是"情感兑现缺失"，给不同建议。
```

### 7.5 加深·藏回提示词（融合三份产出）

```
你拿到三份报告：对话潜台词地图 + 隐藏层地图 + 追读力报告。
你的任务不是重写，是加深。原则：

1. 做减法优先于做加法。能删一个解释性词语解决的，不要加一整句。
2. 把浮在表面的潜台词压下去。已经说出来的潜台词不算潜台词。
3. 对话藏回：把说破的潜台词改为通过动作/神态泄露。
4. 保留留白点。地图标注的 silence_points 不要动。
5. 追读力不足时，优先补情感钩子而非情节钩子。
6. 不要追求"更动人"，追求"更藏"。越藏读者越能自己感到。

只修改报告指出的位置，其他地方一个字不动。
返回修改后的完整正文 + 每处修改的说明。
```

---

## 8. 实施路线图

### Phase 0：分层重构 + 提示词包（2 天）

```
目标：解决 main.py 2428 行巨石，为后续管线铺路

1. 创建 interfaces/application/engine/domain/workflows/infrastructure 目录
2. 从 main.py 拆出：
   - routes/ → interfaces/routes/
   - build_generation_context → application/context_builder.py
   - run_ai_workflow + 各工作流 → workflows/
   - database.py/storage.py → infrastructure/
3. 创建 prompt_packages/_base/ + 9 个 YAML
4. 创建 engine/prompt_loader.py
5. 保持现有单章手动模式可用（回归测试通过）

验收：
- main.py < 100 行（仅 app 装配）
- 26 个测试通过
- 单章生成功能不变，prompt 内容来自 YAML
```

### Phase 1：引擎内核（2 天）

```
目标：九步管线 + 多章托管能跑

1. engine/pipeline.py（StoryPipeline 九步）
2. engine/orchestrator.py（Orchestrator + 后台线程）
3. engine/checkpoint.py（检查点 + 智能停，补充情感节奏条件）
4. engine/circuit_breaker.py（熔断）
5. application/job_service.py
6. infrastructure/database.py 新增 4 张表
7. interfaces/routes/blueprints.py + jobs.py + SSE

验收：
- API 能启动 3 章自动生成，九步管线串联跑通
- 熔断、检查点、智能停可用
- SSE 推送进度
```

### Phase 2：情感深度工作流（3 天）

```
目标：v4 的情感差异化能力落地

1. workflows/archaeology.py（三视角，视角一升级为五层分析）
2. workflows/dialogue.py（对话潜台词挖掘，新增）
3. workflows/reader_pull.py（追读力分析，新增）
4. workflows/deepen.py（融合三份产出的加深·藏回）
5. workflows/anti_ai.py（Anti-AI 终检，新增）
6. workflows/image_growth.py（意象生长追踪）
7. 角色声纹库字段 + 注入/回写机制
8. 叙事记忆表 + 注入下一章种子机制

验收：
- 对话潜台词地图能识别"说破的潜台词"
- 考古五层分析能标注每层状态
- 追读力报告能区分情感钩子 vs 情节钩子
- deepen 能做减法（对比初稿字数应减少或持平，不应大幅增加）
- Anti-AI 能扫描套路表达
```

### Phase 3：前端控制台（2 天）

```
1. BlueprintEditor.tsx（蓝图 + 情感气候图可视化）
2. JobLauncher.tsx（任务启动）
3. JobProgressPanel.tsx（SSE 实时进度 + 九步明细）
4. CheckpointNotification.tsx（检查点 + 智能停通知）
5. EmotionWorkbench.tsx 增强（展示考古五层 / 对话地图 / 追读力报告）
6. JobResultOverview.tsx（结果总览 + 衔接包链 + 伏笔回收）

验收：前端能启动任务、看实时进度、检查点放行、查看情感分析报告
```

### Phase 4：桌面化打包（1.5 天）

```
1. backend/sidecar_entry.py + scripts/build_sidecar.py
2. desktop/ Tauri 壳（已有基础，完善 sidecar 管理）
3. frontend/src/api.ts 动态 API_BASE
4. SettingsPage.tsx（已有，完善）
5. scripts/build_all.ps1
6. 打包验证

验收：.msi 安装包可在无开发环境的 Windows 上安装运行
```

### Phase 5：打磨 + 蓝图自动生成（1 天）

```
1. 蓝图自动生成工作流（AI 生成完整蓝图 JSON + 情感气候图）
2. 伏笔状态追踪（planted→paid_off）
3. 断点续跑完善
4. 并发控制（同项目同时只跑一个 job）

验收：智能停 + 蓝图自动生成 + 断点恢复
```

**总工期：约 11.5 天**

---

## 9. 验收标准（情感深度专项）

这是 v4 最关键的验收——不是"能跑"，而是"写得动人"。

### 9.1 对话情感验收

| 标准 | 检验方法 |
|---|---|
| 潜台词不说破 | 对话地图标注的"说破"位置，deepen 后应改为动作/神态泄露 |
| 角色声纹一致 | 同一角色在不同章的对话，声纹特征保持 |
| 有沉默/停顿 | 至少 30% 的对话段落包含非语言节奏（沉默/动作/神态） |
| 情感债务可追踪 | 追读力报告能列出未表达情感的累积 |

### 9.2 叙述文学性验收

| 标准 | 检验方法 |
|---|---|
| 五层有深度 | 考古五层分析中，意层/潜层/韵层至少 2 层有内容 |
| 做减法生效 | deepen 后字数 ≤ 初稿字数 × 1.05（不应大幅增加） |
| 意象有生长 | 同一意象在多章出现，felt_meaning 有演化 |
| 无 AI 套路 | Anti-AI 扫描套路表达密度 < 2 处/千字 |

### 9.3 情感节奏验收

| 标准 | 检验方法 |
|---|---|
| 追读力达标 | 80% 章节追读力评分 ≥ 6 |
| 情感钩子优先 | 章末钩子中情感钩子占比 ≥ 50% |
| 张弛有度 | 无连续 3 章高张力或低张力（智能停会提醒） |
| 情感线连贯 | 考古发现的 emotional_leads 在后续章节有回响 |

### 9.4 工程验收

| 标准 | 检验方法 |
|---|---|
| main.py < 100 行 | 代码检查 |
| 九步管线串联 | 自动生成 3 章成功 |
| 熔断/检查点/智能停 | 各触发一次验证 |
| 桌面端可分发 | .msi 安装运行成功 |

---

## 10. 与两个参考项目的最终对照

| 维度 | webnovel-writer | PlotPilot | 本项目 v4 |
|---|---|---|---|
| 形态 | Claude Code 插件 | Tauri 桌面应用 | Tauri 桌面应用 ✅ |
| 架构 | Story System 主链 | DDD 五层 | DDD 分层 + 九步管线 ✅ |
| 情感核心 | 无 | 张力评分（间接） | **情感考古 + 五层 + 对话潜台词** ✅ |
| 对话处理 | 无 | POV 防火墙 | **对话潜台词分层挖掘** ✅ |
| 追读力 | Hook/债务 | 无 | **吸收 + 情感联动** ✅ |
| 修改哲学 | 做加法 | 做加法 | **做减法优先** ✅ |
| 提示词 | 硬编码 | YAML 20+ 接点 | YAML 9 接点 + 题材包 ✅ |
| 质量监控 | 审查维度 | 张力/漂移/陈词 | 考古+追读力+Anti-AI+漂移 ✅ |
| 熔断 | 断点恢复 | 熔断保护 | 熔断 + 检查点 + 智能停 ✅ |
| 题材扩展 | 37 模板 | 提示包目录 | 提示包目录 ✅ |
| 向量检索 | RAG | ChromaDB | 暂缓（MVP 够用） |
| 一致性 | Story System | 叙事状态机 | 叙事状态机 + 衔接包 ✅ |

---

## 附录 A：v4 相对 v3 的变更清单

| 变更 | v3 | v4 | 理由 |
|---|---|---|---|
| 管线步数 | 七步 | 九步 | 新增对话挖掘 + 追读力分析 |
| 对话处理 | 无 | dialogue_subtext_excavation | 对话是情感半壁江山 |
| 追读力 | 无 | analyze_reader_pull + 情感债务 | 吸收 webnovel-writer |
| 考古输出 | 线索清单 | 五层分析 | 文学性显式化 |
| 考古反馈 | 一次性消费 | 双向反馈（即时+纵向+横向） | v3 的缺口 |
| Anti-AI | 无 | anti_ai_polish | 吸收 webnovel-writer |
| 声线锚点 | 无 | voice_anchor in YAML | 吸收 PlotPilot |
| 文风漂移处理 | 定向修写 | 先考古理解再决定 | 做减法优先 |
| 情感气候 | 无 | emotional_climate（柔软参考） | 补 v2 的折中 |
| 架构 | 新增模块 | interfaces/application/engine/domain/workflows/infrastructure | 解决 main.py 巨石 |
| 叙事记忆 | 无 | narrative_memory 表 | 考古发现注入下一章 |

## 附录 B：不做什么（v4 明确排除）


| 风险 | 等级 | 对策 |
|---|---|---|
| 九步管线 LLM 调用成本高 | 中 | 关键步骤（draft/archaeology/deepen）必跑，其他可配置跳过 |
| 对话挖掘误判（把好的台词标为"说破"） | 中 | 产出给用户确认，不自动修改 |
| 考古五层分析过于主观 | 中 | 多视角交叉验证，单视角不触发加深 |
| 追读力与文学性冲突 | 低 | 追读力报告区分情感钩子 vs 情节钩子，优先前者 |
| main.py 重构引入回归 | 高 | Phase 0 保持 26 个测试通过，渐进式拆分 |
| Tauri sidecar 打包遗漏依赖 | 中 | PyInstaller --collect-all + 完整测试 |
| 情感考古让生成变慢 | 中 | 检查点策略可配，用户可介入加速 |
