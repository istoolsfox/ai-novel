# 全自动托管执行内核（阶段一）

本阶段只实现托管任务的持久化执行能力，不提前加入章节衔接、分层记忆、动态剧情图谱和影响传播。

## 已实现

- 持久化 `generation_jobs`
- 持久化 `generation_steps`
- 持久化 `generation_events`
- 自动创建缺失章节记录
- 顺序执行：
  1. `generate_chapter_brief`
  2. `generate_chapter_draft`
  3. `finalize_chapter`
- 自动失败重试
- 暂停、恢复、停止
- 失败步骤单独重试
- 服务启动时恢复 `queued` / `running` 任务
- SSE 任务状态流
- 每个步骤使用幂等键，已完成步骤不会重复执行

## API

```text
POST /api/projects/{project_id}/autopilot/start
GET  /api/projects/{project_id}/autopilot/status
GET  /api/projects/{project_id}/autopilot/jobs/{job_id}
POST /api/projects/{project_id}/autopilot/jobs/{job_id}/pause
POST /api/projects/{project_id}/autopilot/jobs/{job_id}/resume
POST /api/projects/{project_id}/autopilot/jobs/{job_id}/stop
POST /api/projects/{project_id}/autopilot/jobs/{job_id}/steps/{step_id}/retry
GET  /api/projects/{project_id}/autopilot/events
GET  /api/projects/{project_id}/autopilot/events/stream
```

启动示例：

```json
{
  "start_chapter": 1,
  "end_chapter": 10,
  "mode": "full_autopilot",
  "max_retries": 2
}
```

如果不传 `end_chapter`，系统会使用项目的 `target_chapter_count`。

## 环境变量

```text
AI_NOVEL_AUTOPILOT_RETRY_DELAY_SECONDS
```

自动重试等待时间，默认 2 秒，后续尝试会逐步增加，最高 30 秒。

```text
AI_NOVEL_AUTOPILOT_DISABLE_WORKER=1
```

只创建任务，不自动执行。主要用于测试和故障排查。

```text
AI_NOVEL_AUTOPILOT_SYNC=1
```

在当前请求中同步执行任务。只用于自动化测试，不建议生产使用。

## 当前限制

- Worker 暂时运行在 API 进程的后台线程中。
- 暂停不会强行中断正在进行的远程模型请求，而是在当前步骤返回后停止后续步骤。
- 当前仍复用现有章节定稿逻辑和基础章节摘要记忆。
- 暂未实现章节衔接包、人物知识边界、连贯性验证和自动局部修复。
- 暂未实现前端托管控制台。

后续阶段应把 Worker 拆成独立进程，并继续实现章节衔接和分层记忆。
