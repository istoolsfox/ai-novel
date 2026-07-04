# AI 小说创作平台 · 全流程托管情感深度版

> 面向长篇小说的 AI 托管生成工作台。核心差异化是**自动化流程 + 情感感染力 + llmwiki 记忆闭环**：用户只需要给出项目设定，系统自动准备大纲、角色、关系、情感约束和章节衔接，再托管生成正文。

## ✨ 核心特性

- **一键托管生成**：自动补齐故事资产后启动后台任务，支持 SSE 实时进度
- **故事资产链路**：项目设定 → 章节大纲 → 角色档案 → 角色关系 → 关系画布 → llmwiki
- **llmwiki 记忆闭环**：角色、关系、大纲、时间线、关键记忆、章节衔接包持续写入 wiki
- **角色关系画布**：前端用 ECharts 展示人物关系，wiki 同步 Mermaid + Graph JSON
- **九步章节管线**：brief → seed → draft → dialogue → archaeology → reader_pull → deepen → anti_ai → finalize
- **情感托管生成**：用户不需要逐章说明情绪，系统自动生成情感种子、情感考古、加深·藏回
- **章节衔接包**：每章末尾自动记录下一章必须承接的末尾状态、未决钩子和情感余波
- **反断裂机制**：下一章上下文自动注入上一章衔接包，避免突然跳场、重复揭示和情绪断层
- **断点续跑**：中断后恢复时跳过已完成章节步骤
- **部署优先，打包后置**：当前支持 Docker 部署上线，后续保留 Tauri + PyInstaller 桌面打包路线

## 🏗️ 架构总览

```text
┌─────────────────────────────────────────────┐
│  Vue 3 + Naive UI + ECharts 前端              │
│  角色关系画布 / 托管生成 / llmwiki / 导出       │
└──────────────────┬──────────────────────────┘
                   │ fetch / SSE
┌──────────────────▼──────────────────────────┐
│  FastAPI 后端（DDD 分层）                    │
│  ├── interfaces/   路由层                   │
│  ├── application/  用例层                   │
│  │   ├── autopilot_service.py               │
│  │   └── story_asset_service.py             │
│  ├── engine/       九步管线 + Orchestrator    │
│  ├── workflows/    LLM 客户端 + 本地 stub      │
│  ├── domain/       Pydantic 模型             │
│  ├── infrastructure/  SQLite + 存储           │
│  └── prompt_packages/  YAML 提示词包          │
└──────────────────┬──────────────────────────┘
                   │ 文件 I/O
┌──────────────────▼──────────────────────────┐
│  SQLite + 项目文件系统 + llmwiki             │
└─────────────────────────────────────────────┘
```

## 🛠️ 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLite + Python 3.13 |
| 前端 | Vue 3 + Naive UI + ECharts + TypeScript + Vite |
| AI 接口 | OpenAI 兼容 Chat Completions API |
| 提示词 | YAML 配置包 + prompt-template 记录 |
| 部署 | Docker / Docker Compose |
| 桌面 | Tauri 2.0 + PyInstaller sidecar（后续） |

## 🔁 托管生成流程

```text
项目设定
  ↓
自动补齐章节大纲
  ↓
自动生成角色档案并写入 llmwiki
  ↓
自动生成角色关系并同步关系画布
  ↓
写入情感托管约束和 prompt skills
  ↓
启动九步章节管线
  ↓
每章定稿后写入时间线、关键记忆、章节衔接包
  ↓
下一章读取上一章衔接包，承接末尾状态、情感余波和未决钩子
```

托管入口：

```text
POST /api/projects/{project_id}/jobs/autopilot
```

## 📁 目录结构

```text
ai-novel/
├── backend/
│   ├── app/
│   │   ├── interfaces/        # FastAPI 路由
│   │   ├── application/       # 业务用例、托管生成、llmwiki 同步
│   │   ├── engine/            # 九步管线 + Orchestrator
│   │   ├── workflows/         # 生成工作流 + LLM 客户端
│   │   ├── domain/            # Pydantic 模型
│   │   ├── infrastructure/    # SQLite + 文件存储
│   │   └── prompt_packages/   # YAML 提示词
│   ├── tests/
│   └── sidecar_entry.py       # PyInstaller 入口
├── frontend/                  # Vue 3 + Naive UI + ECharts
│   └── src/
├── desktop/                   # Tauri 桌面壳
├── docs/                      # PDR / 开发要求 / 部署说明
├── Dockerfile
└── docker-compose.yml
```

## 🚀 快速开始

### 环境要求

- Python 3.13+
- Node.js 22+
- Docker（部署时推荐）
- （可选）Rust + Tauri CLI（用于桌面打包）

### 启动后端

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.interfaces.main:app --reload --host 127.0.0.1 --port 8000
```

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问：

```text
http://127.0.0.1:5173
```

### Docker 部署

```bash
docker compose up -d --build
```

访问：

```text
http://127.0.0.1:8000
```

部署细节见：[`docs/部署上线说明.md`](docs/部署上线说明.md)

### 桌面打包（后续）

```bash
# 1. 构建前端
cd frontend && VITE_TAURI=true npm run build

# 2. 构建 sidecar
python scripts/build_sidecar.py

# 3. 构建 Tauri 应用
cd desktop && cargo tauri build
```

## 🧪 测试

```bash
# 后端回归测试
cd backend
python -m pytest tests/test_mvp.py -q

# 前端类型检查 + 构建
cd frontend
npx vue-tsc --noEmit
npm run build
```

## 📖 九步管线

| 步骤 | 工作流 | 说明 |
|---|---|---|
| 1 | brief | 章节概要 |
| 2 | seed | 情感种子 |
| 3 | draft | 初稿生成 |
| 4 | dialogue | 对话潜台词挖掘 |
| 5 | archaeology | 五层情感考古 |
| 6 | reader_pull | 追读力分析 |
| 7 | deepen | 加深·藏回 |
| 8 | anti_ai | 去 AI 味终检 |
| 9 | finalize | 定稿 + 衔接包 |

## 📚 文档

- [`docs/部署上线说明.md`](docs/部署上线说明.md) — Docker 部署、模型配置和上线建议
- [`docs/PDR-v4-全流程托管情感深度版.md`](docs/PDR-v4-全流程托管情感深度版.md) — 综合 PDR
- [`docs/开发要求-v4-情感深度增强版.md`](docs/开发要求-v4-情感深度增强版.md) — 执行规格
- [`docs/情感深度解决方案v2-情感考古架构.md`](docs/情感深度解决方案v2-情感考古架构.md) — 情感方案理论基础
- [`docs/PDR-桌面化改造.md`](docs/PDR-桌面化改造.md) — Tauri 桌面化方案

## 📄 License

MIT
