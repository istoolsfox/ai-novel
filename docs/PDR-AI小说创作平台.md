# PDR · AI 小说创作平台

| 项 | 值 |
|---|---|
| 文档版本 | 1.0 |
| 创建日期 | 2026-07-01 |
| 状态 | 待实施 |
| 项目代号 | ai-novel-workbench |
| 仓库根目录 | `G:\ai小说` |

---

## 1. 项目概述

### 1.1 项目定位

**本地优先的 AI 长篇小说创作工作台。** 用 FastAPI + SQLite + React 构建一个不依赖云服务的小说创作工具，把"项目管理 / 创作资料 / AI 生成 / 记忆系统 / 导出"整合在一个本地应用里。

### 1.2 核心价值主张

1. **本地优先**：数据在本地 SQLite + 文件系统，不依赖云服务，隐私可控
2. **项目隔离**：每本小说独立的项目空间，章节、记忆、资料、导出全隔离
3. **AI 辅助创作**：从设定到大纲到正文的全链路 AI 工作流，支持任意 OpenAI-compatible 模型
4. **本地记忆系统**：参考 llmwiki 思路的项目级记忆目录，解决长篇创作的一致性问题
5. **情感深度增强**（本次重点）：通过"情感考古"架构，让 AI 生成有文学感染力的文字

### 1.3 当前痛点

| 痛点 | 描述 |
|------|------|
| **情感程式化** | AI 正文缺乏情感深度，平铺直叙，按部就班 |
| **角色扁平** | voice 字段存了但生成时未使用，对话工具人化 |
| **记忆粗糙** | 卷记忆是简单拼接，缺乏结构化检索 |
| **审查单一** | 只查事实一致性，不查情感深度 |

---

## 2. 现状基线

### 2.1 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| 后端框架 | FastAPI + uvicorn | - |
| 数据库 | SQLite | 嵌入式 |
| 前端框架 | React + TypeScript | React 19, TS 5.9 |
| 构建工具 | Vite | 7.1 |
| 流程图 | @xyflow/react | 12.9（关系图可视化） |
| 图标 | lucide-react | 0.468 |
| 测试 | pytest（后端）+ vitest（前端） | - |
| Python | 3.13 | - |
| Node | 22.22 | - |

### 2.2 代码规模

| 文件 | 行数 | 职责 |
|------|------|------|
| backend/app/main.py | 1813 | 全部 API 路由 + AI 工作流 + 业务逻辑 |
| backend/app/database.py | 185 | 数据模型 + CRUD 辅助 |
| backend/app/storage.py | 56 | 文件系统 + 项目目录管理 |
| backend/tests/test_mvp.py | 1053 | 后端测试 |
| frontend/src/ | - | 9 个组件 + App + api |

### 2.3 已有功能清单

#### 2.3.1 项目管理
- 创建/列表/详情/更新/删除项目
- 项目级隔离：章节、版本、评分、记忆、Wiki、导出均绑定项目
- 项目元数据：标题、题材、受众、调性、目标章节数、每章字数、logline、 synopsis

#### 2.3.2 章节工作台
- 章节创建/列表/详情/更新/删除
- 章节字段：编号、标题、大纲（brief）、正文（draft）、摘要（summary）、字数、状态、质量评分
- 候选版本管理：创建版本、列表、设为当前正文
- 定稿：锁定章节 + 自动生成摘要 + 写入记忆 + 重建卷记忆 + 同步 Wiki

#### 2.3.3 创作资料（通用记录系统）
通过 `GENERIC_TABLES` 统一管理的 13 类资料：
- model-configs（模型配置）
- model-task-routes（任务路由）
- character-profiles（人物档案）
- character-relationships（人物关系）
- world-settings（世界观设定）
- outlines（大纲）
- memory-items（记忆条目）
- timeline-events（时间线事件）
- foreshadowings（伏笔）
- style-profiles（风格档案）
- taboo-rules（雷点规则）
- knowledge-documents（知识库资料）
- prompt-templates（提示词模板）

每类资料统一提供 CRUD：`GET/POST /api/projects/{id}/{resource}`、`PATCH/DELETE /api/projects/{id}/{resource}/{record_id}`

#### 2.3.4 本地 Wiki 记忆
- 每个项目创建 `memory/raw_sources/`、`memory/wiki/`、`memory/index/` 目录
- Wiki 读写：`POST /wiki/write`、`POST /wiki/append`、`GET /wiki/read`
- Wiki 搜索：`GET /wiki/search`（简单文本匹配）
- Wiki 计数 / 修订历史 / lint 检查
- 定稿章节自动同步到 Wiki

#### 2.3.5 AI 工作流
统一入口 `POST /api/projects/{id}/ai/{workflow}`，已有工作流：

| 工作流 | 用途 |
|--------|------|
| generate_setting | 生成世界观设定 |
| generate_characters | 生成人物卡 |
| generate_outline | 生成总纲 |
| generate_chapter_directory | 生成章节目录 |
| generate_chapter_brief | 生成本章大纲 |
| generate_chapter_draft | 生成章节正文 |
| generate_chapter_variants | 生成候选版本 |
| summarize_chapter | 章节摘要 |
| extract_memory | 记忆提取 |
| extract_timeline_events | 时间线提取 |
| extract_relationships | 关系变化 |
| check_consistency | 一致性检查 |
| check_taboo_rules | 雷点检查 |
| analyze_style_sample | 风格分析 |
| revise_selection | 改写选段 |
| score_chapter | 章节评分 |

**双模式**：
- 无远程模型时：返回本地 stub（可编辑占位结果）
- 有远程模型时：调用 OpenAI-compatible API，自动装配上下文

#### 2.3.6 上下文装配
`build_generation_context` 自动聚合：章节信息、最近3章、卷记忆、防重复说明、角色、关系、大纲、风格、时间线、伏笔、雷点、知识库、Wiki 页面。

#### 2.3.7 导出
- Markdown / TXT：纯文本拼接
- DOCX：python-docx
- PDF：reportlab
- EPUB：ebooklib

#### 2.3.8 前端组件
- NovelEditorPage：章节编辑主界面
- CharacterWorkbench：人物工作台
- OutlineWorkbench：大纲工作台
- RelationshipGraphWorkbench：关系图（@xyflow/react）
- MemoryWorkbenches：记忆工作台
- StyleLearningPanel：风格学习面板
- AIResultCard：AI 结果展示卡

#### 2.3.9 认证
- OAuth 支持：openai / github / google / custom
- 简单 session 管理

---

## 3. 核心问题与目标

### 3.1 核心问题

**AI 生成的小说文本缺乏情感深度。** 表现为程式化、按部就班、机械式平铺直叙，无法生成具有强烈情感表达力和文学感染力的文字。

根因：现有生成管线把情感当"模型自由发挥的副产物"，而非"被显式建模、传递、注入、挖掘的一等公民"。

### 3.2 设计原则

> **情感不是被规划出来的，是被发现和加深的。**

采用"挖掘式"而非"规划式"：
1. **种子而非蓝图**：写前只给模糊入口，不规定节拍/技法/张力
2. **自由生长**：最少情感指令，允许偏离
3. **情感考古**（核心）：写后多视角深度阅读，发现隐藏层
4. **加深·藏回**：做减法 > 做加法
5. **跨章回溯**：后面发现的线索可回溯加深前面章节

### 3.3 项目目标

| 目标 | 度量 |
|------|------|
| 正文生成有情感方向感 | system prompt 注入情感种子引导 |
| 写后能发现隐藏情感层 | 情感考古工作流产出隐藏层地图 |
| 可定向加深而不破坏原文 | deepen_and_bury 工作流做减法优先 |
| 情感跨章连续 | emotional_leads 表 + 回溯加深机制 |
| 意象含义自然生长 | image_growth 追踪表，不预设含义 |
| 现有功能不回归 | 全部现有测试通过 |

---

## 4. 产品功能规划

### 4.1 功能全景

```
AI 小说创作平台
├── 项目管理（已有）
├── 章节工作台（已有）
│   ├── 章节编辑 / 版本 / 定稿（已有）
│   ├── 情感种子生成（新增 P1）
│   ├── 情感考古（新增 P0）
│   ├── 加深·藏回（新增 P1）
│   └── 跨章回溯加深（新增 P2）
├── 创作资料（已有，13类通用记录）
│   └── character-profiles 扩展情感字段（新增 P1）
├── 本地记忆系统（已有）
│   ├── Wiki 读写搜索（已有）
│   └── 意象生长追踪（新增 P2）
├── AI 工作流（已有 16 个 + 新增 5 个）
├── 导出（已有，5格式）
└── 认证（已有）
```

### 4.2 新增功能清单

| ID | 功能 | 类型 | 优先级 | 依赖 |
|----|------|------|--------|------|
| F1 | 情感种子生成 `generate_emotion_seed` | 新工作流 | P1 | - |
| F2 | 正文生成 prompt 注入种子 | 改造现有 | P1 | F1 |
| F3 | 情感考古 `emotion_archaeology` | 新工作流 | P0 | - |
| F4 | 加深·藏回 `deepen_and_bury` | 新工作流 | P1 | F3 |
| F5 | 意象生长追踪 `trace_image_growth` | 新工作流 | P2 | - |
| F6 | 跨章回溯加深 `retrospect_deepen` | 新工作流 | P2 | F3, F4 |
| F7 | 情感考古记录查询 API | 新接口 | P0 | F3 |
| F8 | 隐藏层地图查看 API | 新接口 | P0 | F3 |
| F9 | character-profiles 情感字段扩展 | 数据扩展 | P1 | - |

---

## 5. 系统架构

### 5.1 整体架构

```
┌─────────────────────────────────────────────┐
│  React 前端（Vite + TypeScript）              │
│  NovelEditorPage / CharacterWorkbench / ...  │
└──────────────────┬──────────────────────────┘
                   │ HTTP / JSON
┌──────────────────▼──────────────────────────┐
│  FastAPI 后端（main.py）                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ 项目/章节  │ │ 通用记录  │ │ AI 工作流    │ │
│  │ 管理      │ │ CRUD     │ │ 路由         │ │
│  └──────────┘ └──────────┘ └──────┬───────┘ │
│  ┌──────────┐ ┌──────────┐        │         │
│  │ Wiki 记忆 │ │ 导出     │        │         │
│  └──────────┘ └──────────┘        │         │
└───────────────────────────────────┼─────────┘
            │                       │
   ┌────────▼────────┐    ┌────────▼────────┐
   │  SQLite         │    │ OpenAI-compat   │
   │  app.db         │    │ 远程模型 / stub │
   │  + 4张新表      │    │                 │
   └─────────────────┘    └─────────────────┘
            │
   ┌────────▼────────┐
   │  文件系统         │
   │  data/projects/  │
   │  ├─ manuscript/  │
   │  ├─ memory/      │
   │  │  ├─ raw_sources/
   │  │  ├─ wiki/
   │  │  └─ index/
   │  ├─ exports/
   │  └─ backups/
   └─────────────────┘
```

### 5.2 AI 工作流架构

```
POST /api/projects/{id}/ai/{workflow}
        │
        ▼
┌─ run_ai_workflow ─────────────────────────┐
│  1. build_generation_context（装配上下文）  │
│  2. validate_workflow_prerequisites        │
│  3. run_model_or_stub                      │
│     ├─ 有模型配置 → compact → 远程调用      │
│     └─ 无模型配置 → build_stub_ai_output   │
│  4. 持久化到 ai_runs 表                    │
│  5. 特定工作流的额外持久化                  │
│     ├─ score_chapter → chapter_scores     │
│     ├─ generate_chapter_variants → versions│
│     ├─ emotion_archaeology → 考古表        │
│     └─ ...                                │
└───────────────────────────────────────────┘
```

### 5.3 情感深度增强架构（核心新增）

```
章节创作流程（增强后）：
  generate_chapter_brief（大纲）
        ↓
  generate_emotion_seed（情感种子）        ← 新增 P1
        ↓
  build_generation_context（含种子）       ← 改造
        ↓
  system_prompt_for_workflow（注入种子）   ← 改造
        ↓
  generate_chapter_draft（正文·自由生长）
        ↓
  emotion_archaeology（情感考古）          ← 新增 P0·核心
  ├─ 视角1：角色潜意识
  ├─ 视角2：读者体感
  └─ 视角3：母题回响
        ↓
  隐藏层地图
        ↓
  deepen_and_bury（加深·藏回）            ← 新增 P1
        ↓
  [定稿] trace_image_growth（意象追踪）    ← 新增 P2
        ↓
  跨章回溯：retrospect_deepen             ← 新增 P2
```

---

## 6. 数据模型设计

### 6.1 现有表（不动）

| 表 | 用途 | 关键字段 |
|----|------|---------|
| projects | 项目 | id, title, genre, audience, tone, logline, synopsis, project_root_path |
| chapters | 章节 | id, project_id, chapter_number, title, brief, draft, summary, status, quality_score |
| chapter_versions | 章节版本 | id, chapter_id, label, content, model |
| chapter_scores | 章节评分 | id, chapter_id, total_score, payload |
| wiki_pages | Wiki 页面 | id, project_id, path, title, content |
| wiki_page_revisions | Wiki 修订 | id, path, content, source_chapter_id |
| ai_runs | AI 运行记录 | id, project_id, workflow, input_snapshot, output_text, model, status |
| 通用表 ×13 | 创作资料 | id, project_id, title, category, content, payload, status |

### 6.2 新增表（情感深度增强）

在 `database.py` 的 `init_db()` 中新增：

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

### 6.3 数据扩展（不改表，扩展 payload）

character-profiles 的 payload 新增可选字段：

```json
{
  "name": "沈照夜",
  "voice": "短句、克制、少用感叹",
  "emotional_baseline": {
    "default_emotion": "警惕性克制",
    "emotional_range": ["冷静", "压抑的愤怒", "动摇", "决绝"],
    "trigger_map": {
      "被质疑动机": "压抑的愤怒 → 短句变碎句"
    },
    "defense_mechanism": "用反问挡回直白情绪",
    "unspoken_rules": "从不说'我害怕'"
  }
}
```

不强制所有角色都有 emotional_baseline——可选增量，有则用，无则不影响现有流程。

---

## 7. API 设计

### 7.1 现有 API（不动，共约30个端点）

| 分组 | 端点 |
|------|------|
| 健康 | `GET /api/health` |
| 认证 | `GET /api/auth/status`、OAuth start/callback、`POST /api/auth/logout` |
| 项目 | `POST/GET/PATCH/DELETE /api/projects` |
| 章节 | `POST/GET/PATCH/DELETE /api/projects/{id}/chapters` |
| 版本 | `POST/GET /api/projects/{id}/chapters/{cid}/versions`、`POST .../select` |
| 定稿 | `POST /api/projects/{id}/chapters/{cid}/finalize` |
| 通用记录 | `GET/POST /api/projects/{id}/{resource}`、`PATCH/DELETE .../{record_id}` |
| Wiki | write/append/read/search/count/revisions/lint |
| AI | `POST /api/projects/{id}/ai/test-connection`、`POST /api/projects/{id}/ai/{workflow}` |
| 导出 | markdown/txt/docx/pdf/epub |

### 7.2 新增 API

#### 7.2.1 新增工作流（复用现有路由）

```
POST /api/projects/{project_id}/ai/{workflow}
```

新增 workflow 值：

| workflow 值 | 功能 | 优先级 |
|-------------|------|--------|
| `generate_emotion_seed` | 生成情感种子 | P1 |
| `emotion_archaeology` | 情感考古（三视角深度阅读） | P0 |
| `deepen_and_bury` | 加深·藏回 | P1 |
| `trace_image_growth` | 意象生长追踪 | P2 |
| `retrospect_deepen` | 跨章回溯加深 | P2 |

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

差异化参数通过 `payload` 传递：
- `emotion_archaeology`：payload 可含 `view_mode`（triple/subconscious/reader/motif）
- `deepen_and_bury`：payload 可含 `selected_opportunities`（用户选定的加深项）
- `retrospect_deepen`：payload 含 `lead_id` + `target_chapter_ids`

#### 7.2.2 新增查询接口

```
GET   /api/projects/{project_id}/chapters/{chapter_id}/emotion-seed
GET   /api/projects/{project_id}/chapters/{chapter_id}/archaeology
GET   /api/projects/{project_id}/chapters/{chapter_id}/archaeology/{archaeology_id}
GET   /api/projects/{project_id}/emotional-leads?status=discovered
GET   /api/projects/{project_id}/emotional-leads/{lead_id}
PATCH /api/projects/{project_id}/emotional-leads/{lead_id}
GET   /api/projects/{project_id}/image-growth
GET   /api/projects/{project_id}/image-growth/{image_name}
```

### 7.3 持久化时机

| 工作流 | 完成后持久化 |
|--------|-------------|
| generate_emotion_seed | 写入 emotion_seeds 表 |
| emotion_archaeology | 写入 emotion_archaeology 表；强线索写入 emotional_leads 表 |
| deepen_and_bury | 更新 chapters.draft；修改说明存入 ai_runs |
| trace_image_growth | 写入 image_growth 表 |
| retrospect_deepen | 更新对应 chapters.draft；更新 emotional_leads.deepened_chapters |

---

## 8. AI 工作流详细设计

### 8.1 F1：情感种子生成

**时机**：`generate_chapter_brief` 之后、`generate_chapter_draft` 之前

**输出**：
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

**Prompt**：
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

### 8.2 F2：正文生成 prompt 注入种子

**改造**：`system_prompt_for_workflow`（main.py L1558）

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
    # ... 其他 workflow 不变
```

**灵魂**：最后一句"允许它偏离"。

### 8.3 F3：情感考古（核心）

**时机**：`generate_chapter_draft` 之后

**机制**：对同一段正文做三次独立深度阅读，每次切换视角，最后汇合。

**三个视角**：

**视角一·角色潜意识考古**：不分析情节，只盯着角色"没说什么"——动作、停顿、回避、反常行为。追问"这个角色自己都没意识到的，是什么？"

**视角二·读者体感考古**：切换到读者第一人称，不分析，只记录"读到哪儿时心里动了一下"——共振点、断裂点、沉默点。

**视角三·母题回响考古**：跳出本章，看全书反复出现的意象、动作、句子。哪些触及了可加深，哪些是新种子，哪些是未解之结。

**Prompt**（完整版见附录 A）产出"隐藏层地图"：

```json
{
  "chapter_id": "...",
  "subconscious_leads": [
    {"position": "第2段", "detail": "擦三遍桌子", "inferred": "用控制小动作压抑失控感", "why": "...", "depth": "can_deepen"}
  ],
  "reader_felt_map": {
    "resonance_points": [{"position": "第3段末", "felt": "心疼", "why": "..."}],
    "rupture_points": [{"position": "第6段", "issue": "该动但没动"}],
    "silence_points": [{"position": "第4段", "note": "好的留白，不要动"}]
  },
  "motif_echoes": {
    "existing_motifs": [{"motif": "留下/被需要", "chapter_touch": "...", "can_deepen": true}],
    "new_seeds": [{"image": "方形", "first_appearance": true, "potential": "..."}],
    "open_knots": [{"knot": "...", "chapter_bumped": true, "resolved": false}]
  },
  "deepen_opportunities": [
    "第2段的'擦三遍'已是好种子，可再压深——不要加字，反而删一个解释性的词"
  ]
}
```

**价值**：不是"哪里不达标要重写"，而是"哪里有矿可以加深"。

### 8.4 F4：加深·藏回

**原则**：做减法 > 做加法

**三种操作**：
- **加深（Deepen）**：把浮在表面的潜台词再压深一层。不是加情绪词，而是删解释性词语。
- **藏回（Bury）**：把过于明显的情感外露收回水线以下。
- **留白（Leave）**：silence_points 不动，那是文学性的最高形态。

**Prompt**：
```
你拿到一份章节正文和一份"隐藏层地图"。地图指出了已藏着但可以再深的潜力点。
你的任务不是重写，是加深。原则：
1. 做减法优先于做加法。能删一个解释性词语解决的，不要加一整句。
2. 把浮在表面的潜台词压下去。已经说出来的潜台词不算潜台词。
3. 保留留白点。silence_points 是好的，不要填满。
4. 不要追求"更动人"，追求"更藏"。越藏读者越能自己感到。
5. 只修改地图指出的位置，其他地方一个字不动。

返回 JSON：
{
  "revised_text": "修改后的完整正文",
  "changes": [{"position": "...", "before": "...", "after": "...", "reason": "..."}]
}
```

### 8.5 F5：意象生长追踪

**时机**：章节定稿时

**机制**：扫描正文识别重复元素（动作、物件、声音、天气），不指定含义，只记录出现史。含义由考古视角回望总结。

### 8.6 F6：跨章回溯加深

**时机**：情感考古发现强线索后

**机制**：
1. 根据 lead 内容检索已写章节里"已触及但未展开"的位置
2. 对选中章节调用 `deepen_and_bury`
3. 回溯前自动创建 chapter_versions 备份
4. 标记线索为已回溯加深

---

## 9. 记忆系统设计

### 9.1 现有机制（不动）

- **Wiki 目录**：`memory/wiki/` 下的 Markdown 文件，支持读写搜索
- **卷记忆**：`关键记忆.md`，定稿章节自动重建（拼接章节摘要）
- **通用记录**：memory_items 表，章节定稿时写入 chapter_summary
- **上下文装配**：`build_generation_context` 聚合 12 类上下文

### 9.2 新增机制

- **情感考古记录**：每次考古的隐藏层地图持久化，可回查历史
- **情感线索库**：跨章的情感线索，可追踪"已发现→已回溯加深"状态
- **意象出现史**：意象在哪些章节、什么情境下出现，含义如何演化

---

## 10. 前端架构

### 10.1 现有组件

| 组件 | 职责 |
|------|------|
| NovelEditorPage | 章节编辑主界面 |
| CharacterWorkbench | 人物档案管理 |
| OutlineWorkbench | 大纲管理 |
| RelationshipGraphWorkbench | 关系图可视化（@xyflow/react） |
| MemoryWorkbenches | 记忆/Wiki 管理 |
| StyleLearningPanel | 风格学习 |
| AIResultCard | AI 结果展示 |

### 10.2 前端改造建议（本次后端先行，前端后续）

- NovelEditorPage 增加"情感考古"按钮和隐藏层地图展示
- 章节工作台增加"情感种子"查看
- 新增"意象生长"视图（时间线展示意象出现史）
- AIResultCard 支持"加深·藏回"的 diff 展示

---

## 11. 代码改造点清单

### 11.1 database.py

| 改造点 | 位置 | 内容 |
|--------|------|------|
| `init_db()` | L56 | 新增 4 张表的 CREATE TABLE |
| 新增 CRUD 函数 | 文件末尾 | create/get/list archaeology/seed/lead/image_growth 等 |

### 11.2 main.py

| 改造点 | 位置 | 内容 |
|--------|------|------|
| `system_prompt_for_workflow` | L1558 | 增加 emotion_seed 参数（F2） |
| `build_generation_context` | L764 | 返回值增加 emotion_seed 字段 |
| `structured_output_for_workflow` | L1330 | 新增 5 个工作流的 stub |
| `build_stub_ai_output` | L1501 | titles 字典新增 5 项 |
| `run_ai_workflow` | L1177 | 新增 5 个工作流的持久化分支 |
| `compact_payload_for_remote` | L924 | 新工作流的 payload 压缩规则 |
| `run_model_or_stub` | L1580 | 传入 emotion_seed |
| 新增 API 路由 | 文件末尾 | 8 个查询接口 |

### 11.3 改造优先级

```
P0（MVP）：
  1. database.py 新增 emotion_archaeology 表 + CRUD
  2. main.py 新增 emotion_archaeology 工作流（prompt + stub + 路由 + 持久化）
  3. main.py 新增查询接口
  → 验收：写完一章后可跑情感考古，产出隐藏层地图

P1（种子 + 加深）：
  4. database.py 新增 emotion_seeds 表
  5. main.py 新增 generate_emotion_seed 工作流
  6. system_prompt_for_workflow 注入种子
  7. build_generation_context 聚合种子
  8. main.py 新增 deepen_and_bury 工作流
  → 验收：写前有种子入口，写后可定向加深

P2（跨章 + 意象）：
  9. database.py 新增 emotional_leads + image_growth 表
  10. main.py 新增 trace_image_growth + retrospect_deepen 工作流
  → 验收：跨章连续，意象生长
```

---

## 12. Stub 输出设计

在 `structured_output_for_workflow` 中为 5 个新工作流添加 stub（无远程模型时的占位）：

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
            {"position": "第2段", "detail": "（stub）角色重复某个动作",
             "inferred": "用控制小动作压抑内在波动",
             "why": "重复是过度的", "depth": "can_deepen"}
        ],
        "reader_felt_map": {
            "resonance_points": [{"position": "第3段末", "felt": "隐隐心疼", "why": "（stub）"}],
            "rupture_points": [],
            "silence_points": [{"position": "第4段", "note": "（stub）好的留白"}]
        },
        "motif_echoes": {
            "existing_motifs": [],
            "new_seeds": [{"image": "（stub）某物件", "first_appearance": True, "potential": "..."}],
            "open_knots": []
        },
        "deepen_opportunities": ["（stub）第2段可以做减法加深"]
    }

if workflow == "deepen_and_bury":
    return {
        "revised_text": payload.content or "（stub）加深后的正文",
        "changes": [{"position": "第2段", "before": "（原文）", "after": "（修改后）", "reason": "做减法"}]
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

## 13. 验收标准

### 13.1 P0 验收

| 验收项 | 标准 |
|--------|------|
| 数据库 | emotion_archaeology 表创建成功，CRUD 正常 |
| 工作流路由 | POST /api/projects/{id}/ai/emotion_archaeology 返回隐藏层地图 JSON |
| Stub | 无远程模型时返回合法 stub JSON |
| 远程模型 | 有远程模型时传入三视角 prompt，返回结构化隐藏层地图 |
| 持久化 | 考古记录写入 emotion_archaeology 表 |
| 查询接口 | GET archaeology 接口返回历史记录 |
| 不破坏现有 | 现有工作流全部正常，test_mvp.py 全通过 |

### 13.2 P1 验收

| 验收项 | 标准 |
|--------|------|
| 情感种子 | generate_emotion_seed 返回三字段 JSON |
| prompt 注入 | 正文生成 system prompt 含种子引导，含"允许偏离" |
| 种子持久化 | emotion_seeds 表读写正常 |
| 加深·藏回 | deepen_and_bury 返回修改后正文 + changes 说明 |
| 正文更新 | 加深后 chapters.draft 被更新 |

### 13.3 P2 验收

| 验收项 | 标准 |
|--------|------|
| 意象追踪 | trace_image_growth 写入 image_growth 表 |
| 线索管理 | emotional_leads 表 CRUD 正常 |
| 回溯加深 | retrospect_deepen 可对前序章节做加深 |
| 回溯备份 | 回溯前自动创建 chapter_versions 备份 |

---

## 14. 风险与对策

| 风险 | 等级 | 对策 |
|------|------|------|
| 考古 prompt 太长导致 token 超限 | 中 | 正文超长时分段考古；compact_value 已有截断机制 |
| 模型返回的隐藏层地图格式不规范 | 中 | parse_structured_ai_text 已有容错；stub 兜底 |
| 加深·藏回破坏原文叙事 | 中 | 只改指定位置；返回 changes 供审阅；不自动覆盖需确认 |
| 意象追踪误判 | 低 | 人工可编辑 image_growth 记录 |
| 回溯加深改坏前序章节 | 中 | 回溯前自动创建 chapter_versions 备份 |
| 现有功能回归 | 中 | 每阶段完成后跑 test_mvp.py |

---

## 15. 实施路线图

```
Phase 0（MVP·先跑通考古）：
  database.py: 新增 emotion_archaeology 表 + CRUD
  main.py: 新增 emotion_archaeology 工作流（prompt + stub + 路由 + 持久化）
  main.py: 新增查询接口
  验收 P0

Phase 1（种子 + 加深）：
  database.py: 新增 emotion_seeds 表
  main.py: generate_emotion_seed 工作流
  main.py: system_prompt_for_workflow 注入种子
  main.py: build_generation_context 聚合种子
  main.py: deepen_and_bury 工作流
  验收 P1

Phase 2（跨章 + 意象）：
  database.py: 新增 emotional_leads + image_growth 表
  main.py: trace_image_growth 工作流
  main.py: retrospect_deepen 工作流
  验收 P2
```

---

## 附录 A：情感考古完整 Prompt

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

---

## 附录 B：现有代码关键位置索引

| 文件 | 行号 | 函数/结构 | 说明 |
|------|------|----------|------|
| main.py | L87 | AiWorkflowIn | AI 工作流请求体（复用） |
| main.py | L110 | init_app | 初始化 |
| main.py | L183 | create_project | 项目创建 |
| main.py | L314 | 章节 CRUD | 章节 API |
| main.py | L466 | finalize_chapter | 章节定稿 |
| main.py | L764 | build_generation_context | 上下文装配（改造点） |
| main.py | L880 | compact_generation_context | 上下文压缩 |
| main.py | L924 | compact_payload_for_remote | payload 压缩（改造点） |
| main.py | L1177 | run_ai_workflow | AI 工作流入口（改造点） |
| main.py | L1225 | validate_workflow_prerequisites | 前置校验 |
| main.py | L1330 | structured_output_for_workflow | stub 输出（改造点） |
| main.py | L1453 | build_local_chapter_draft | 本地正文 stub |
| main.py | L1501 | build_stub_ai_output | stub 入口（改造点） |
| main.py | L1558 | system_prompt_for_workflow | prompt 生成（改造点） |
| main.py | L1580 | run_model_or_stub | 模型调用（改造点） |
| main.py | L1725 | export_* | 导出 |
| database.py | L56 | init_db | 建表（改造点） |
| database.py | L170 | GENERIC_TABLES | 通用表映射 |
| storage.py | L7 | data_root | 数据目录 |

---

## 附录 C：不做什么（明确排除）

- ❌ 不做情感蓝图（5节拍张力曲线）——v1 的错误
- ❌ 不做硬约束 prompt（必须命中/必须达到）
- ❌ 不做情感达标审查（打分 + 薄弱节拍）
- ❌ 不做情感强化改写（做加法）
- ❌ 不预设意象含义
- ❌ 不改现有 score_chapter（保留事实评分）
- ❌ 不强制所有角色都有 emotional_baseline（可选增量）
- ❌ 不改前端（本次后端先行，前端后续）
- ❌ 不引入新依赖（复用现有 FastAPI + SQLite）
- ❌ 不改现有数据表结构（新表独立，旧表 payload 扩展）
