import importlib
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path, *, admin_token=""):
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("AI_NOVEL_MASTER_KEY_FILE", str(tmp_path / "master.key"))
    monkeypatch.setenv("AI_NOVEL_RUNTIME_SYNC", "1")
    if admin_token:
        monkeypatch.setenv("AI_NOVEL_ADMIN_TOKEN", admin_token)
    else:
        monkeypatch.delenv("AI_NOVEL_ADMIN_TOKEN", raising=False)

    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return main, TestClient(main.app)


def create_project(client):
    response = client.post("/api/projects", json={"title": "安全测试小说"})
    assert response.status_code == 200
    return response.json()


def test_credential_api_encrypts_and_never_returns_plaintext(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    project = create_project(client)
    secret = "sk-test-super-secret-123456"

    created = client.post(
        f"/api/security/projects/{project['id']}/credentials",
        json={"name": "OpenAI 主密钥", "provider": "OpenAI", "secret": secret},
    )
    assert created.status_code == 200
    payload = created.json()
    assert "secret" not in payload
    assert secret not in json.dumps(payload, ensure_ascii=False)
    assert payload["secret_hint"].startswith("sk-")

    listed = client.get(f"/api/security/projects/{project['id']}/credentials")
    assert listed.status_code == 200
    assert secret not in listed.text

    database_bytes = (tmp_path / "test.db").read_bytes()
    assert secret.encode() not in database_bytes
    key_path = tmp_path / "master.key"
    assert key_path.is_file()
    if os.name != "nt":
        assert key_path.stat().st_mode & 0o077 == 0


def test_legacy_model_config_route_moves_api_key_to_credential(monkeypatch, tmp_path):
    main, client = make_client(monkeypatch, tmp_path)
    project = create_project(client)
    secret = "sk-route-secret-abcdef"

    response = client.post(
        f"/api/projects/{project['id']}/model-configs",
        json={
            "title": "写作模型",
            "category": "OpenAI",
            "content": "gpt-test",
            "payload": {
                "provider": "OpenAI",
                "api_key": secret,
                "base_url": "https://example.invalid/v1",
                "model_name": "gpt-test",
                "is_default": True,
            },
            "status": "active",
        },
    )
    assert response.status_code == 200
    config = response.json()
    assert config["payload"]["api_key"] == ""
    assert config["payload"]["credential_id"]
    assert secret not in response.text

    public_credentials = client.get(f"/api/security/projects/{project['id']}/credentials").json()
    assert len(public_credentials) == 1
    assert secret not in json.dumps(public_credentials)

    resolved = main.resolve_model_config(project["id"], "generate_chapter_draft")
    assert resolved["payload"]["api_key"] == secret
    stored = client.get(f"/api/projects/{project['id']}/model-configs").json()[0]
    assert stored["payload"]["api_key"] == ""


def test_plaintext_migration_clears_old_model_config(monkeypatch, tmp_path):
    main, client = make_client(monkeypatch, tmp_path)
    project = create_project(client)
    from backend.app.database import connect, new_id, utc_now
    from backend.app.secret_store import migrate_plaintext_model_configs

    config_id = new_id()
    now = utc_now()
    secret = "legacy-plaintext-key"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO model_configs (id, project_id, title, category, content, payload, status, created_at, updated_at)
            VALUES (?, ?, '旧模型', 'OpenAI', 'gpt-old', ?, 'active', ?, ?)
            """,
            (
                config_id,
                project["id"],
                json.dumps({"provider": "OpenAI", "api_key": secret, "model_name": "gpt-old", "is_default": True}),
                now,
                now,
            ),
        )

    result = migrate_plaintext_model_configs()
    assert result["migrated"] == 1
    with connect() as conn:
        stored = json.loads(conn.execute("SELECT payload FROM model_configs WHERE id=?", (config_id,)).fetchone()[0])
        encrypted = conn.execute("SELECT encrypted_secret FROM encrypted_credentials WHERE project_id=?", (project["id"],)).fetchone()[0]
    assert stored["api_key"] == ""
    assert stored["credential_id"]
    assert secret not in encrypted
    assert main.resolve_model_config(project["id"], "generate_chapter_draft")["payload"]["api_key"] == secret


def test_admin_token_protects_secret_mutations(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path, admin_token="admin-test-token")
    project = create_project(client)
    endpoint = f"/api/security/projects/{project['id']}/credentials"

    denied = client.post(endpoint, json={"name": "密钥", "provider": "OpenAI", "secret": "abc123"})
    assert denied.status_code == 401

    allowed = client.post(
        endpoint,
        headers={"X-AI-Novel-Admin-Token": "admin-test-token"},
        json={"name": "密钥", "provider": "OpenAI", "secret": "abc123"},
    )
    assert allowed.status_code == 200


def test_secret_rotation_changes_hint_and_security_events(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    project = create_project(client)
    created = client.post(
        f"/api/security/projects/{project['id']}/credentials",
        json={"name": "轮换密钥", "provider": "OpenAI", "secret": "old-secret-111"},
    ).json()

    rotated = client.patch(
        f"/api/security/projects/{project['id']}/credentials/{created['id']}",
        json={"secret": "new-secret-999"},
    )
    assert rotated.status_code == 200
    assert rotated.json()["secret_hint"] != created["secret_hint"]
    assert rotated.json()["rotated_at"]

    events = client.get("/api/security/events", params={"project_id": project["id"]}).json()
    assert any(event["event_type"] == "credential.rotated" for event in events)
    assert "new-secret-999" not in json.dumps(events)
