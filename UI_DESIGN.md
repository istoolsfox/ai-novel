# Novel OS — UI Design Specification v0.1

> 产品设计规范。frontend 负责落地；后端复用现有 FastAPI 模块（projects/chapters/records/story-graph/memory/autopilot）。

## 1. 产品定位

AI-native 的故事创作与项目管理平台。

核心目标：**让 AI 理解、管理并持续维护一个完整的故事世界。**

两种项目模式：

```text
Novel        → Volume / Chapter / Paragraph
Short Drama  → Season / Episode / Scene / Shot
```

共享 Story Engine：Story Bible / Characters / Relationships / World / Timeline / Plotlines / Foreshadowings / Story State。

## 2. 整体 UI 架构

桌面端三栏：

```text
┌────────────────────────────────────────────────────┐
│                   Top Bar (52px)                   │
├──────────┬─────────────────────┬─────────────────┤
│ Sidebar  │  Main Workspace     │  AI Panel       │
│ 220px    │  flex: 1            │  320px          │
└──────────┴─────────────────────┴─────────────────┘
```

AI Panel 按页面显示：Dashboard 无；Overview/Outline/Character 可折叠；Editor 默认；AI Studio 最大化。

## 3. 全局导航（Sidebar）

工作区分组：WORKSPACE（Dashboard/Projects）→ CURRENT PROJECT（Overview/Story/Outline/Characters/World/Relations/Timeline/Writing）→ AI（AI Studio）→ DATA（Assets/Analytics）→ Settings。

收缩态 64px，`⌘B` 切换。

## 4. 顶部 Top Bar

左 Breadcrumb（Projects / 雨夜玫瑰 / Chapter 38），中 ⌘K 搜索，右 Notifications/Help/User；编辑态显示 Saving…/Saved。

## 5. Dashboard

`/dashboard`：欢迎 + New Project；Recent Projects 卡（进度条）；Today（字数/章节/时长）；AI Insights（角色冲突/未尽伏笔/一致性）。

## 6. Project Overview

`/projects/:id`：项目进度、四指标（Characters/World/Plotlines/Foreshadowings）、最近章节（状态徽章）、Story Health（一致性分）。

## 7. Outline

`/projects/:id/outline`：Board / List 两模式；卡片显示 Chapter Number / Title / Summary / Plotlines / Characters / Conflict Level / Status。

## 8. Chapter Drawer

点击章节右滑打开：Status / Summary / Plotlines / Characters / Foreshadowings / AI 快捷动作。

## 9. Characters

`/projects/:id/characters`：左角色列表（MAIN/SUPPORTING 分组），右角色详情（Role/Personality/Current State/Goal/Character Arc/Appearances）+ AI。

## 10. Character AI

弹出 Character AI：Generate / Improve Personality / Backstory / Analyze Arc / Dialogue / Check OOC。

## 11. World

`/projects/:id/world`：Locations/Organizations/Companies/Families/Countries/Rules/Objects。

## 12. Relations

`/projects/:id/relations`：关系图（Auto Layout/Filter/AI Analyze）；点击关系看 Relationship/Intensity/State/History。

## 13. Timeline

`/projects/:id/timeline`：横向时间轴，支持 Zoom/Filter/Character/Plotline/Chapter。

## 14. Writing Editor

`/projects/:id/writing/:chapterId`：左章节树 + 中央编辑器（Notion/Typora 式）+ 右 AI Copilot。

## 15. AI Copilot

Context（14 sources）+ 当前章节 + Characters + Current State + Active Plotlines + Foreshadowings + Quick Actions（Continue/Rewrite/Expand/Polish/Dialogue/Logic Check）。

## 16. AI Context Drawer

展开 sources：Chapter/Characters/World/Plot/Timeline/Foreshadowings 来源列表（对应 Context Builder）。

## 17. AI Studio

`/projects/:id/ai`：自然语言描述 + Genre/Format/Episodes/Duration → Generate。

## 18. AI Generation Pipeline

不用 Loading spinner，用步骤列表（Concept→Bible→Characters→World→Outline→...）+ Pause/Stop/Review/Continue。

## 19. 短剧模式

Short Drama 项目导航：Episode/Scene/Shot；Scene→Shot→Generate Video Prompt（对接触视频模型）。

## 20. AI 一致性中心

Consistency Center：Overall Health + 分类问题列表（Characters/Timeline/World/Plot/Foreshadowing）；逐条 Ignore/Fix/View Context。

## 21. 全局 Command Palette

⌘K：Open Chapter 38 / Create Character / Generate Outline / Continue Writing / Check Consistency / 等。

## 22. 快捷键

⌘K Command Palette · ⌘B Sidebar · ⌘J AI Panel · ⌘S Save · ⌘Enter AI Generate · ⌘Shift P Polish · ⌘Shift R Rewrite · ⌘Shift C Continue · Esc Drawer · ↑/↓ Chapter nav。

## 23. Design System（墨纸 Ink & Paper · 已实施）

- 字体：标题衬线（Songti SC / Noto Serif SC / Georgia）；正文 UI 无衬线（PingFang SC / system-ui）
- 字号：Body 14 / Small 12.5 / 页标题 27（衬线）/ 卡片题 14
- Spacing：页面内边距 40/48，卡片内边距 22，卡片间距 16，区块间距 32
- Radius：6（控件）/ 10（弹层）/ 14（卡片）
- Border：1px 发丝线 #E7E2D5；阴影极轻，仅弹层用大阴影
- AI 内容视觉：统一紫 #6D5ACD（AI 按钮 / AI Generated 左边线 / AI 徽标）

## 24. Color System（tokens 见 frontend/src/styles/theme.css）

```text
--paper   #F6F4EF  页面底（暖纸）
--surface #FFFDF9  卡片
--ink     #232019  主墨 / #5F594D 次墨 / #9A937F 弱墨
--line    #E7E2D5  发丝线
--accent  #B4432C  朱砂（主按钮 / 激活态 / 关键强调）
--ai      #6D5ACD  AI 紫（仅 AI 相关元素）
--ok      #4A7C59 / --warn #A8742A / --danger #A8321F
```

## 25. AI 内容视觉区分

AI 生成内容标 "AI Generated"，带 Accept / Reject / Edit，不直接写入正文。

## 26. 路由

`/dashboard` · `/projects/:projectId/{overview,story,characters,world,relations,timeline,outline,writing,:chapterId,ai,consistency,assets,analytics}` · `/settings`；短剧项目加 episodes/scenes/shots/video-prompts。

## 27. 数据模型第一版

Project → StoryBible / Character[] / Relationship[] / WorldEntity[] / TimelineEvent[] / Plotline[] / Foreshadowing[] / Volume[]→Chapter[]→Scene[] / Document[] / AIJob[] / ConsistencyIssue[]。

核心原则：**不要把故事内容只存成 Markdown**，DB 必须结构化实体。

## 28. AI 架构

User → AI Request → Context Builder → Retriever → Story State → Prompt Builder → LLM Router → Structured Output → Validator → DB。点「继续写」= 组装上下文而非裸 prompt。

## 29. 开发顺序（MVP 一次不要全做完）

```text
PHASE 1  App Shell / Dashboard / Project / Characters / Outline / Writing Editor / AI Copilot
PHASE 2  World / Relations / Timeline / Consistency / Story State
PHASE 3  Short Drama / Episode / Scene / Shot / Video Prompt / AI Pipeline
```

## 30. 最终形态

NOVEL OS：Story Engine（Characters/World/Timeline/Plotlines/Relations）+ AI Context Engine（Generate/Analyze/Validate）。Novel 与 Short Drama 只是两个输出层，底层共享 Story Engine。
