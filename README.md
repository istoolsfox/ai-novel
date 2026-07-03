# AI 小说创作平台 · 全流程托管情感深度版

> 本地优先的 AI 长篇小说生成桌面应用。核心差异化是**情感感染力**——文字富含深意，区别于纯爽感导向和纯工程导向的工具。

## ✨ 核心特性

- **九步管线托管生成**：启动后全自动跑完，仅检查点/熔断暂停
- **情感考古架构**：种子 → 自由生长 → 三视角考古（潜意识/读者体感/母题回响）→ 加深·藏回
- **垂直五层情感模型**：表层 → 情感层 → 意层 → 潜层 → 韵层
- **对话潜台词挖掘**：四层（表层台词 / 语气层 / 未尽之言 / 动机泄露）
- **追读力系统**：情感钩子 > 情节钩子，情感债务追踪与兑现
- **角色声纹库**：注入 → 检查 → 回写闭环，保证人物对话一致性
- **叙事记忆**：考古发现横向注入下一章种子，实现跨章情感沉积
- **AI 蓝图自动生成**：根据项目设定生成完整卷蓝图（情感气候/伏笔规划/角色弧线）
- **断点续跑**：中断后恢复不重跑已完成步骤
- **桌面化打包**：Tauri 2.0 + PyInstaller sidecar，可独立分发

## 🏗️ 架构总览

```
┌─────────────────────────────────────────────┐
│  Vue 3 + Naive UI 前端（SSE 实时进度）       │
└──────────────────┬──────────────────────────┘
                   │ fetch / SSE
┌──────────────────▼──────────────────────────┐
│  FastAPI 后端（DDD 分层）                    │
│  ├── interfaces/   路由层                   │
│  ├── application/  用例层                   │
│  ├── engine/       引擎（管线+调度+熔断）     │
│  ├── workflows/    工作流（含 LLM 客户端）     │
│  ├── domain/       领域模型                  │
│  ├── infrastructure/  数据库+存储            │
│  └── prompt_packages/  YAML 提示词包         │
└──────────────────┬──────────────────────────┘
                   │ 文件 I/O
┌──────────────────▼──────────────────────────┐
│  SQLite (WAL) + 项目文件系统                  │
└─────────────────────────────────────────────┘
```

## 🛠️ 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLite (WAL) + Python 3.13 |
| 前端 | Vue 3 + Naive UI + ECharts + TypeScript + Vite |
| 桌面 | Tauri 2.0 + PyInstaller sidecar |
| 提示词 | YAML 配置包（代码与提示词分离） |

## 📁 目录结构

```
ai-novel/
├── backend/
│   ├── app/
│   │   ├── interfaces/        # FastAPI 路由
│   │   ├── application/       # 业务用例
│   │   ├── engine/            # 九步管线 + Orchestrator
│   │   ├── workflows/         # 生成工作流 + LLM 客户端
│   │   ├── domain/            # Pydantic 模型
│   │   ├── infrastructure/    # SQLite + 文件存储
│   │   └── prompt_packages/   # YAML 提示词
│   ├── tests/
│   └── sidecar_entry.py       # PyInstaller 入口
├── frontend/                  # Vue 3 + Naive UI
│   └── src/
│       ├── api/               # API 客户端 + 类型
│       ├── stores/            # Pinia 状态管理
│       ├── components/         # 9 个核心业务组件
│       ├── layouts/           # 主布局
│       ├── views/             # 页面
│       └── router/            # Vue Router
├── desktop/                   # Tauri 桌面壳
│   └── src/                   # Rust (main/sidecar/config)
├── scripts/                   # 打包脚本
└── docs/                      # PDR + 开发要求
```

## 🚀 快速开始

### 环境要求

- Python 3.13+
- Node.js 22+
- （可选）Rust + Tauri CLI（用于桌面打包）

### 启动后端

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install fastapi uvicorn pydantic pyyaml openai httpx python-docx reportlab ebooklib
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://127.0.0.1:5173

### 桌面打包（可选）

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

- [`docs/PDR-v4-全流程托管情感深度版.md`](docs/PDR-v4-全流程托管情感深度版.md) — 综合 PDR
- [`docs/开发要求-v4-情感深度增强版.md`](docs/开发要求-v4-情感深度增强版.md) — 执行规格
- [`docs/情感深度解决方案v2-情感考古架构.md`](docs/情感深度解决方案v2-情感考古架构.md) — 情感方案理论基础
- [`docs/PDR-桌面化改造.md`](docs/PDR-桌面化改造.md) — Tauri 桌面化方案

## 📄 License

MIT
