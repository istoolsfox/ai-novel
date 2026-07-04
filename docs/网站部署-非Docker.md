# 网站部署说明（非 Docker）

当前目标是先把项目部署成一个可访问的网站，用来测试功能是否完整。桌面打包和 Docker 都不是本阶段重点。

## 免费测试方案

先用 Render Free Web Service 跑功能测试。仓库根目录的 `render.yaml` 已经改成免费配置：

```text
plan: free
AI_NOVEL_DATA_DIR=/tmp/ai-novel-data
AI_NOVEL_DATABASE_URL=sqlite:////tmp/ai-novel-data/app.db
```

这个模式适合先看功能链路是否跑通：页面、API、Autopilot、llmwiki、关系画布和导出都可以测试。

需要注意：免费模式没有持久化磁盘，服务休眠、重启或重新部署后，SQLite 数据库、项目文件、章节正文和 llmwiki 可能丢失。所以它适合“上线功能测试”，不适合长期保存小说项目。

## Cloudflare 域名接入

如果你想用自己的域名访问网站，建议让 Cloudflare 负责域名解析 / HTTPS / CDN，实际应用仍然跑在 Render Free Web Service 上。

详细步骤见：

```text
docs/Cloudflare域名部署.md
```

推荐结构：

```text
用户访问你的域名
  ↓
Cloudflare DNS / HTTPS
  ↓
Render Free Web Service
  ↓
FastAPI 后端托管 Vue 前端 + API
```

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

### 免费测试环境变量

```text
AI_NOVEL_DATA_DIR=/tmp/ai-novel-data
AI_NOVEL_DATABASE_URL=sqlite:////tmp/ai-novel-data/app.db
AI_NOVEL_MODEL_TIMEOUT_SECONDS=120
AI_NOVEL_GENERATION_TIMEOUT_SECONDS=900
```

### 后续持久化配置

如果后续要长期保存数据，再改成付费持久化磁盘，例如挂载到：

```text
/var/data
```

并把环境变量改为：

```text
AI_NOVEL_DATA_DIR=/var/data
AI_NOVEL_DATABASE_URL=sqlite:////var/data/app.db
```

这样 SQLite 数据库、项目文件、llmwiki、章节正文和导出文件才不会随着重启丢失。

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

如果只是部署到 Netlify / Cloudflare Pages 这类静态站点，前端页面可以打开，但 FastAPI 后端、SQLite、llmwiki、托管生成任务和导出功能都无法完整运行。因此现阶段不建议只做静态部署。

要测试完整功能，必须部署为 Web Service。也就是：网站页面和 `/api` 后端在同一个服务里运行。