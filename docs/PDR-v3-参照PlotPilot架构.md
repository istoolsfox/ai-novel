# PDR v3 · 参照 PlotPilot 架构的自动化小说生成平台

| 项 | 值 |
|---|---|
| 文档版本 | 3.1 |
| 创建日期 | 2026-07-01 |
| 状态 | 待实施 |
| 项目代号 | ai-novel-workbench |
| 仓库根目录 | `G:\ai小说` |
| 参考项目 | [PlotPilot](https://github.com/shenminglinyi/PlotPilot)（shenminglinyi） |
| 前置文档 | `docs/PDR-AI小说创作平台.md`、`docs/PDR-桌面化改造.md`、`docs/PDR-v3-自动化生成.md`（已废弃） |

> **本版真正参照 PlotPilot 的架构设计**，结合本项目 FastAPI + SQLite + React 的现有优点，做分层重构 + 自动化管线 + 提示词包 + 叙事状态机 + 熔断保护。
>
> 核心理念：PlotPilot 证明"长篇 AI 创作是系统工程问题，不是提示词堆砌"。本版照此理念重构。

---

## 1. 与 PlotPilot 的对标

### 1.1 PlotPilot 五大子系统 → 本项目映射

| PlotPilot 子系统 | PlotPilot 做法 | 本项目做法（结合自身优点） |
|---|---|---|
| **叙事状态机** | Story Bible + 章级摘要链 + 事件流 + 故事线 DAG + 伏笔注册表 | 复用现有 chapters/wiki/memory_items/foreshadowings 表 + 新增 chapter_bridges（v2已有） + volume_blueprints |
| **向量语义检索** | FAISS/ChromaDB + 三元组索引 | 暂不引入向量库（SQLite + 全文检索 + 卷记忆已够 MVP），后续可选升级 |
| **引擎运行时** | EngineDaemon + StoryPipelineRunner + BaseStoryPipeline 十步管线 | **新增 `engine/` 模块**：StoryPipeline 管线类 + Orchestrator 调度器，跑在后台线程 |
| **提示词策略层** | 20+ 独立提示接点 + YAML 配置覆写 | **新增 `prompt_packages/` YAML 配置**：把硬编码 prompt 改为可配置接点 |
| **质量监控** | 张力心电图 + 文风相似度 + 漂移告警 + 定向修写 + 陈词滥调扫描 | **复用 v2 的 emotion_archaeology + deepen_and_bury** + 新增张力评分 + 漂移检测 |

### 1.2 PlotPilot 十步管线 → 本项目七步管线

PlotPilot 的十步管线是它的核心组件。本项目根据自身特点做七步（合并了几个步骤）：

| PlotPilot 步骤 | 本项目对应 | 说明 |
|---|---|---|
| 1. 叙事治理预算 | 蓝图参数注入 | 卷蓝图提供宏观预算 |
| 2. 章节执行剧本准备 | **Step 1: generate_chapter_brief** | 生成大纲 |
| 3. 上下文装配 | build_generation_context（已有） | 自动装配 |
| 4. LLM 调用 | **Step 2: generate_emotion_seed + Step 3: generate_chapter_draft** | 种子+正文 |
| 5. 内容策略验证 | **Step 4: emotion_archaeology** | 考古替代验证 |
| 6. 文风漂移检测 | 合并进 Step 4 考古 | 考古含 rupture_points |
| 7. 章末管线 | **Step 5: deepen_and_bury + Step 6: summarize_chapter** | 加深+摘要 |
| 8. 向量索引更新 | 跳过（无向量库） | 卷记忆重建替代 |
| 9. 张力评分 | 合并进 Step 4 考古 | 考古含 reader_felt_map |
| 10. 状态落库 | **Step 7: generate_chapter_bridge** + 自动定稿 | 衔接包+定稿 |

### 1.3 PlotPilot 工程特性 → 本项目采纳

| PlotPilot 特性 | 本项目采纳方式 |
|---|---|
| 单一生产入口 | `POST /api/projects/{pid}/jobs` 启动，引擎在后台跑 |
| 可回退写作路径 | 保留 v2 的单章手动模式作为 fallback |
| **熔断保护** | 连续失败超阈值自动暂停 job + 附带诊断信息 |
| **单写者路由** | SQLite 已是单写者（WAL 模式），engine 串行执行 |
| **SSE 实时推流** | `/jobs/{jid}/stream` 推送进度 |
| **检查点快照** | chapter_generation_steps 记录每步状态，可从断点恢复 |
| **提示词包 YAML** | 新增 `prompt_packages/` 目录，每个接点一个 YAML |

---

## 2. 架构设计（DDD 分层）

### 2.1 参照 PlotPilot 的分层

PlotPilot 用 DDD 分层：domain / application / engine / infrastructure / interfaces。

本项目**不照搬目录名**（避免改太多 import），而是在 `backend/app/` 下新增模块，逻辑上分层：

```
backend/app/
├── main.py              # interfaces 层：FastAPI 路由（现有，不动）
├── database.py          # infrastructure 层：SQLite（现有，扩展）
├── storage.py           # infrastructure 层：文件系统（现有，不动）
│
├── domain/              # 【新增】领域层：纯业务模型
│   ├── __init__.py
│   ├── models.py        # Pydantic 数据模型（ChapterDraft/EmotionSeed/Bridge/Blueprint 等）
│   └── enums.py         # 枚举（JobStatus/StepStatus/CheckpointStrategy 等）
│
├── engine/              # 【新增】引擎内核：生产运行时
│   ├── __init__.py
│   ├── pipeline.py      # StoryPipeline 管线类（七步串联）
│   ├── orchestrator.py  # Orchestrator 调度器（多章循环 + 检查点 + 熔断）
│   ├── checkpoint.py    # 检查点 + 智能停检测
│   └── circuit_breaker.py  # 熔断保护
│
├── application/         # 【新增】应用层：用例编排
│   ├── __init__.py
│   ├── job_service.py   # 生成任务的用例（启动/暂停/恢复/中止）
│   ├── blueprint_service.py  # 蓝图用例
│   └── context_builder.py    # 上下文装配（从 main.py 的 build_generation_context 迁出）
│
└── prompt_packages/     # 【新增】提示词策略层
    ├── README.md
    ├── generate_chapter_brief.yaml
    ├── generate_emotion_seed.yaml
    ├── generate_chapter_draft.yaml
    ├── emotion_archaeology.yaml
    ├── deepen_and_bury.yaml
    ├── generate_chapter_bridge.yaml
    └── summarize_chapter.yaml
```

### 2.2 分层职责

| 层 | 职责 | 对应 PlotPilot |
|---|---|---|
| **interfaces**（main.py） | HTTP 路由、请求校验、SSE 流 | interfaces/ |
| **application** | 用例编排：启动 job、装配上下文、协调 engine | application/ |
| **engine** | 生产运行时：管线执行、检查点、熔断 | engine/ |
| **domain** | 纯数据模型：不依赖框架 | domain/ |
| **infrastructure**（database.py/storage.py） | SQLite + 文件系统 | infrastructure/ |
| **prompt_packages** | YAML 配置的提示词接点 | prompt_packages/ |

### 2.3 调用链路

```
用户点击"开始自动生成"
    ↓
main.py 路由 POST /api/projects/{pid}/jobs
    ↓
application/job_service.py 启动 job 记录
    ↓
engine/orchestrator.py 在后台线程跑 run_generation_job
    ↓
engine/pipeline.py 对每一章跑 run_single_chapter_pipeline
    ↓
    ├─ Step 1: generate_chapter_brief     （读 prompt_packages/*.yaml）
    ├─ Step 2: generate_emotion_seed
    ├─ Step 3: generate_chapter_draft
    ├─ Step 4: emotion_archaeology
    ├─ Step 5: deepen_and_bury
    ├─ Step 6: summarize_chapter
    └─ Step 7: generate_chapter_bridge
    ↓
engine/checkpoint.py 检查是否需要停
    ↓
engine/circuit_breaker.py 检查是否熔断
    ↓
SSE 推送进度 → 前端
```

---

## 3. 提示词包（Prompt Packages）

### 3.1 参照 PlotPilot 的 YAML 配置

PlotPilot 有 20+ 提示接点，每个接点可通过 YAML 独立覆写。本项目照此设计，把 `system_prompt_for_workflow` 里硬编码的 prompt 改为 YAML 配置。

### 3.2 YAML 结构

```yaml
# prompt_packages/generate_chapter_draft.yaml
name: generate_chapter_draft
description: 章节正文生成
category: generation
system_prompt: |
  你是专业的中文长篇小说创作助手。当前任务是生成或改写小说正文。
  只返回可直接放入章节编辑器的中文正文，不要返回 JSON、Markdown 标题。
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
  - name: prev_bridge
    condition: "prev_chapter_bridge is not None"
    template: |
      【上一章衔接包·本章必须承接】
      末尾状态：{prev_bridge.ending_state}
      未决钩子：{prev_bridge.open_hooks}
      情感余波：{prev_bridge.emotional_residue}
      ...
      【连贯性硬约束】
      1. 开头必须承接上一章末尾状态
      2. 角色情绪必须从余波起步
      3. 必须回应至少一个未决钩子
      4. 不要重复揭示已揭示的信息
      5. 前 2-3 段必须有明显承接感
  - name: blueprint
    condition: "blueprint is not None"
    template: |
      【卷级蓝图·本章位置】
      卷弧线：{blueprint.volume_arc}
      本章在情感走向的位置：{blueprint.current_emotion_segment}
      本章应埋伏笔：{blueprint.foreshadowings_to_plant}
      本章应回收伏笔：{blueprint.foreshadowings_to_payoff}
```

### 3.3 加载机制

```python
# engine/prompt_loader.py
import yaml
from pathlib import Path

_PROMPT_CACHE: dict[str, dict] = {}

def load_prompt_package(workflow: str) -> dict:
    if workflow in _PROMPT_CACHE:
        return _PROMPT_CACHE[workflow]
    path = Path(__file__).parent.parent / "prompt_packages" / f"{workflow}.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    _PROMPT_CACHE[workflow] = data
    return data

def render_system_prompt(workflow: str, context: dict) -> str:
    pkg = load_prompt_package(workflow)
    base = pkg.get("system_prompt", "")
    for directive in pkg.get("directives", []):
        # 简单的条件判断 + 模板替换
        if _evaluate_condition(directive.get("condition", ""), context):
            template = directive["template"]
            base += "\n\n" + _render_template(template, context)
    return base
```

### 3.4 好处

- **不改代码就能调 prompt**：编辑 YAML 即可
- **不同题材不同包**：`prompt_packages/wuxia/`、`prompt_packages/scifi/`，切换题材不改代码（照搬 PlotPilot）
- **指令可组合**：seed/bridge/blueprint 三个指令按条件叠加

---

## 4. 引擎内核（Engine）

### 4.1 StoryPipeline 管线类

参照 PlotPilot 的 `BaseStoryPipeline`，抽象为管线类：

```python
# engine/pipeline.py
from dataclasses import dataclass
from typing import Callable

@dataclass
class PipelineStep:
    name: str
    workflow: str
    prepare: Callable  # 准备 payload
    post_process: Callable  # 处理输出

class StoryPipeline:
    """单章七步管线。参照 PlotPilot BaseStoryPipeline。"""
    
    steps: list[PipelineStep] = [
        PipelineStep("brief", "generate_chapter_brief",
            prepare=lambda ctx: {"chapter_id": ctx.chapter_id, "prompt": ctx.brief_prompt},
            post_process=lambda out, ctx: ctx.update_brief(out)),
        PipelineStep("seed", "generate_emotion_seed",
            prepare=lambda ctx: {"chapter_id": ctx.chapter_id},
            post_process=lambda out, ctx: None),  # 已在 run_ai_workflow 持久化
        PipelineStep("draft", "generate_chapter_draft",
            prepare=lambda ctx: {"chapter_id": ctx.chapter_id, "prompt": f"目标字数：{ctx.target_words}"},
            post_process=lambda out, ctx: ctx.update_draft(out)),
        PipelineStep("archaeology", "emotion_archaeology",
            prepare=lambda ctx: {"chapter_id": ctx.chapter_id, "content": ctx.draft},
            post_process=lambda out, ctx: ctx.update_archaeology(out)),
        PipelineStep("deepen", "deepen_and_bury",
            prepare=lambda ctx: {"chapter_id": ctx.chapter_id, "content": ctx.draft},
            post_process=lambda out, ctx: ctx.update_draft(out.revised_text)),
        PipelineStep("summarize", "summarize_chapter",
            prepare=lambda ctx: {"chapter_id": ctx.chapter_id, "content": ctx.draft},
            post_process=lambda out, ctx: ctx.update_summary(out)),
        PipelineStep("bridge", "generate_chapter_bridge",
            prepare=lambda ctx: {"chapter_id": ctx.chapter_id, "content": ctx.draft},
            post_process=lambda out, ctx: None),  # 已持久化
    ]
    
    def run(self, ctx: ChapterContext, on_step: Callable = None):
        for step in self.steps:
            if on_step:
                on_step(step.name, "running")
            try:
                payload = step.prepare(ctx)
                output = call_workflow(ctx.project_id, step.workflow, payload)
                step.post_process(output, ctx)
                if on_step:
                    on_step(step.name, "completed")
            except Exception as e:
                if on_step:
                    on_step(step.name, "failed", str(e))
                # 熔断器决定是否继续
                if self.circuit_breaker.should_stop(step.name, e):
                    raise
        return ctx
```

### 4.2 Orchestrator 调度器

```python
# engine/orchestrator.py
import threading

class Orchestrator:
    """多章循环调度器。参照 PlotPilot StoryPipelineRunner。"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.pipeline = StoryPipeline()
        self.checkpoint = CheckpointManager()
        self.breaker = CircuitBreaker()
    
    def run(self):
        job = get_job(self.job_id)
        blueprint = get_blueprint(job.blueprint_id)
        
        for offset in range(job.target_chapter_count):
            chapter_number = job.start_chapter_number + offset
            
            # 暂停检查
            self._wait_if_paused()
            
            # 检查点放行检查
            self._wait_if_checkpoint_pending()
            
            try:
                # 创建章节
                chapter = create_chapter(job.project_id, chapter_number)
                
                # 跑单章管线
                ctx = ChapterContext(
                    project_id=job.project_id,
                    chapter_id=chapter.id,
                    chapter_number=chapter_number,
                    blueprint=blueprint,
                    target_words=blueprint.params.words_per_chapter,
                )
                
                self.pipeline.run(ctx, on_step=self._on_step)
                
                # 智能停检测
                should_stop, reason = self.checkpoint.should_smart_stop(ctx)
                if should_stop:
                    self._pause_with_reason("smart_stop", reason, chapter)
                    self._wait_if_checkpoint_pending()
                
                # 检查点
                elif self.checkpoint.hit_checkpoint(job.checkpoint_strategy, offset):
                    self._pause_with_reason("checkpoint", "", chapter)
                    self._wait_if_checkpoint_pending()
                
                # 自动定稿
                if job.auto_finalize:
                    finalize_chapter(job.project_id, chapter.id)
                
                # 更新进度
                update_job_progress(self.job_id, chapter_number)
                
            except Exception as e:
                self.breaker.record_failure(e)
                if self.breaker.should_trip():
                    self._fail_job(f"熔断：连续失败 {self.breaker.failure_count} 次")
                    return
                # 单章失败，记录后继续
                record_chapter_failure(self.job_id, chapter_number, str(e))
        
        complete_job(self.job_id)
```

### 4.3 熔断保护

```python
# engine/circuit_breaker.py
class CircuitBreaker:
    """连续失败熔断。参照 PlotPilot 的熔断保护。"""
    
    def __init__(self, threshold: int = 3, window: int = 5):
        self.threshold = threshold  # 连续失败阈值
        self.window = window        # 窗口大小（最近 N 章）
        self.failures: list[bool] = []  # 最近 N 章的成功/失败
    
    def record_failure(self, error: Exception):
        self.failures.append(False)
        if len(self.failures) > self.window:
            self.failures.pop(0)
    
    def record_success(self):
        self.failures.append(True)
        if len(self.failures) > self.window:
            self.failures.pop(0)
    
    @property
    def consecutive_failures(self) -> int:
        count = 0
        for ok in reversed(self.failures):
            if not ok:
                count += 1
            else:
                break
        return count
    
    @property
    def failure_count(self) -> int:
        return sum(1 for ok in self.failures if not ok)
    
    def should_trip(self) -> bool:
        return self.consecutive_failures >= self.threshold
    
    def should_stop(self, step_name: str, error: Exception) -> bool:
        # 单步失败不熔断，只有连续 N 章失败才熔断
        return False
```

### 4.4 检查点 + 智能停

```python
# engine/checkpoint.py
class CheckpointManager:
    def hit_checkpoint(self, strategy: str, offset: int) -> bool:
        if strategy == "every_chapter":
            return True
        if strategy == "every_3":
            return (offset + 1) % 3 == 0
        if strategy == "none":
            return False
        return False
    
    def should_smart_stop(self, ctx: ChapterContext) -> tuple[bool, str]:
        """智能停检测，5 种条件。"""
        # 1. 考古断裂点过多
        arch = ctx.archaeology
        if arch and len(arch.get("reader_felt_map", {}).get("rupture_points", [])) > 3:
            return True, "情感断裂点超过 3 个"
        
        # 2. 未回收钩子累积
        bridges = list_chapter_bridges(ctx.project_id)
        total_hooks = sum(len(b.get("open_hooks", [])) for b in bridges)
        if total_hooks > 8:
            return True, f"未回收钩子 {total_hooks} 个，超过 8"
        
        # 3. 字数偏差
        target = ctx.target_words
        actual = len(ctx.draft)
        if target and (actual < target * 0.7 or actual > target * 1.3):
            return True, f"字数偏差：目标 {target}，实际 {actual}"
        
        # 4. 衔接断裂（简单检测：正文开头是否提及上一章末尾关键词）
        prev_bridge = get_previous_chapter_bridge(ctx.project_id, ctx.chapter_number)
        if prev_bridge:
            ending = prev_bridge.get("ending_state", {})
            if isinstance(ending, dict):
                location = ending.get("location", "")
                if location and location not in ctx.draft[:500]:
                    return True, f"正文开头未提及上一章末尾位置 {location}，可能衔接断裂"
        
        # 5. 重复事件检测（与卷记忆比对）
        volume_memory = get_volume_memory(ctx.project_id)
        if volume_memory and ctx.summary:
            # 简单检测：摘要是否与卷记忆高度重复
            if _text_overlap_ratio(ctx.summary, volume_memory) > 0.6:
                return True, "本章摘要与卷记忆高度重复，可能重复了已有事件"
        
        return False, ""
```

---

## 5. 叙事状态机（复用 + 扩展）

### 5.1 PlotPilot 的叙事状态机组成

| 组成 | PlotPilot | 本项目 |
|---|---|---|
| Story Bible（人物档案） | bible/ 模块 | characters 表（已有） |
| 章级摘要链 | 每章压缩摘要 | chapters.summary + memory_items（已有） |
| 叙事事件流 | 关键事件时序登记 | timeline_events 表（已有） |
| 故事线 DAG | 多故事线有向无环图 | 暂不实现（MVP 不需要） |
| 伏笔注册表 | 钩子开启/悬置/消费状态 | foreshadowings 表（已有，需扩展状态） |
| **章级衔接包** | - | **chapter_bridges 表（v2 新增）** |
| **卷级蓝图** | - | **volume_blueprints 表（v3 新增）** |

### 5.2 伏笔状态扩展

foreshadowings 表的 payload 扩展状态字段：

```json
{
  "content": "裂开的印章",
  "status": "planted",  // planted / suspended / paid_off
  "planted_in_chapter": 3,
  "payoff_in_chapter": 18,
  "blueprint_id": "..."
}
```

编排器在生成每章前，检查蓝图里的伏笔规划：
- 当前章号 == `planted_in_chapter` → 在 brief 里提示"本章应埋此伏笔"
- 当前章号 == `payoff_in_chapter` → 在 brief 里提示"本章应回收此伏笔"

---

## 6. 数据模型

### 6.1 新增表（v3）

```sql
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

-- 自动化生成任务
CREATE TABLE IF NOT EXISTS generation_jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    volume_blueprint_id TEXT,
    start_chapter_number INTEGER NOT NULL,
    target_chapter_count INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending/running/paused/checkpoint/completed/failed
    current_chapter_number INTEGER DEFAULT 0,
    current_step TEXT DEFAULT '',
    checkpoint_strategy TEXT DEFAULT 'every_3',
    auto_finalize INTEGER DEFAULT 0,
    params_json TEXT DEFAULT '{}',
    pause_reason TEXT DEFAULT '',     -- checkpoint / smart_stop / user_paused
    pause_detail TEXT DEFAULT '',
    error_message TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

-- 每章每步的生成记录（检查点快照）
CREATE TABLE IF NOT EXISTS chapter_generation_steps (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    chapter_number INTEGER NOT NULL,
    step_name TEXT NOT NULL,        -- brief/seed/draft/archaeology/deepen/summarize/bridge/finalize
    step_status TEXT DEFAULT 'pending',  -- pending/running/completed/failed/skipped
    step_output TEXT DEFAULT '{}',
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT DEFAULT '',
    FOREIGN KEY(job_id) REFERENCES generation_jobs(id)
);
```

### 6.2 复用现有表

| 表 | 来源 | 用途 |
|---|---|---|
| chapters / chapter_versions / chapter_scores | v1 | 章节 |
| emotion_seeds / emotion_archaeology / emotional_leads / image_growth | v2 | 情感深度 |
| chapter_bridges | v2 | 章节衔接包 |
| characters / foreshadowings / timeline_events / ... | v1 | 创作资料 |
| wiki_pages / memory_items | v1 | 记忆系统 |
| ai_runs | v1 | AI 调用记录 |

---

## 7. API 设计

### 7.1 蓝图 API

```
POST   /api/projects/{pid}/blueprints                    创建蓝图
GET    /api/projects/{pid}/blueprints                    列出
GET    /api/projects/{pid}/blueprints/{bid}              查看
PATCH  /api/projects/{pid}/blueprints/{bid}              更新
DELETE /api/projects/{pid}/blueprints/{bid}              删除
POST   /api/projects/{pid}/blueprints/{bid}/approve      批准（→ active）
POST   /api/projects/{pid}/blueprints/auto-generate      AI 自动生成蓝图
```

### 7.2 任务 API

```
POST   /api/projects/{pid}/jobs                          启动任务
       body: { blueprint_id, start_chapter, count, checkpoint_strategy, auto_finalize, params }
GET    /api/projects/{pid}/jobs                          列出
GET    /api/projects/{pid}/jobs/{jid}                    查看进度
POST   /api/projects/{pid}/jobs/{jid}/pause              暂停
POST   /api/projects/{pid}/jobs/{jid}/resume             恢复
POST   /api/projects/{pid}/jobs/{jid}/abort              中止
POST   /api/projects/{pid}/jobs/{jid}/checkpoint/continue  检查点放行
GET    /api/projects/{pid}/jobs/{jid}/steps              步骤明细
GET    /api/projects/{pid}/jobs/{jid}/stream             SSE 实时流
```

### 7.3 蓝图数据结构

```json
{
  "volume_number": 1,
  "volume_title": "第一卷 · 灰塔苏醒",
  "volume_arc": "主角发现记忆被篡改，从被动受害者变为主动追查者",
  "chapter_range": { "start": 1, "end": 20 },
  "emotional_trajectory": {
    "shape": "rise-fall-rise",
    "segments": [
      { "range": "1-5", "emotion": "迷茫→警觉", "intensity": 3 },
      { "range": "6-10", "emotion": "警觉→愤怒", "intensity": 6 },
      { "range": "11-15", "emotion": "愤怒→动摇", "intensity": 7 },
      { "range": "16-20", "emotion": "动摇→决绝", "intensity": 8 }
    ]
  },
  "key_foreshadowings": [
    { "id": "fs_01", "planted_in": 3, "payoff_in": 18, "content": "裂开的印章" }
  ],
  "character_arcs": [
    { "character": "沈照夜", "start_state": "被动", "end_state": "主动", "turning_point": "第12章" }
  ],
  "recurring_motifs": ["雨声", "印章", "抽屉"],
  "taboo_list": ["不要让主角在10章前就知道真相"],
  "generation_params": {
    "words_per_chapter": 3000,
    "auto_finalize": false,
    "checkpoint_strategy": "every_3",
    "auto_run_side_extractions": true
  }
}
```

---

## 8. SSE 实时进度推送

```python
from fastapi.responses import StreamingResponse

@app.get("/api/projects/{pid}/jobs/{jid}/stream")
def job_stream(pid: str, jid: str):
    def event_generator():
        while True:
            job = get_job(jid)
            if not job:
                break
            step = get_current_step(jid)
            yield f"data: {json.dumps({'type': 'progress', 'job': job, 'step': step})}\n\n"
            if job.status in ('completed', 'failed', 'aborted'):
                yield f"data: {json.dumps({'type': 'done', 'job': job})}\n\n"
                break
            if job.status == 'paused' or job.status == 'checkpoint':
                yield f"data: {json.dumps({'type': 'paused', 'job': job})}\n\n"
            time.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## 9. 前端改造

### 9.1 新增"自动生成"tab

```
自动生成控制台
├── 宏观蓝图编辑器（BlueprintEditor.tsx）
│   ├── 卷弧线输入
│   ├── 情感走向曲线（可视化图表）
│   ├── 伏笔规划表
│   ├── 角色弧线
│   └── 生成参数
├── 任务启动面板（JobLauncher.tsx）
│   ├── 选择蓝图
│   ├── 起始章号 + 生成章数
│   ├── 检查点策略
│   └── [开始生成]
├── 实时进度面板（JobProgressPanel.tsx）
│   ├── 总进度（当前章/总章数）
│   ├── 当前步骤
│   ├── 步骤明细列表
│   ├── SSE 日志流
│   └── [暂停][恢复][中止]
├── 检查点通知（CheckpointNotification.tsx）
│   ├── 触发原因
│   ├── 本章预览
│   └── [放行][介入][中止]
└── 结果总览（JobResultOverview.tsx）
    ├── 章节列表
    ├── 衔接包链
    └── 伏笔回收情况
```

---

## 10. 实施路线图

### Phase 0：分层重构 + 提示词包（1.5天）

```
1. 创建 backend/app/domain/ 目录 + models.py + enums.py
2. 创建 backend/app/prompt_packages/ 目录 + 7 个 YAML
3. 创建 backend/app/engine/prompt_loader.py（YAML 加载 + 模板渲染）
4. 改造 system_prompt_for_workflow → 改为调用 render_system_prompt
5. 保持现有单章手动模式可用（回归测试通过）
验收：prompt 从硬编码改为 YAML，单章生成功能不变
```

### Phase 1：引擎内核（2天）

```
1. 创建 backend/app/engine/pipeline.py（StoryPipeline）
2. 创建 backend/app/engine/orchestrator.py（Orchestrator + 后台线程）
3. 创建 backend/app/engine/checkpoint.py（检查点 + 智能停）
4. 创建 backend/app/engine/circuit_breaker.py（熔断）
5. 创建 backend/app/application/job_service.py（任务用例）
6. database.py 新增 3 张表
7. main.py 新增蓝图 CRUD + 任务 CRUD + SSE API
验收：API 能启动 3 章自动生成，7 步管线串联跑通
```

### Phase 2：前端控制台（2天）

```
1. BlueprintEditor.tsx
2. JobLauncher.tsx
3. JobProgressPanel.tsx（SSE）
4. CheckpointNotification.tsx
5. JobResultOverview.tsx
6. App.tsx 新增 "自动生成" tab
验收：前端能启动任务、看实时进度、检查点放行
```

### Phase 3：蓝图自动生成 + 打磨（1天）

```
1. 蓝图自动生成工作流（AI 生成完整蓝图 JSON）
2. 伏笔状态追踪（planted→paid_off）
3. 错误恢复（断点续跑）
4. 并发控制（同项目同时只跑一个 job）
验收：智能停 + 蓝图自动生成 + 断点恢复
```

---

## 11. 验收标准

### 11.1 Phase 0 验收

| 项 | 标准 |
|---|---|
| YAML 配置 | 7 个 prompt_packages/*.yaml 存在 |
| 加载机制 | render_system_prompt 能从 YAML 渲染 |
| 回归 | 26 个测试通过 |
| 单章生成 | 手动模式正常，prompt 内容来自 YAML |

### 11.2 Phase 1 验收

| 项 | 标准 |
|---|---|
| 分层 | domain/engine/application 目录存在 |
| 管线 | StoryPipeline 7 步串联 |
| 编排器 | Orchestrator 能跑 3 章自动循环 |
| 熔断 | 连续 3 章失败自动中止 |
| 检查点 | every_3 策略每 3 章暂停 |
| 智能停 | 至少 3 种条件能触发 |
| SSE | /stream 推送实时进度 |
| API | 蓝图 + 任务 CRUD 全可用 |

### 11.3 Phase 2 验收

| 项 | 标准 |
|---|---|
| 蓝图编辑 | 能创建/编辑/批准蓝图 |
| 任务启动 | 能选蓝图启动 |
| 实时进度 | SSE 流实时更新 |
| 检查点 | 弹通知能放行 |
| 暂停恢复 | 正常工作 |

---

## 12. 与 PlotPilot 的差异（结合自身优点）

| 维度 | PlotPilot | 本项目 | 理由 |
|---|---|---|---|
| 数据库 | SQLite + Write Dispatch | SQLite（WAL 模式） | SQLite 已是单写者，够用 |
| 向量检索 | FAISS/ChromaDB | 暂不引入 | MVP 用卷记忆 + 全文检索够用 |
| 前端 | Vue 3 + Naive UI | React 19 + 自定义 | 已有 React 代码不重写 |
| 桌面 | Tauri | Tauri（v2 PDR 已设计） | 后续整合 |
| 语言 | Python 3.14 | Python 3.13 | 兼容性 |
| 异步 | 守护进程 | 后台线程 | 不引入 Celery/Redis |
| 提示词 | YAML 20+ 接点 | YAML 7 接点 | 按需扩展 |

---

## 附录 A：PlotPilot 架构对照表

| PlotPilot 特性 | 本项目是否采纳 | 实现方式 |
|---|---|---|
| DDD 分层 | ✅ | domain/engine/application/infrastructure/interfaces |
| 十步管线 | ✅ 简化为七步 | StoryPipeline |
| EngineDaemon | ⚠️ 简化 | 后台线程（不引入守护进程） |
| StoryPipelineRunner | ✅ | Orchestrator |
| 熔断保护 | ✅ | CircuitBreaker |
| 单写者路由 | ✅ | SQLite WAL |
| SSE 实时推流 | ✅ | /jobs/{jid}/stream |
| 检查点快照 | ✅ | chapter_generation_steps 表 |
| 提示词包 YAML | ✅ | prompt_packages/ |
| 题材扩展 | ✅ | prompt_packages/{genre}/ |
| 张力心电图 | ⚠️ 合并 | emotion_archaeology 的 reader_felt_map |
| 文风漂移检测 | ⚠️ 合并 | 考古的 rupture_points |
| 定向修写 | ✅ | deepen_and_bury |
| 陈词滥调扫描 | ⚠️ 后续 | 可在考古 prompt 里加 |
| 向量检索 | ❌ 暂不 | MVP 不需要 |
| 故事线 DAG | ❌ 暂不 | MVP 不需要 |

---

## 附录 B：不做什么

- ❌ 不引入向量数据库（MVP 用卷记忆够）
- ❌ 不引入 Celery/Redis（后台线程够）
- ❌ 不做守护进程（FastAPI 后台线程够）
- ❌ 不重写前端为 Vue（保留 React）
- ❌ 不破坏 v2 的单章手动模式（保留为 fallback）
- ❌ 不改现有 16 个工作流内部逻辑（管线只串联调用）
- ❌ 不要求 Python 3.14（3.13 够）
