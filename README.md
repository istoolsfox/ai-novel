# AI 小说创作平台

本项目是一个本地优先的 AI 小说创作工作台 MVP，包含 FastAPI 后端、Vite React 前端、SQLite 数据库，以及参考 `llmwiki` 思路实现的项目级本地记忆目录。

## 功能范围

- 小说项目隔离：项目、章节、版本、评分、记忆、Wiki 页面和导出文件都绑定到当前项目。
- 章节工作台：章节编辑、候选版本、设为当前正文、独立评分、定稿。
- 创作资料：人物、世界观、时间线、伏笔、雷点、风格档案、知识库资料。
- 本地 Wiki 记忆：每个项目创建 `memory/raw_sources/`、`memory/wiki/`、`memory/index/`。
- AI 工作流：当前为本地 stub，可替换为真实 OpenAI-compatible 调用。
- 导出：Markdown、TXT、DOCX、PDF、EPUB。

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
