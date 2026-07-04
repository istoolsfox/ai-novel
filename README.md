# AI 小说创作平台

本项目是一个本地优先的 AI 小说创作工作台 MVP，包含 FastAPI 后端、Vite React 前端、SQLite 数据库，以及参考 `llmwiki` 思路实现的项目级本地记忆目录。

当前代码基线已回到 2026-04-30 的 React + FastAPI 工作台版本，并在该版本上叠加轻量情感增强能力。

## 功能范围

- 小说项目隔离：项目、章节、版本、评分、记忆、Wiki 页面和导出文件都绑定到当前项目。
- 章节工作台：章节编辑、候选版本、设为当前正文、独立评分、定稿。
- 创作资料：人物、世界观、时间线、伏笔、雷点、风格档案、知识库资料。
- 本地 Wiki 记忆：每个项目创建 `memory/raw_sources/`、`memory/wiki/`、`memory/index/`。
- AI 工作流：要求配置真实远程模型；未配置或调用失败时直接报错，不再回退到本地占位正文。
- 情感增强：编辑器 AI 副驾支持情感种子、五层情感考古、对话潜台词、追读力检查、情感加深藏回和去 AI 味工作流。
- 导出：Markdown、TXT、DOCX、PDF、EPUB。

## 远程模型配置

进入前端 `设置 -> 模型配置`，选择服务商、填写 API Key，并点击“测试连接”。测试通过后勾选“是否默认模型”，或在 `任务路由` 中为不同 AI 工作流指定模型。

内置预设：

- DeepSeek：`https://api.deepseek.com/v1`，默认模型 `deepseek-chat`
- Xiaomi MiMo：`https://api.xiaomimimo.com/v1`，默认模型 `mimo-v2.5-pro`
- MiniMax：`https://api.minimax.io/v1`，默认模型 `MiniMax-M3`
- OpenAI / 自定义 OpenAI-compatible：按服务商文档填写 Base URL 和模型名

MiMo 调用会使用 `api-key` 请求头和 `max_completion_tokens`；其他 OpenAI-compatible 服务默认使用 Bearer Token 和 `max_tokens`。

## 开发约束

执行任何实现计划前，先阅读并遵循 [CLAUDE.md](CLAUDE.md)。这里的“项目”默认指左侧项目库中选中的小说项目；所有章节、版本、评分、记忆和导出都必须归属到该项目。

## 启动后端

```powershell
cd G:\ai小说
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

后端接口文档：

```text
http://127.0.0.1:8000/docs
```

## 启动前端

```powershell
cd G:\ai小说\frontend
npm install
npm run dev
```

前端地址：

```text
http://127.0.0.1:5173
```

## 测试

```powershell
cd G:\ai小说
python -m pytest backend/tests/test_mvp.py -q
```

```powershell
cd G:\ai小说\frontend
npm test
npm run build
```

## 本地数据

默认数据目录为 `data/`，可以通过环境变量调整：

```powershell
$env:AI_NOVEL_DATA_DIR='data'
$env:AI_NOVEL_DATABASE_URL='sqlite:///backend/app.db'
```
