import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("AI_NOVEL_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("AI_NOVEL_MASTER_KEY_FILE", str(tmp_path / "master.key"))
    monkeypatch.setenv("AI_NOVEL_AUTO_MIGRATE", "0")
    monkeypatch.setenv("AI_NOVEL_RUNTIME_SYNC", "1")
    monkeypatch.delenv("AI_NOVEL_MASTER_KEY", raising=False)
    monkeypatch.delenv("AI_NOVEL_ADMIN_TOKEN", raising=False)

    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return main, TestClient(main.app)


def create_project(client, title="迁移测试小说"):
    response = client.post("/api/projects", json={"title": title})
    assert response.status_code == 200
    return response.json()


def test_migration_plan_apply_and_idempotency(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    create_project(client)

    plan = client.get("/api/migrations/plan")
    assert plan.status_code == 200
    assert plan.json()["current_version"] == 0
    assert [item["version"] for item in plan.json()["pending"]] == [1, 2, 3, 4]
    assert plan.json()["can_apply"] is True

    applied = client.post("/api/migrations/apply", json={"confirmation": "APPLY"})
    assert applied.status_code == 200
    payload = applied.json()
    assert payload["applied_versions"] == [1, 2, 3, 4]
    assert payload["backup"]["kind"] == "pre_upgrade"

    status = client.get("/api/migrations/status").json()
    assert status["status"] == "current"
    assert status["current_version"] == 4
    assert len(status["applied"]) == 4

    second = client.post("/api/migrations/apply", json={"confirmation": "APPLY"})
    assert second.status_code == 200
    assert second.json()["status"] == "current"
    assert second.json()["applied_versions"] == []


def test_checksum_drift_blocks_upgrade(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    client.post("/api/migrations/apply", json={"confirmation": "APPLY"})
    from backend.app.database import connect

    with connect() as conn:
        conn.execute("UPDATE schema_migrations SET checksum='tampered' WHERE version=2")

    plan = client.get("/api/migrations/plan").json()
    assert plan["status"] == "drift"
    assert plan["can_apply"] is False
    assert plan["drift"][0]["version"] == 2


def test_active_worker_blocks_migration(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    from backend.app.runtime_queue import register_worker

    register_worker("upgrade-blocker", "all")
    plan = client.get("/api/migrations/plan").json()
    assert plan["can_apply"] is False
    assert any("workers" in blocker.lower() for blocker in plan["blockers"])

    response = client.post("/api/migrations/apply", json={"confirmation": "APPLY"})
    assert response.status_code == 409


def test_upgrade_rollback_restores_pre_upgrade_snapshot(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    project = create_project(client, "升级前标题")
    applied = client.post("/api/migrations/apply", json={"confirmation": "APPLY"}).json()
    backup_id = applied["backup"]["id"]

    updated = client.patch(f"/api/projects/{project['id']}", json={"title": "升级后修改"})
    assert updated.status_code == 200
    assert client.get(f"/api/projects/{project['id']}").json()["title"] == "升级后修改"

    rolled_back = client.post(
        f"/api/migrations/rollback/{backup_id}",
        json={"confirmation": "ROLLBACK"},
    )
    assert rolled_back.status_code == 200
    assert rolled_back.json()["status"] == "rolled_back"
    assert client.get(f"/api/projects/{project['id']}").json()["title"] == "升级前标题"
    assert rolled_back.json()["restore"]["safety_backup"]["kind"] == "pre_restore"


def test_failed_migration_restores_snapshot_and_records_rollback(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    create_project(client)
    import backend.app.migration_service as service

    def fail_after_schema_change(conn):
        conn.execute("CREATE TABLE migration_should_disappear (id TEXT PRIMARY KEY)")
        raise RuntimeError("intentional migration failure")

    failing = service.Migration(5, "intentional_failure", "Exercise automatic snapshot rollback.", fail_after_schema_change)
    monkeypatch.setattr(service, "MIGRATIONS", service.MIGRATIONS + (failing,))
    monkeypatch.setattr(service, "LATEST_SCHEMA_VERSION", 5)

    with pytest.raises(ValueError, match="database snapshot was restored"):
        service.apply_pending_migrations(confirmation="APPLY")

    from backend.app.database import connect

    with connect() as conn:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='migration_should_disappear'"
        ).fetchone()
        run = conn.execute("SELECT status, error_message FROM migration_runs ORDER BY started_at DESC LIMIT 1").fetchone()
    assert table is None
    assert run["status"] == "rolled_back"
    assert "intentional migration failure" in run["error_message"]


def test_master_key_rotation_and_restore(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    project = create_project(client)
    secret = "rotation-secret-value"
    credential = client.post(
        f"/api/security/projects/{project['id']}/credentials",
        json={"name": "轮换凭证", "provider": "OpenAI", "secret": secret},
    ).json()
    key_path = tmp_path / "master.key"
    old_key = key_path.read_bytes()

    rotated = client.post(
        "/api/security/master-key/rotate",
        json={"confirmation": "ROTATE", "new_master_key": ""},
    )
    assert rotated.status_code == 200
    rotation = rotated.json()
    assert rotation["status"] == "completed"
    assert rotation["previous_fingerprint"] != rotation["new_fingerprint"]
    assert key_path.read_bytes() != old_key
    assert Path(rotation["key_backup_path"]).is_file()

    from backend.app.secret_store import get_credential

    assert get_credential(project["id"], credential["id"], include_secret=True)["secret"] == secret

    restored = client.post(
        f"/api/security/master-key/rotations/{rotation['rotation_id']}/restore",
        json={"confirmation": "RESTORE_KEY"},
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "restored"
    assert key_path.read_bytes() == old_key
    assert get_credential(project["id"], credential["id"], include_secret=True)["secret"] == secret


def test_environment_managed_master_key_rotation_is_blocked(monkeypatch, tmp_path):
    from cryptography.fernet import Fernet

    _main, client = make_client(monkeypatch, tmp_path)
    monkeypatch.setenv("AI_NOVEL_MASTER_KEY", Fernet.generate_key().decode("ascii"))
    response = client.post(
        "/api/security/master-key/rotate",
        json={"confirmation": "ROTATE", "new_master_key": ""},
    )
    assert response.status_code == 409
    assert "environment" in response.json()["detail"].lower()
