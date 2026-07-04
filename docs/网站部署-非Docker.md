# 网站部署说明（非 Docker）

当前目标是先把项目部署成一个可访问的网站，用来测试功能是否完整。桌面打包和 Docker 都不是本阶段重点。

## 推荐方案

使用 Render / Railway 这类 Web Service 平台，把 FastAPI 后端和 Vue 前端放在同一个服务里运行：

```text
构建阶段：安装后端依赖 → 构建 frontend/dist
运行阶段：FastAPI 启动 → 后端托管 API 和前端静态页面
```

项目已经支持这种方式：`backend/app/interfaces/main.py` 会在检测到 `frontend/dist` 存在时自动托管前端页面。

## Render Blueprint

仓库根目录已经提供：

```text
render.yaml
runtime.txt
```

部署时选择从 GitHub 仓库创建 Blueprint / Web Service。

### Build Command

```bash
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
cd frontend
npm install
npm run build
```

### Start Command

```bash
python -m uvicorn backend.app.interfaces.main:app --host 0.0.0.0 --port $PORT
```

### 环境变量

```text
AI_NOVEL_DATA_DIR=/var/data
AI_NOVEL_DATABASE_URL=sqlite:////var/data/app.db
AI_NOVEL_MODEL_TIMEOUT_SECONDS=120
AI_NOVEL_GENERATION_TIMEOUT_SECONDS=900
```

如果平台支持持久化磁盘，把磁盘挂载到：

```text
/var/data
```

这样 SQLite 数据库、项目文件、llmwiki、章节正文和导出文件不会随着重启丢失。

## 上线后测试顺序

1. 打开网站首页，确认前端能正常加载。
2. 创建一个测试项目。
3. 在模型设置里填写 OpenAI 兼容接口；如果暂时不配置模型，也可以先用本地 stub 跑通流程。
4. 启动 Autopilot 托管生成。
5. 检查是否自动生成：

```text
角色档案
角色关系
关系画布
章节大纲
情感托管约束
章节正文
章节衔接包
llmwiki 页面
```

6. 打开 wiki 搜索，检查这些页面是否存在：

```text
characters.md
relationships.md
relationships/canvas.md
outlines/outline.md
chapters/index.md
bridges/index.md
关键记忆.md
```

7. 生成至少 2 章，重点检查第 2 章是否承接第 1 章末尾状态、情感余波和未决钩子。
8. 测试导出 Markdown / TXT / DOCX / PDF / EPUB。

## 重要提醒

如果只是部署到 Netlify 这类静态站点，前端页面可以打开，但 FastAPI 后端、SQLite、llmwiki、托管生成任务和导出功能都无法完整运行。因此现阶段不建议只做静态部署。

要测试完整功能，必须部署为 Web Service。也就是：网站页面和 `/api` 后端在同一个服务里运行。
