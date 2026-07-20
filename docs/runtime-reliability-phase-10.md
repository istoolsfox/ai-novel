# 阶段十：独立 Worker 与运行可靠性

本阶段把长时间任务从 FastAPI Web 进程中移出。Web 进程只创建任务和提供状态接口，独立 Worker 通过 SQLite 原子认领、租约和心跳执行任务。

## 运行结构

```text
浏览器 / API
      |
      v
FastAPI Web ---- 写入 SQLite 队列
      |
      +---- generation_jobs（章节托管）
      +---- runtime_tasks（Obsidian 导出等通用任务）
                         |
                         v
                 Independent Worker
```

Web 重启不会丢失任务。Worker 意外退出后，租约到期的任务会被其他 Worker 或手动恢复接口重新排队。

## 启动方式

在仓库根目录启动 Web：

```bash
uvicorn backend.app.main:app --reload
```

另开一个终端启动 Worker：

```bash
python -m backend.app.runtime_worker
```

只执行一个任务后退出，适合测试或计划任务：

```bash
python -m backend.app.runtime_worker --once
```

只处理章节托管：

```bash
python -m backend.app.runtime_worker --worker-type autopilot
```

只处理 Obsidian 导出：

```bash
python -m backend.app.runtime_worker --worker-type exports
```

PowerShell 中使用相同的 `python -m` 命令即可。

## 兼容模式

生产默认使用独立 Worker。测试中可以同步执行：

```bash
AI_NOVEL_RUNTIME_SYNC=1
```

原有 `AI_NOVEL_AUTOPILOT_SYNC=1` 也会进入同步测试模式。

旧版进程内线程仅在显式配置后启用：

```bash
AI_NOVEL_AUTOPILOT_LEGACY_THREADS=1
```

不建议在生产环境继续使用旧线程模式。

## 心跳与租约

默认配置：

```text
AI_NOVEL_RUNTIME_LEASE_SECONDS=90
AI_NOVEL_RUNTIME_HEARTBEAT_SECONDS=10
```

执行模型请求或导出时，Worker 会持续刷新自身和任务心跳。只有租约过期后，任务才允许被恢复，避免两个 Worker 同时执行同一项工作。

## 健康和诊断接口

```text
GET  /api/runtime/health
GET  /api/runtime/diagnostics
GET  /api/runtime/workers
GET  /api/runtime/tasks
GET  /api/runtime/tasks/{task_id}
GET  /api/runtime/events
POST /api/runtime/recover
```

当队列中存在任务但没有健康 Worker 时，健康状态为 `degraded`，并返回明确警告。

## 异步 Obsidian 导出

生产模式下：

```text
POST /api/projects/{project_id}/obsidian/export
```

返回 `queued` 和 `task_id`。状态查询：

```text
GET /api/projects/{project_id}/obsidian/status
GET /api/projects/{project_id}/obsidian/jobs/{task_id}
```

Worker 完成后，原有 Manifest 与 ZIP 下载接口保持不变。

## 数据库备份

```text
GET    /api/runtime/backups
POST   /api/runtime/backups
GET    /api/runtime/backups/{backup_id}?verify=true
GET    /api/runtime/backups/{backup_id}/download
DELETE /api/runtime/backups/{backup_id}
```

备份使用 SQLite Backup API 创建，并保存：

- SHA-256 校验值
- SQLite 完整性检查结果
- 文件大小
- 创建时间
- 备注和备份类型

默认目录位于数据库旁的 `backups/`，也可通过 `AI_NOVEL_BACKUP_DIR` 修改。

## 数据库恢复

恢复接口：

```text
POST /api/runtime/backups/{backup_id}/restore
```

请求体：

```json
{
  "confirmation": "RESTORE"
}
```

恢复前必须满足：

1. 所有独立 Worker 已停止。
2. 没有 queued、running 或 paused 的章节托管任务。
3. 没有 queued 或 running 的通用异步任务。
4. 备份 SHA-256 和 SQLite integrity check 均通过。

正式覆盖前，系统会自动创建一份 `pre_restore` 安全备份。恢复使用临时数据库和原子替换，避免半写入数据库。

## 当前边界

- 队列仍基于本地 SQLite，适合单机或共享同一磁盘的部署。
- 不支持多台机器通过网络文件系统并发运行 Worker。
- Worker 数量可以增加，但 SQLite 写入仍是单写者模型。
- 数据库恢复要求先停止 Worker，尚未提供在线热恢复。
- 定时自动备份策略尚未加入，本阶段提供安全的备份与恢复原语。
