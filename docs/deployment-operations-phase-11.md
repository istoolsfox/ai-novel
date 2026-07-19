# Phase 11: deployment and operations

This phase turns the phase-ten Web/Worker runtime into an operable single-machine deployment.

## Recommended deployment: Docker Compose

```bash
cp deploy/.env.example .env
docker compose up -d --build
docker compose ps
```

Open `http://127.0.0.1:8080`.

The Compose stack contains:

- `frontend`: Nginx static frontend and `/api` reverse proxy.
- `backend`: FastAPI Web process. It creates jobs but does not execute production jobs in Web-owned threads.
- `worker`: independent SQLite lease Worker for autopilot, Obsidian export, and scheduled backups.
- `ai-novel-data`: persistent SQLite database, project files, Vault exports, and backups.

Useful commands:

```bash
docker compose logs -f backend
docker compose logs -f worker
docker compose restart worker
docker compose down
```

`docker compose down` keeps the named volume. Do not add `-v` unless the stored novels, database, exports, and backups should be deleted.

## Windows PowerShell

Docker Desktop deployment:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/start-docker.ps1
powershell -ExecutionPolicy Bypass -File scripts/windows/stop-docker.ps1
```

Local three-process development deployment:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/start-local.ps1
powershell -ExecutionPolicy Bypass -File scripts/windows/stop-local.ps1
```

The local launcher starts FastAPI, the independent Worker, and Vite separately and writes their process IDs to `.runtime/local-processes.json`.

## systemd

Expected layout:

- repository: `/opt/ai-novel`
- virtual environment: `/opt/ai-novel/.venv`
- persistent data: `/var/lib/ai-novel`
- environment file: `/etc/ai-novel.env`
- service user: `ai-novel`

Example installation:

```bash
sudo useradd --system --home /var/lib/ai-novel --shell /usr/sbin/nologin ai-novel
sudo mkdir -p /opt/ai-novel /var/lib/ai-novel
sudo chown -R ai-novel:ai-novel /opt/ai-novel /var/lib/ai-novel

python3 -m venv /opt/ai-novel/.venv
/opt/ai-novel/.venv/bin/pip install -r /opt/ai-novel/backend/requirements.txt

sudo cp deploy/systemd/ai-novel.env.example /etc/ai-novel.env
sudo cp deploy/systemd/ai-novel-web.service /etc/systemd/system/
sudo cp deploy/systemd/ai-novel-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ai-novel-web ai-novel-worker
```

Logs:

```bash
sudo journalctl -u ai-novel-web -f
sudo journalctl -u ai-novel-worker -f
```

## Nginx and server-sent events

`deploy/nginx.conf` disables proxy buffering for project API routes. This is required for the autopilot server-sent event stream to update the frontend without waiting for a buffered response.

## Operations center

The frontend now has two launchers:

- `托管控制台`: writing, memory, graph, plans, worldlines, and Obsidian.
- `运行中心`: health, Workers, queues, logs, backups, restore, automatic backup schedule, and deployment commands.

The operations center refreshes runtime state every five seconds while open.

## Runtime health

```text
GET /api/runtime/health
GET /api/runtime/diagnostics
GET /api/runtime/workers
GET /api/runtime/tasks
GET /api/runtime/events
POST /api/runtime/recover
```

The health response becomes `degraded` when queued work has no healthy Worker, stale leases are found, automatic backups are enabled without a Worker, or the most recent scheduled backup failed.

Runtime event filters:

```text
GET /api/runtime/events?event_type=task.completed
GET /api/runtime/events?worker_id=<worker-id>
GET /api/runtime/events?task_id=<task-id>
```

## Automatic database backups

The schedule is disabled by default.

```text
GET  /api/runtime/backup-schedule
PUT  /api/runtime/backup-schedule
POST /api/runtime/backup-schedule/run-now
```

Example:

```json
{
  "enabled": true,
  "interval_hours": 24,
  "retention_count": 7
}
```

Any `all` or `exports` Worker may claim a due backup. Claiming uses a SQLite transaction and a lease, so concurrent Workers do not create the same scheduled backup twice.

Scheduled backup retention deletes only backups whose manifest kind is `scheduled`. Manual and pre-restore safety backups are not removed by the schedule.

The `run-now` endpoint enables the schedule and sets its next run to the current time. A healthy Worker performs the backup on its next poll.

## Restore safety

The frontend requires selecting a backup and entering `RESTORE`. The backend independently requires the same confirmation and rejects restore when:

- a healthy Worker exists;
- an autopilot job is queued, running, or paused;
- a runtime task is queued or running;
- checksum or SQLite integrity verification fails.

Before replacing the active database, the backend creates a `pre_restore` safety backup.

## Environment variables

```text
AI_NOVEL_DATABASE_URL
AI_NOVEL_DATA_DIR
AI_NOVEL_BACKUP_DIR
AI_NOVEL_RUNTIME_LEASE_SECONDS
AI_NOVEL_RUNTIME_HEARTBEAT_SECONDS
AI_NOVEL_PORT
```

Docker defaults:

```text
AI_NOVEL_DATABASE_URL=sqlite:////data/app.db
AI_NOVEL_DATA_DIR=/data/projects
AI_NOVEL_BACKUP_DIR=/data/backups
AI_NOVEL_PORT=8080
```

## Current limits

- Docker Compose and systemd target one machine.
- SQLite remains a single-writer database.
- The browser reports Worker state but does not kill operating-system processes.
- TLS and public-domain configuration remain the responsibility of the deployment reverse proxy.
- Secrets are still supplied through environment files; a cloud secret manager is not included.
- Automatic backups run only while at least one `all` or `exports` Worker is healthy.
