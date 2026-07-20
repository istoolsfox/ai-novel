import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("AI_NOVEL_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.delenv("AI_NOVEL_RUNTIME_SYNC", raising=False)
    monkeypatch.delenv("AI_NOVEL_AUTOPILOT_SYNC", raising=False)

    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return main, TestClient(main.app)


def test_worker_runs_scheduled_backups_and_applies_retention(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    from backend.app.runtime_worker import RuntimeWorker

    initial = client.get("/api/runtime/backup-schedule")
    assert initial.status_code == 200
    assert initial.json()["enabled"] is False

    configured = client.put(
        "/api/runtime/backup-schedule",
        json={"enabled": True, "interval_hours": 1, "retention_count": 1},
    )
    assert configured.status_code == 200
    assert configured.json()["enabled"] is True

    client.post("/api/runtime/backup-schedule/run-now")
    first_worker = RuntimeWorker(worker_type="exports", worker_id="scheduled-worker-1")
    assert first_worker.run_once() is True
    first_worker.stop()

    first_schedule = client.get("/api/runtime/backup-schedule").json()
    assert first_schedule["last_backup_id"]
    assert first_schedule["last_error"] == ""

    client.post("/api/runtime/backup-schedule/run-now")
    second_worker = RuntimeWorker(worker_type="exports", worker_id="scheduled-worker-2")
    assert second_worker.run_once() is True
    second_worker.stop()

    backups = client.get("/api/runtime/backups").json()
    scheduled = [backup for backup in backups if backup["kind"] == "scheduled"]
    assert len(scheduled) == 1
    assert scheduled[0]["id"] == client.get("/api/runtime/backup-schedule").json()["last_backup_id"]


def test_runtime_events_support_filters(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    from backend.app.runtime_queue import append_runtime_event

    append_runtime_event("test.alpha", "alpha", worker_id="worker-a", task_id="task-a")
    append_runtime_event("test.beta", "beta", worker_id="worker-b", task_id="task-b")

    events = client.get("/api/runtime/events", params={"event_type": "test.alpha", "worker_id": "worker-a"})
    assert events.status_code == 200
    assert len(events.json()) == 1
    assert events.json()[0]["task_id"] == "task-a"


def test_deployment_files_keep_web_worker_and_data_separate():
    root = Path(__file__).resolve().parents[2]
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    nginx = (root / "deploy/nginx.conf").read_text(encoding="utf-8")
    backend_dockerfile = (root / "Dockerfile.backend").read_text(encoding="utf-8")
    frontend_dockerfile = (root / "Dockerfile.frontend").read_text(encoding="utf-8")

    assert "backend:" in compose
    assert "worker:" in compose
    assert "frontend:" in compose
    assert "ai-novel-data:/data" in compose
    assert "backend.app.runtime_worker" in compose
    assert "proxy_buffering off" in nginx
    assert "backend.app.main:app" in backend_dockerfile
    assert "npm run build" in frontend_dockerfile

    required = [
        root / "scripts/windows/start-docker.ps1",
        root / "scripts/windows/stop-docker.ps1",
        root / "scripts/windows/start-local.ps1",
        root / "scripts/windows/stop-local.ps1",
        root / "deploy/systemd/ai-novel-web.service",
        root / "deploy/systemd/ai-novel-worker.service",
    ]
    assert all(path.is_file() for path in required)
