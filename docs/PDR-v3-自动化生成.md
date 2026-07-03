# PDR v3 · AI 自动化长篇小说生成平台

| 项 | 值 |
|---|---|
| 文档版本 | 3.0 |
| 创建日期 | 2026-07-01 |
| 状态 | 待实施 |
| 项目代号 | ai-novel-workbench |
| 仓库根目录 | `G:\ai小说` |
| 前置文档 | `docs/PDR-AI小说创作平台.md`（v1）、`docs/PDR-桌面化改造.md`（v2） |

> **本版推翻 v1/v2 的"单章手动生成"范式，改为"批量自动化生成 + 用户调控"范式。**
> 用户设定方向和约束，AI 自动跑通"大纲 → 种子 → 正文 → 考古 → 加深 → 衔接包 → 下一章"的完整循环，一次产出 N 章。用户在每个检查点可以介入调整，但不必逐章手动点击。

---

## 1. 项目定位重述

### 1.1 v1/v2 的问题

v1/v2 的 PDR 虽然加了情感考古、衔接包等机制，但**工作方式仍然是单章手动**：
- 用户点"生成大纲" → 看一眼 → 点"生成种子" → 看一眼 → 点"生成正文" → 看一眼 → 点"定稿" → 再去下一章重复
- 一章要点 5-6 次，十章要点 50-60 次
- 用户反馈："一章一章生成效率太低了"

### 1.2 v3 的核心转变

> **从"用户驱动每一步"变为"AI 驱动整个循环，用户在检查点调控"。**

用户只需要：
1. 设定**卷级宏观蓝图**（这一卷要讲什么、情感走向、要埋的伏笔）
2. 设定**生成参数**（生成几章、每章字数、自动定稿还是停在草稿）
3. 点"开始自动生成"
4. AI 自动跑完 N 章的完整管线
5. 用户在关键节点收到**检查点通知**，可以介入调整，也可以直接放行

---

## 2. 自动化生成管线

### 2.1 单章管线（自动化版）

每一章的生成不再需要用户逐步点击，而是由"编排器"（Orchestrator）自动串联：

```
[输入：章节号 + 宏观蓝图 + 上一章衔接包]

  1. generate_chapter_brief       ← 生成本章大纲（含衔接包承接）
  2. generate_emotion_seed        ← 生成情感种子
  3. generate_chapter_draft       ← 生成正文（含种子 + 衔接包）
  4. emotion_archaeology          ← 情感考古（三视角深度阅读）
  5. deepen_and_bury              ← 加深·藏回（做减法）
  6. summarize_chapter            ← 生成摘要
  7. generate_chapter_bridge      ← 生成衔接包（供下一章承接）
  8. [可选] extract_timeline_events / extract_relationships / trace_image_growth
  9. [可选] finalize_chapter      ← 自动定稿 or 停在草稿

[输出：完成的章节 + 衔接包 + 考古记录 + 衍生记录]
```

**关键**：步骤 1-7 是自动串联的，用户不介入。步骤 8-9 根据用户设定的参数决定是否自动执行。

### 2.2 批量管线（多章自动循环）

```
[用户设定]
  - 起始章号 N
  - 生成章数 K（如 10）
  - 每章字数（如 3000）
  - 自动定稿：是/否
  - 检查点策略：每章停 / 每3章停 / 全程不停

[自动循环]
  for i in range(K):
    chapter = run_single_chapter_pipeline(N + i)
    if should_checkpoint(i):
      notify_user(chapter)  # 推送检查点
      wait_for_user_review_or_auto_continue()
    if auto_finalize:
      finalize_chapter(chapter)

[输出]
  - K 章完整章节（草稿 or 定稿）
  - K 个衔接包（链式传递）
  - K 份考古记录
  - K 份情感种子
  - 衍生的时间线/关系/意象记录
```

### 2.3 检查点机制

用户不必盯着每一章，但需要在关键节点有"刹车"：

| 检查点策略 | 触发时机 | 用户操作 |
|-----------|---------|---------|
| `每章停` | 每章管线跑完后 | 用户审阅后点"继续" |
| `每3章停` | 每 3 章后 | 用户审阅 3 章后点"继续" |
| `全程不停` | 全部跑完才停 | 事后统一审阅 |
| `智能停` | 检测到质量问题/衔接断裂/伏笔冲突时自动停 | 用户介入修复 |

**智能停的触发条件**（自动刹车）：
- 考古发现的 `rupture_points`（情感断裂点）超过 3 个
- 衔接包的 `open_hooks` 累积超过 8 个未回收
- 正文与上一章的语义相似度过低（衔接断裂）
- 字数偏差超过目标 ±30%
- 检测到重复事件（与卷记忆撞车）

---

## 3. 宏观蓝图（Volume Blueprint）

### 3.1 为什么需要宏观蓝图

单章管线再自动化，如果不知道"这一卷整体要往哪走"，AI 也会跑偏。宏观蓝图是**卷级的方向设定**，让每一章的生成都有宏观指引。

### 3.2 蓝图数据结构

```json
{
  "volume_number": 1,
  "volume_title": "第一卷 · 灰塔苏醒",
  "volume_arc": "主角发现记忆被篡改，从被动受害者变为主动追查者，但第一次追查就付出代价",
  "chapter_range": { "start": 1, "end": 20 },
  "emotional_trajectory": {
    "shape": "rise-fall-rise",
    "chapters": [
      { "range": "1-5", "emotion": "迷茫→警觉", "intensity": 3 },
      { "range": "6-10", "emotion": "警觉→愤怒", "intensity": 6 },
      { "range": "11-15", "emotion": "愤怒→动摇", "intensity": 7 },
      { "range": "16-20", "emotion": "动摇→决绝", "intensity": 8 }
    ]
  },
  "key_foreshadowings": [
    { "id": "fs_01", "planted_in": 3, "payoff_in": 18, "content": "裂开的印章" },
    { "id": "fs_02", "planted_in": 7, "payoff_in": 20, "content": "守夜人的真实身份" }
  ],
  "character_arcs": [
    {
      "character": "沈照夜",
      "start_state": "被动、不信任自己",
      "end_state": "主动、承担代价",
      "turning_point": "第12章发现盟友隐瞒"
    }
  ],
  "recurring_motifs": ["雨声", "印章", "抽屉", "签名"],
  "taboo_list": ["不要让主角在10章前就知道真相", "不要让守夜人在15章前暴露身份"],
  "generation_params": {
    "words_per_chapter": 3000,
    "auto_finalize": false,
    "checkpoint_strategy": "every_3",
    "auto_run_side_extractions": true
  }
}
```

### 3.3 蓝图的作用

- **单章生成时**：`generate_chapter_brief` 会参考蓝图，知道"这一章在大弧线里的位置"和"该埋什么伏笔"
- **情感种子生成时**：参考 `emotional_trajectory`，知道"这一章的情绪应该在哪个区间"
- **检查点判断时**：`智能停` 会比对"实际伏笔回收情况 vs 蓝图规划"
- **跨章一致性**：蓝图是宏观真源，单章偏离时系统会预警

---

## 4. 编排器（Orchestrator）

### 4.1 编排器职责

编排器是自动化管线的核心，负责：

1. **管线调度**：按顺序调用 7 个工作流，传递上下文
2. **状态管理**：跟踪每章的生成进度（brief/draft/archaeology/deepened/finalized）
3. **检查点控制**：根据策略决定是否暂停等用户
4. **错误恢复**：某步失败时决定重试/跳过/中止
5. **进度推送**：通过 SSE/WebSocket 实时推送进度给前端

### 4.2 编排器数据模型

```sql
-- 自动化生成任务
CREATE TABLE IF NOT EXISTS generation_jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    volume_blueprint_id TEXT,
    start_chapter_number INTEGER NOT NULL,
    target_chapter_count INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending/running/paused/completed/failed
    current_chapter_number INTEGER DEFAULT 0,
    current_step TEXT DEFAULT '',    -- brief/seed/draft/archaeology/deepen/summarize/bridge/finalize
    checkpoint_strategy TEXT DEFAULT 'every_3',
    auto_finalize INTEGER DEFAULT 0,
    params_json TEXT DEFAULT '{}',
    error_message TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

-- 每章的生成步骤记录
CREATE TABLE IF NOT EXISTS chapter_generation_steps (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    chapter_number INTEGER NOT NULL,
    step_name TEXT NOT NULL,        -- brief/seed/draft/archaeology/deepen/summarize/bridge/finalize
    step_status TEXT DEFAULT 'pending',  -- pending/running/completed/failed/skipped
    step_output TEXT DEFAULT '{}',   -- 该步骤的输出摘要
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT DEFAULT '',
    FOREIGN KEY(job_id) REFERENCES generation_jobs(id)
);

-- 卷级宏观蓝图
CREATE TABLE IF NOT EXISTS volume_blueprints (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    volume_number INTEGER DEFAULT 1,
    volume_title TEXT DEFAULT '',
    volume_arc TEXT DEFAULT '',
    chapter_range_start INTEGER DEFAULT 1,
    chapter_range_end INTEGER DEFAULT 20,
    blueprint_json TEXT DEFAULT '{}',
    status TEXT DEFAULT 'draft',     -- draft/approved/active/completed
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);
```

### 4.3 编排器 API

```
POST   /api/projects/{pid}/blueprints                    创建宏观蓝图
GET    /api/projects/{pid}/blueprints                    列出蓝图
GET    /api/projects/{pid}/blueprints/{bid}              查看蓝图
PATCH  /api/projects/{pid}/blueprints/{bid}              更新蓝图
POST   /api/projects/{pid}/blueprints/{bid}/approve      批准蓝图（status→active）

POST   /api/projects/{pid}/jobs                          启动自动化生成任务
       body: { blueprint_id, start_chapter, count, checkpoint_strategy, auto_finalize, params }
GET    /api/projects/{pid}/jobs                          列出任务
GET    /api/projects/{pid}/jobs/{job_id}                 查看任务进度
POST   /api/projects/{pid}/jobs/{job_id}/pause           暂停任务
POST   /api/projects/{pid}/jobs/{job_id}/resume          恢复任务
POST   /api/projects/{pid}/jobs/{job_id}/abort           中止任务
POST   /api/projects/{pid}/jobs/{job_id}/checkpoint/continue  检查点放行
GET    /api/projects/{pid}/jobs/{job_id}/steps           查看步骤明细

GET    /api/projects/{pid}/jobs/{job_id}/stream          SSE 实时进度流
```

---

## 5. 自动化工作流详细设计

### 5.1 编排器主循环（orchestrator.py）

```python
def run_generation_job(job_id: str):
    job = get_job(job_id)
    blueprint = get_blueprint(job.blueprint_id)
    
    for chapter_offset in range(job.target_chapter_count):
        chapter_number = job.start_chapter_number + chapter_offset
        
        # 检查暂停
        if job.status == 'paused':
            wait_for_resume(job_id)
        
        # 检查检查点放行
        if job.pending_checkpoint:
            wait_for_checkpoint_continue(job_id)
        
        # 跑单章管线
        chapter = run_single_chapter_pipeline(
            project_id=job.project_id,
            chapter_number=chapter_number,
            blueprint=blueprint,
            job_id=job_id,
        )
        
        # 更新进度
        update_job_progress(job_id, chapter_number)
        
        # 智能停检测
        if should_smart_stop(chapter):
            pause_job_with_reason(job_id, "smart_stop", reason)
            notify_user(job_id, "smart_stop", chapter)
            wait_for_user_intervention(job_id)
        
        # 检查点
        elif hit_checkpoint(job.checkpoint_strategy, chapter_offset):
            pause_job_with_reason(job_id, "checkpoint", chapter)
            notify_user(job_id, "checkpoint", chapter)
            wait_for_checkpoint_continue(job_id)
        
        # 自动定稿
        if job.auto_finalize:
            finalize_chapter(job.project_id, chapter.id)
    
    complete_job(job_id)


def run_single_chapter_pipeline(project_id, chapter_number, blueprint, job_id):
    """单章完整管线，7 步自动串联。"""
    
    # 创建章节记录
    chapter = create_chapter(project_id, chapter_number, title=f"第 {chapter_number} 章")
    
    # Step 1: 大纲
    record_step(job_id, chapter.id, "brief", "running")
    brief_output = call_workflow(project_id, "generate_chapter_brief", {
        chapter_id: chapter.id,
        prompt: f"第{chapter_number}章，参考蓝图：{blueprint.volume_arc}",
    })
    update_chapter_brief(chapter.id, brief_output)
    record_step(job_id, chapter.id, "brief", "completed")
    
    # Step 2: 情感种子
    record_step(job_id, chapter.id, "seed", "running")
    seed_output = call_workflow(project_id, "generate_emotion_seed", {
        chapter_id: chapter.id,
    })
    # 种子已在上一步持久化
    record_step(job_id, chapter.id, "seed", "completed")
    
    # Step 3: 正文
    record_step(job_id, chapter.id, "draft", "running")
    draft_output = call_workflow(project_id, "generate_chapter_draft", {
        chapter_id: chapter.id,
        prompt: f"目标字数：{blueprint.params.words_per_chapter}",
    })
    update_chapter_draft(chapter.id, draft_output.text)
    record_step(job_id, chapter.id, "draft", "completed")
    
    # Step 4: 情感考古
    record_step(job_id, chapter.id, "archaeology", "running")
    arch_output = call_workflow(project_id, "emotion_archaeology", {
        chapter_id: chapter.id,
        content: draft_output.text,
    })
    record_step(job_id, chapter.id, "archaeology", "completed")
    
    # Step 5: 加深·藏回
    record_step(job_id, chapter.id, "deepen", "running")
    deepen_output = call_workflow(project_id, "deepen_and_bury", {
        chapter_id: chapter.id,
        content: draft_output.text,
    })
    # deepen 已更新 chapter.draft
    record_step(job_id, chapter.id, "deepen", "completed")
    
    # Step 6: 摘要
    record_step(job_id, chapter.id, "summarize", "running")
    summary_output = call_workflow(project_id, "summarize_chapter", {
        chapter_id: chapter.id,
        content: deepen_output.revised_text,
    })
    update_chapter_summary(chapter.id, summary_output.text)
    record_step(job_id, chapter.id, "summarize", "completed")
    
    # Step 7: 衔接包
    record_step(job_id, chapter.id, "bridge", "running")
    bridge_output = call_workflow(project_id, "generate_chapter_bridge", {
        chapter_id: chapter.id,
        content: deepen_output.revised_text,
    })
    record_step(job_id, chapter.id, "bridge", "completed")
    
    # Step 8（可选）: 衍生提取
    if blueprint.params.auto_run_side_extractions:
        call_workflow(project_id, "extract_timeline_events", {chapter_id: chapter.id})
        call_workflow(project_id, "extract_relationships", {chapter_id: chapter.id})
        call_workflow(project_id, "trace_image_growth", {chapter_id: chapter.id})
    
    return chapter
```

### 5.2 智能停检测

```python
def should_smart_stop(chapter) -> tuple[bool, str]:
    """检测是否需要智能刹车。返回 (是否停, 原因)。"""
    
    # 1. 考古断裂点过多
    archaeology = get_latest_archaeology(chapter.project_id, chapter.id)
    if archaeology:
        ruptures = archaeology.reader_felt_map.rupture_points
        if len(ruptures) > 3:
            return True, f"情感断裂点 {len(ruptures)} 个，超过阈值 3"
    
    # 2. 未回收钩子累积过多
    all_bridges = list_chapter_bridges(chapter.project_id)
    total_open_hooks = sum(len(b.open_hooks) for b in all_bridges)
    if total_open_hooks > 8:
        return True, f"未回收钩子累积 {total_open_hooks} 个，超过阈值 8"
    
    # 3. 字数偏差
    target = blueprint.params.words_per_chapter
    actual = len(chapter.draft)
    if actual < target * 0.7 or actual > target * 1.3:
        return True, f"字数偏差过大：目标 {target}，实际 {actual}"
    
    # 4. 与上一章语义相似度过低（衔接断裂）
    prev_bridge = get_previous_chapter_bridge(chapter.project_id, chapter.chapter_number)
    if prev_bridge and not has_reasonable_continuity(prev_bridge, chapter.draft):
        return True, "与上一章衔接度不足，可能存在跳跃"
    
    return False, ""
```

---

## 6. 前端改造

### 6.1 新增页面：自动化生成控制台

```
自动化生成控制台
├── 宏观蓝图编辑器
│   ├── 卷级弧线设定
│   ├── 情感走向曲线（可视化）
│   ├── 伏笔规划表
│   ├── 角色弧线设定
│   └── 生成参数
├── 任务启动面板
│   ├── 选择蓝图
│   ├── 起始章号
│   ├── 生成章数
│   ├── 检查点策略
│   ├── 自动定稿
│   └── [开始生成]按钮
├── 实时进度面板
│   ├── 当前章号 / 总章数
│   ├── 当前步骤（brief/seed/draft/...）
│   ├── 步骤明细列表（每章每步的状态）
│   ├── SSE 实时日志流
│   └── [暂停][恢复][中止]按钮
├── 检查点通知
│   ├── 触发的检查点类型（手动/智能停）
│   ├── 触发原因
│   ├── 本章预览
│   └── [放行][介入调整][中止]按钮
└── 生成结果总览
    ├── 已生成章节列表
    ├── 衔接包链
    ├── 考古记录汇总
    └── 伏笔回收情况
```

### 6.2 前端组件

| 组件 | 职责 |
|------|------|
| `BlueprintEditor.tsx` | 宏观蓝图编辑（表单 + 情感曲线可视化） |
| `JobLauncher.tsx` | 任务启动面板 |
| `JobProgressPanel.tsx` | 实时进度（SSE 流 + 步骤明细） |
| `CheckpointNotification.tsx` | 检查点通知弹窗 |
| `JobResultOverview.tsx` | 生成结果总览 |

---

## 7. 数据模型汇总

### 7.1 新增表（v3）

| 表 | 用途 |
|----|------|
| `volume_blueprints` | 卷级宏观蓝图 |
| `generation_jobs` | 自动化生成任务 |
| `chapter_generation_steps` | 每章每步的生成记录 |

### 7.2 复用 v2 的表

| 表 | 用途 |
|----|------|
| `emotion_seeds` | 情感种子 |
| `emotion_archaeology` | 情感考古记录 |
| `emotional_leads` | 跨章情感线索 |
| `image_growth` | 意象生长记录 |
| `chapter_bridges` | 章节衔接包 |

### 7.3 现有表（不动）

projects / chapters / chapter_versions / chapter_scores / wiki_pages / wiki_page_revisions / ai_runs / 通用表 ×13

---

## 8. API 设计

### 8.1 蓝图 API

```
POST   /api/projects/{pid}/blueprints
GET    /api/projects/{pid}/blueprints
GET    /api/projects/{pid}/blueprints/{bid}
PATCH  /api/projects/{pid}/blueprints/{bid}
DELETE /api/projects/{pid}/blueprints/{bid}
POST   /api/projects/{pid}/blueprints/{bid}/approve
```

### 8.2 任务 API

```
POST   /api/projects/{pid}/jobs                    启动任务
GET    /api/projects/{pid}/jobs                    列出任务
GET    /api/projects/{pid}/jobs/{jid}              查看任务
POST   /api/projects/{pid}/jobs/{jid}/pause        暂停
POST   /api/projects/{pid}/jobs/{jid}/resume       恢复
POST   /api/projects/{pid}/jobs/{jid}/abort        中止
POST   /api/projects/{pid}/jobs/{jid}/checkpoint/continue  检查点放行
GET    /api/projects/{pid}/jobs/{jid}/steps        步骤明细
GET    /api/projects/{pid}/jobs/{jid}/stream       SSE 实时流
```

### 8.3 自动生成蓝图 API

```
POST   /api/projects/{pid}/blueprints/auto-generate
       body: { volume_arc, chapter_count, keywords }
       → AI 自动生成完整蓝图 JSON
```

---

## 9. SSE 实时进度推送

编排器在每步完成时通过 SSE 推送进度：

```python
@app.get("/api/projects/{pid}/jobs/{jid}/stream")
def job_stream(pid: str, jid: str):
    def event_generator():
        while True:
            job = get_job(jid)
            if not job or job.status in ('completed', 'failed', 'aborted'):
                yield f"data: {json.dumps({'type': 'done', 'job': job})}\n\n"
                break
            step = get_current_step(jid)
            yield f"data: {json.dumps({'type': 'progress', 'step': step})}\n\n"
            time.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

前端用 EventSource 接收：

```typescript
const es = new EventSource(`${base}/api/projects/${pid}/jobs/${jid}/stream`);
es.onmessage = (e) => {
  const data = JSON.parse(e.data);
  if (data.type === 'progress') updateProgress(data.step);
  if (data.type === 'done') es.close();
};
```

---

## 10. 实施路线图

### Phase 0：编排器核心（2天）

```
1. database.py 新增 3 张表（volume_blueprints / generation_jobs / chapter_generation_steps）
2. main.py 新增 orchestrator 模块（run_generation_job / run_single_chapter_pipeline / should_smart_stop）
3. main.py 新增蓝图 CRUD + 任务 CRUD API
4. main.py 新增 SSE 流接口
验收：能用 API 启动一个 3 章的自动生成任务，后台跑完 7 步管线
```

### Phase 1：前端控制台（2天）

```
1. BlueprintEditor.tsx（蓝图编辑 + 情感曲线可视化）
2. JobLauncher.tsx（任务启动面板）
3. JobProgressPanel.tsx（SSE 实时进度）
4. CheckpointNotification.tsx（检查点通知）
5. App.tsx 新增 "自动生成" tab
验收：前端能启动任务、看实时进度、在检查点放行
```

### Phase 2：智能停 + 蓝图自动生成（1天）

```
1. should_smart_stop 完整实现（5 种检测条件）
2. 蓝图自动生成工作流（AI 根据卷弧线 + 关键词生成完整蓝图 JSON）
3. 伏笔回收追踪（比对蓝图规划 vs 实际回收）
验收：智能停能正确触发；蓝图能自动生成
```

### Phase 3：优化与打磨（1天）

```
1. 错误恢复策略（某步失败时重试/跳过/中止）
2. 并发控制（同一项目同时只能跑一个 job）
3. 进度持久化（服务重启后能恢复中断的 job）
4. 前端进度可视化优化
```

---

## 11. 验收标准

### 11.1 Phase 0 验收

| 验收项 | 标准 |
|--------|------|
| 数据库 | 3 张新表创建成功 |
| 编排器 | `run_generation_job` 能跑完 3 章完整管线 |
| 单章管线 | 7 步全部执行（brief→seed→draft→archaeology→deepen→summarize→bridge） |
| 步骤记录 | `chapter_generation_steps` 每步状态正确 |
| 衔接链 | 第 2 章的 brief 能看到第 1 章的衔接包 |
| SSE | `/stream` 接口能推送实时进度 |
| API | 蓝图 CRUD + 任务 CRUD 全部可用 |

### 11.2 Phase 1 验收

| 验收项 | 标准 |
|--------|------|
| 蓝图编辑器 | 能创建/编辑/批准蓝图 |
| 任务启动 | 能选蓝图、设参数、启动任务 |
| 实时进度 | SSE 流实时更新步骤状态 |
| 检查点 | 检查点触发时弹通知，能放行 |
| 暂停恢复 | 能暂停任务并恢复 |

### 11.3 Phase 2 验收

| 验收项 | 标准 |
|--------|------|
| 智能停 | 5 种检测条件至少 3 种能正确触发 |
| 蓝图自动生成 | 输入卷弧线+关键词，AI 生成完整蓝图 |
| 伏笔追踪 | 能比对规划 vs 实际回收 |

---

## 12. 与 v1/v2 的关系

| 维度 | v1（单章手动） | v2（加情感+衔接） | v3（自动化） |
|------|--------------|-----------------|-------------|
| 工作方式 | 用户逐步点击 | 用户逐步点击 | **AI 自动跑管线** |
| 单章步骤 | 大纲→正文 | 大纲→种子→正文→考古→加深→衔接 | **7 步自动串联** |
| 多章 | 手动重复 | 手动重复 | **批量循环** |
| 宏观指引 | 无 | 无 | **卷级蓝图** |
| 检查点 | 每步都是 | 每步都是 | **可配置（每章/每3章/智能停）** |
| 进度可见 | 无 | 无 | **SSE 实时流** |
| 用户角色 | 执行者 | 执行者 | **调控者** |

**v3 保留 v2 的全部机制**（情感种子、考古、加深、衔接包、意象、线索），只是把它们从"手动逐步调用"变为"编排器自动串联"。

---

## 附录 A：编排器错误恢复策略

| 错误类型 | 处理方式 |
|---------|---------|
| 某步工作流调用失败 | 重试 1 次；仍失败则记录 failed，跳过该步继续 |
| 远程模型超时 | 重试 1 次；仍失败则用 stub 兜底 |
| 衔接包生成失败 | 跳过（下一章用 recent_chapter_line 退化） |
| 考古/加深失败 | 跳过（不影响正文已生成） |
| 摘要失败 | 用正文前 200 字兜底 |
| 整章失败 | 标记 failed，继续下一章 |
| 服务重启 | job 状态为 paused，用户手动恢复 |

---

## 附录 B：蓝图自动生成 Prompt

```
你是一位资深小说策划。根据以下信息，生成一份卷级宏观蓝图。

卷弧线：{volume_arc}
章节数：{chapter_count}
关键词：{keywords}
已有角色：{characters}

返回 JSON，包含：
1. volume_title：卷标题
2. emotional_trajectory：情感走向（分 3-5 段，每段标注章节范围、情绪、强度）
3. key_foreshadowings：3-5 个关键伏笔（planted_in / payoff_in / content）
4. character_arcs：主要角色的弧线（start_state / end_state / turning_point）
5. recurring_motifs：3-5 个贯穿意象
6. taboo_list：2-3 条禁忌

要求：
- 伏笔的 payoff_in 不能超过章节总数
- 情感走向要有起伏，不能一路平稳
- 角色弧线要有明确的转折点
```

---

## 附录 C：不做什么

- ❌ 不做实时协同编辑（单人本地应用）
- ❌ 不做多用户权限（本地优先）
- ❌ 不做云端同步（v3 仍是本地优先）
- ❌ 不破坏 v2 的单章手动模式（保留作为备用）
- ❌ 不改现有 16 个工作流的内部逻辑（编排器只负责串联调用）
- ❌ 不引入 Celery/Redis 等重型异步框架（用 Python 后台线程 + SSE 足够）
