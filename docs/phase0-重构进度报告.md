# Phase 0 重构进度报告

## 完成情况

### ✅ 已完成

| 改造点 | 状态 | 说明 |
|---|---|---|
| DDD 分层目录结构 | ✅ | interfaces/application/engine/domain/workflows/infrastructure/prompt_packages 全部创建 |
| Pydantic 模型迁移 | ✅ | 8 个模型迁到 `domain/models.py`，main.py 用 re-export 保持兼容 |
| 上下文压缩工具迁移 | ✅ | 9 个 compact/trim 函数迁到 `application/context_builder.py` |
| database/storage 迁移 | ✅ | 迁到 `infrastructure/`，原位置保留 re-export shim |
| 提示词包 YAML | ✅ | 9 个工作流的 YAML 提示词包创建在 `prompt_packages/_base/` |
| prompt_loader 实现 | ✅ | `engine/prompt_loader.py` 三函数可用，YAML 驱动已验证 |
| system_prompt YAML 化 | ✅ | `system_prompt_for_workflow` 改为从 YAML 渲染 |
| 回归测试 | ✅ | 26 个测试全部通过 |

### ⏳ 待续（下一步会话）

| 改造点 | 说明 | 预估 |
|---|---|---|
| 路由拆分到 interfaces/routes/ | 把 ~30 个 @app 路由按资源拆分 | 大工作量 |
| LLM 客户端迁移 | run_model_or_stub/resolve_model_config 迁到 workflows/llm_client.py | 中等 |
| 工作流逻辑迁移 | structured_output_for_workflow/build_local_chapter_draft 迁到 workflows/generation.py | 大工作量 |
| main.py < 100 行 | 上述完成后 main.py 仅保留 app 装配 | 最终目标 |

## 当前 main.py 状态

- **行数**：2182 行（从 2428 行减少 246 行）
- **结构**：已剥离模型定义、compact 工具、database/storage 实现、system_prompt 硬编码
- **仍含**：所有路由 handlers、run_ai_workflow、structured_output_for_workflow、build_local_chapter_draft、LLM 调用逻辑

## 验证结果

```
=== prompt_loader 冒烟测试 ===
draft prompt 长度: 499
包含情感入口: True
包含对话节奏: True
brief prompt 长度: 373
draft params: {'temperature': 0.85, 'top_p': 0.92, 'max_tokens': 4096}
可用工作流: ['analyze_reader_pull', 'anti_ai_polish', 'deepen_and_bury', 
'dialogue_subtext_excavation', 'emotion_archaeology', 'generate_chapter_bridge', 
'generate_chapter_brief', 'generate_chapter_draft', 'generate_emotion_seed', 
'summarize_chapter']

=== 回归测试 ===
26 passed in 5.83s
```

## 架构现状

```
backend/app/
├── main.py                  # 2182 行（路由 + 工作流逻辑，待进一步拆分）
├── database.py              # re-export shim → infrastructure/database.py
├── storage.py               # re-export shim → infrastructure/storage.py
├── domain/
│   └── models.py            # ✅ 8 个 Pydantic 模型
├── application/
│   └── context_builder.py   # ✅ 9 个 compact/trim 函数
├── engine/
│   └── prompt_loader.py     # ✅ YAML 提示词加载 + 渲染
├── infrastructure/
│   ├── database.py          # ✅ SQLite 实现（从 app/ 迁入）
│   └── storage.py           # ✅ 文件系统实现（从 app/ 迁入）
├── workflows/               # 待填充
└── prompt_packages/
    └── _base/               # ✅ 9 个 YAML 提示词包
```

## 连续性说明

下一步会话应继续：
1. 把 `run_model_or_stub`/`resolve_model_config`/`build_stub_ai_output`/`parse_structured_ai_text` 迁到 `workflows/llm_client.py`
2. 把 `structured_output_for_workflow`/`build_local_chapter_draft` 及辅助函数迁到 `workflows/generation.py`
3. 把各 `@app` 路由按资源拆分到 `interfaces/routes/*.py`
4. 最终 `main.py` 只保留 FastAPI app 装配（< 100 行）

每步迁移后跑 `pytest tests/test_mvp.py` 确认 26 个测试通过。
