# AI Novel Workbench

**当前版本：`1.0.0-rc.1`**

AI Novel Workbench 是一个本地优先的 AI 长篇小说创作、自动托管和知识管理系统。它使用 FastAPI、React、SQLite 与独立 Worker，在一台电脑上完成章节生成、连续性检查、记忆编译、剧情规划、世界线分叉、Obsidian 导出、备份恢复和运行维护。

正文、记忆、世界线、数据库和模型凭证默认保存在本机。系统不会因为使用远程模型而自动上传整个项目，只会向已配置的模型服务发送当前工作流所需上下文。

## 主要能力

- 多章节自动托管：章节简报、初稿、章节契约、连续性检查、自动修复、复检、定稿和记忆编译。
- 长篇一致性：硬事实、人物状态、知识边界、关系、物品、叙事债务和伏笔。
- 剧情规划：多线剧情图谱、剧情节点和边、影响传播、停滞检测和滚动章节计划。
- 世界线：从任意章节分叉，隔离正文和状态，支持激活、提升主线、归档和差异比较。
- 可视化控制台：托管中心、可拖拽剧情图谱、世界线比较、运行中心、安全中心和升级中心。
- Obsidian：按世界线导出 Markdown Vault、Canvas、清单和 ZIP，支持增量更新。
- 独立 Worker：SQLite 租约、心跳、失联恢复、异步导出和自动备份。
- 安全：本地 Fernet 加密 API Key、可选管理令牌、密钥轮换和旧密钥恢复。
- 升级：带校验和的数据库迁移、升级前快照、失败自动恢复和人工回滚。
- 发布：确定性源码包、SHA-256 清单、Docker 镜像验证和黄金路径端到端测试。

## 最快启动方式：Docker Desktop

安装 Docker Desktop 后，在项目根目录执行：

```bash
cp deploy/.env.example .env
docker compose up -d --build
```

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/start-docker.ps1
```

打开：

```text
http://127.0.0.1:8080
```

停止服务但保留数据：

```bash
docker compose down
```

默认持久化数据保存在 Docker 卷 `ai-novel-data` 中。不要使用 `docker compose down -v`，除非明确准备删除数据库、项目、备份和本地主密钥。

## Windows 本地启动

不使用 Docker 时，先安装 Python 3.12 和 Node.js 22：

```powershell
python -m pip install -r backend/requirements.txt
cd frontend
npm ci
cd ..
powershell -ExecutionPolicy Bypass -File scripts/windows/start-local.ps1
```

本地地址：

```text
前端：http://127.0.0.1:5173
后端：http://127.0.0.1:8000
接口文档：http://127.0.0.1:8000/docs
```

停止：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/stop-local.ps1
```

## Linux systemd

模板位于：

```text
deploy/systemd/ai-novel-web.service
deploy/systemd/ai-novel-worker.service
deploy/systemd/ai-novel.env.example
```

安装并修改路径后：

```bash
sudo systemctl enable --now ai-novel-web ai-novel-worker
sudo systemctl status ai-novel-web ai-novel-worker
```

## 首次启动

首次打开时会出现发布就绪向导，检查：

- SQLite 完整性和数据目录写入权限
- 数据库迁移版本
- 本地凭证加密状态
- 模型配置
- 独立 Worker 心跳
- 数据库备份

核心检查通过后，可以先确认使用 Stub 模式进入，也可以先在“安全中心”保存真实模型 API Key。

## 模型配置与加密凭证

原“设置 → 模型配置”仍可使用。后端会透明处理 API Key：

1. 接收新密钥。
2. 使用本地主密钥加密。
3. 将密文写入 `encrypted_credentials`。
4. 将普通模型配置中的 `api_key` 清空。
5. 仅保存 `credential_id` 和脱敏提示。
6. 模型调用时在内存中临时解密。

可在“安全中心”查看、轮换、停用、测试和删除凭证。

本地主密钥默认位于数据库旁的 `.ai-novel-master.key`。它不会写入数据库，也被 Git 忽略。数据库备份和主密钥应分别安全保存；丢失主密钥后，已有加密凭证无法恢复。

公网或多人可访问环境建议在 `.env` 中配置：

```env
AI_NOVEL_ADMIN_TOKEN=<随机长令牌>
AI_NOVEL_MASTER_KEY=<由 Secret Manager 提供的 Fernet Key>
```

## 数据库升级和回滚

生产 Web 默认在健康检查通过前自动执行已知迁移：

```env
AI_NOVEL_AUTO_MIGRATE=1
```

升级前会创建 `pre_upgrade` 快照。迁移校验和漂移、未知版本、运行中的 Worker 或任务都会阻止升级。

CLI：

```bash
python -m backend.app.migration_cli status
python -m backend.app.migration_cli plan
python -m backend.app.migration_cli apply
python -m backend.app.migration_cli rollback <backup-id>
python -m backend.app.migration_cli rotate-key
```

也可以通过前端“升级中心”操作。

## 备份与恢复

“运行中心”支持：

- 手动 SQLite 在线备份
- 自动备份周期与保留数量
- SHA-256 和 SQLite 完整性验证
- 下载和删除备份
- 带 `RESTORE` 确认的安全恢复
- 恢复前自动创建 `pre_restore` 安全备份

## 构建发布包

```bash
python scripts/build_release.py --output release-dist
python scripts/build_release.py --output release-dist --verify
```

生成：

```text
ai-novel-workbench-<version>-source.zip
ai-novel-workbench-<version>-manifest.json
SHA256SUMS
release-result.json
```

源码包排除 `.env`、主密钥、数据库、项目数据、备份和依赖目录，并包含逐文件 SHA-256 清单。

## 测试

后端全量：

```bash
python -m pytest backend/tests -q
```

前端：

```bash
cd frontend
npm ci
npm test
npm run build
```

Docker 发布验证由 `.github/workflows/release-validation.yml` 实际构建后端与前端镜像、启动 Compose、检查版本 API、Schema、页面和独立 Worker 心跳。

## 重要目录

```text
backend/app/          后端、Worker、迁移和导出逻辑
backend/tests/        后端与端到端测试
frontend/src/         编辑器和各控制中心
deploy/               Nginx、环境变量和 systemd 模板
scripts/windows/      Windows 一键启动与停止
scripts/build_release.py  发布包构建器
docs/                 各阶段和运维文档
```

## 发布说明

完整变更见 [CHANGELOG.md](CHANGELOG.md)。`1.0.0-rc.1` 是发布候选版本：功能链已经完成并进入真实镜像、升级回滚和黄金路径验收阶段。除非明确创建版本标签或手动批准发布工作流，否则仓库不会自动创建 GitHub Release。
