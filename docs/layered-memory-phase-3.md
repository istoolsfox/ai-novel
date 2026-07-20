# 阶段三：分层记忆编译器

本阶段在阶段二章节衔接和连续性检查基础上，扩展章节定稿后的结构化记忆。

## 目标

章节正文通过复检后，不只保存摘要、人物状态和人物知识，还要维护：

- 硬事实
- 动态人物关系
- 物品状态与归属
- 叙事债务
- 伏笔生命周期
- 每章记忆编译记录

这些状态会自动进入下一章执行合同。

## 新增数据表

```text
memory_compilations
story_facts
relationship_states
story_items
item_ownership
narrative_debts
foreshadowing_states
```

每条派生状态均记录来源章节和记忆编译记录。重新编译同一章时，系统会替换该章派生状态，不会重复累积。

## 记忆编译输出

```text
章节正文
├── 章节摘要和结束状态
├── 硬事实
├── 人物状态
├── 人物知识变化
├── 关系变化
├── 物品及归属变化
├── 叙事债务变化
├── 伏笔变化
├── 未完成动作
├── 未解决钩子
├── 情绪余波
└── 下一章种子
```

## 下一章强约束

章节合同新增：

```text
hard_facts
relationship_states
item_ownership
narrative_debts
active_foreshadowings
```

正文生成提示会明确要求：

- 物品不能无理由转移。
- 关系变化必须有过渡。
- 未解决叙事债务不能被遗忘。
- 已埋伏笔不能被当成首次出现。
- 已撤销事实不能继续作为真实前提。

## API

```text
GET /api/projects/{project_id}/memory/context
GET /api/projects/{project_id}/memory/compilations
GET /api/projects/{project_id}/memory/facts
GET /api/projects/{project_id}/memory/relationships
GET /api/projects/{project_id}/memory/items
GET /api/projects/{project_id}/memory/debts
GET /api/projects/{project_id}/memory/foreshadowings
```

`debts` 支持 `open_only=true`，`foreshadowings` 支持 `active_only=true`。

## 当前限制

- 结构化提取仍依赖远程模型正确返回 JSON。
- 当前上下文对每层最多注入 80 条状态，尚未加入相关性检索。
- 人物关系和物品归属目前按章节保存历史快照，尚未提供前端时间轴。
- 叙事债务暂未自动按截止章节触发高风险暂停。
- 伏笔状态与旧的通用 `foreshadowings` 记录尚未做双向同步。
