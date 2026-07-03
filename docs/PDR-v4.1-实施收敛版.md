# PDR v4.1 · 全流程托管 AI 小说生成平台实施收敛版

| 项 | 值 |
|---|---|
| 文档版本 | 4.1 |
| 创建日期 | 2026-07-03 |
| 状态 | 实施基线 |
| 仓库根目录 | `G:\ai小说` |
| 上游愿景文档 | `docs/PDR-v4-全流程托管情感深度版.md` |

## 1. 本版为什么存在

v4 的产品方向成立：全流程托管、长篇防烂尾、情感考古、对话潜台词、追读力债务和本地桌面化，都是这个项目真正有辨识度的部分。

但 v4 文档里的执行基线已经过期。当前仓库已经具备以下事实：

- 后端已存在 `interfaces/application/engine/domain/workflows/infrastructure` 分层。
- `backend/app/main.py` 已经是兼容 shim，不再是 2428 行业务巨石。
- 后端已有 `StoryPipeline`、`Orchestrator`、`generation_jobs`、`chapter_generation_steps`、`narrative_memory` 等托管雏形。
- 前端已经是 Vue 3 + Naive UI + ECharts + Pinia + Vue Router，不再需要从 React 清理重建。
- `prompt_packages/_base` 已经存在 10 个 YAML 提示词包。

因此 v4.1 不再把任务定义为“从零重构”，而是定义为：**基于现有 v4 雏形，修正文档口径，补齐可运行、可恢复、可验证的托管生成 MVP，然后逐步增强情感深度。**

## 2. 第一性目标

本项目的核心验收不是“界面多漂亮”或“架构多分层”，而是：

> 平台能托管生成一部不会烂尾的小说，正文是真正文稿，记忆层只保存关键事实和摘要，任务可断点恢复，出现失败能诊断和停机。

## 3. v4.1 分阶段目标

### PlotPilot 参考边界

`PlotPilot` 可以作为产品和流程参考，重点借鉴：

- 分阶段规划、写作、检查和导出的托管链路。
- 长任务的检查点、恢复和质量门禁。
- 将故事设定、章节计划、正文产物分层管理。

但当前项目不直接照搬其技术栈或界面结构。现有 Vue 3 / FastAPI / SQLite / 本地文件记忆层已经具备可继续演进的基础，v4.1 的策略是保留这套基础，优先补齐自动生成闭环。

### Phase A：基线校准和托管 MVP

目标：让现有分层和托管骨架稳定跑通。

范围：

- 校准 v4 文档中已过期的基线描述。
- 保留现有 Vue 前端，不再清理重建。
- 保留现有后端分层，不再大拆 `main.py`。
- 修正 job / pipeline / SSE / step 记录中的字段和事件不一致问题。
- 支持三档生成模式：
  - `fast`：跳过可选分析步骤，优先验证多章正文闭环。
  - `standard`：保留关键情感检查，适合日常托管。
  - `deep`：完整九步，适合重点章节或最终质量打磨。
- 验证 3 章托管任务能完成、定稿、写入关键记忆。

不做：

- 不做 Tauri 打包。
- 不做完整 100 章压测。
- 不做全量情感报告 UI。

### Phase B：15 章完结压测

目标：证明平台能生成有结尾的短篇/中篇闭环。

验收：

- 从蓝图/大纲出发生成 15 章。
- 每章是正文，不是建议、提纲或剧情板。
- 最后一章有明确收束。
- `llmwiki` 不保存整章正文，只保存关键记忆、时间线、伏笔、章摘要、衔接包和叙事记忆。
- 导出 Markdown/TXT 能读取完整正文。

### Phase C：情感深度增强

目标：把 v4 的文学性差异化做成可控增强，而不是默认拖慢所有任务。

范围：

- 对话潜台词地图。
- 五层情感考古。
- 追读力报告。
- `deepen_and_bury` 优先 patch/span edits，避免默认整章重写。
- Anti-AI 终检。
- 叙事记忆注入下一章种子。

验收：

- 结构化报告可查。
- deepen 后不大幅增字，默认 `revised_length <= original_length * 1.05`。
- 对话中“说破潜台词”的位置能被识别并藏回。

### Phase D：桌面化和长期分发

目标：Tauri sidecar + Windows 安装包。

前提：

- Phase A/B/C 的 Web 形态已经稳定。
- 本地数据目录、模型配置、日志路径和故障诊断已明确。

## 4. 托管生成 MVP 的硬边界

### 4.1 llmwiki 边界

`llmwiki` 是长篇记忆层，不是正文仓库。

允许写入：

- `关键记忆.md`
- `outline.md`
- `timeline.md`
- `foreshadowing.md`
- `taboo-rules.md`
- `relationships.md`
- `characters/*.md`
- `knowledge/*.md`
- `chapter_bridges` / narrative memory 对应摘要页

禁止写入：

- 整章正文聚合页。
- 每章完整正文副本。
- 重复的大段模型输出。

正文权威来源只能是：

- `chapters.draft`
- 版本表
- 导出文件

### 4.2 任务模式

`generation_jobs.params_json` 支持：

```json
{
  "generation_mode": "fast|standard|deep",
  "skip_steps": ["dialogue", "reader_pull", "anti_ai"]
}
```

优先级：

1. 显式 `skip_steps`
2. `generation_mode`
3. 默认 `standard`

模式默认：

- `fast`：跳过 `dialogue`、`reader_pull`、`anti_ai`。
- `standard`：跳过 `dialogue`、`reader_pull`、`anti_ai`，保留 `archaeology` 和 `deepen`。
- `deep`：不跳过。

### 4.3 断点恢复

恢复任务时：

- 已完成所有必需步骤的章节不重跑。
- 未完成章节从第一个未完成步骤继续是后续目标；MVP 可先从章节粒度恢复。
- 步骤判断必须使用 `chapter_generation_steps.step_status`，不能使用不存在的 `status` 或 `step_index` 字段。

### 4.4 SSE 事件契约

后端事件：

- `job_started`
- `chapter_started`
- `step`
- `chapter_completed`
- `checkpoint`
- `smart_stop`
- `chapter_failed`
- `completed`
- `done`

前端必须按这个契约渲染，不再使用旧的 `step_start` / `step_done` / `chapter_start` / `chapter_done` 命名。

### 4.5 模型配置契约

模型连接测试不能只验证临时表单值。用户在设置页测试成功后，必须把配置保存到当前项目的 `model_configs`，并标记为默认模型：

- `payload.provider`
- `payload.api_key`
- `payload.base_url`
- `payload.model_name`
- `payload.is_default = true`

章节生成、蓝图生成和情感增强工作流读取同一个默认配置。否则会出现“设置页显示连接成功，但托管生成仍走 fallback stub”的断裂体验。

## 5. 第一轮验收清单

- `pytest backend/tests/test_mvp.py` 通过。
- `npm run build` 通过。
- 能通过 API 启动一个 3 章托管任务。
- job 完成后：
  - `generation_jobs.status = completed`
  - 每章有 `draft`
  - 每章可定稿或已经定稿
  - `chapter_generation_steps` 有步骤记录
  - `关键记忆.md` 存在且不包含整章正文
- 前端进度页能显示真实后端 SSE 事件。

## 6. 后续保留的 v4 愿景

v4 的完整情感深度方案仍然有效，但它是增强层，不是 Phase A 的入口条件。完整愿景继续保留在 `docs/PDR-v4-全流程托管情感深度版.md` 中。
