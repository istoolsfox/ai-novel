import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'recovery.db'}")
    monkeypatch.setenv("AI_NOVEL_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("AI_NOVEL_MASTER_KEY_FILE", str(tmp_path / "master.key"))
    monkeypatch.setenv("AI_NOVEL_AUTO_MIGRATE", "1")
    monkeypatch.setenv("AI_NOVEL_RUNTIME_SYNC", "1")
    monkeypatch.delenv("AI_NOVEL_MASTER_KEY", raising=False)
    monkeypatch.delenv("AI_NOVEL_ADMIN_TOKEN", raising=False)

    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return main, TestClient(main.app)


def test_database_and_matching_master_key_disaster_recovery(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={"title": "灾难恢复原始项目", "genre": "悬疑"},
    ).json()
    chapter = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={
            "chapter_number": 1,
            "title": "恢复前章节",
            "draft": "这是需要从备份中恢复的稳定版正文。",
            "summary": "恢复演练原始摘要。",
            "status": "final",
        },
    ).json()
    secret = "stable-disaster-recovery-secret"
    credential = client.post(
        f"/api/security/projects/{project['id']}/credentials",
        json={"name": "恢复演练凭证", "provider": "OpenAI", "secret": secret},
    ).json()

    key_path = tmp_path / "master.key"
    original_key = key_path.read_bytes()
    backup = client.post("/api/runtime/backups", json={"note": "Stable disaster recovery baseline"}).json()
    assert backup["integrity"].lower() == "ok"
    assert Path(backup["file_path"]).is_file()

    rotated = client.post(
        "/api/security/master-key/rotate",
        json={"confirmation": "ROTATE", "new_master_key": ""},
    )
    assert rotated.status_code == 200
    assert key_path.read_bytes() != original_key

    changed = client.patch(
        f"/api/projects/{project['id']}",
        json={"title": "灾难后的错误标题", "genre": "悬疑"},
    )
    assert changed.status_code == 200
    client.patch(
        f"/api/security/projects/{project['id']}/credentials/{credential['id']}",
        json={"secret": "post-disaster-secret"},
    )
    assert client.get(f"/api/projects/{project['id']}").json()["title"] == "灾难后的错误标题"

    restored = client.post(
        f"/api/runtime/backups/{backup['id']}/restore",
        json={"confirmation": "RESTORE"},
    )
    assert restored.status_code == 200
    assert restored.json()["safety_backup"]["kind"] == "pre_restore"

    # The restored database contains ciphertext encrypted by the original key.
    # Simulate restoring the separately stored matching key before restarting.
    key_path.write_bytes(original_key)

    from backend.app.secret_store import get_credential, security_status

    recovered_project = client.get(f"/api/projects/{project['id']}").json()
    recovered_chapters = client.get(f"/api/projects/{project['id']}/chapters").json()
    recovered_credential = get_credential(project["id"], credential["id"], include_secret=True)

    assert recovered_project["title"] == "灾难恢复原始项目"
    assert recovered_chapters[0]["id"] == chapter["id"]
    assert recovered_chapters[0]["draft"] == "这是需要从备份中恢复的稳定版正文。"
    assert recovered_credential["secret"] == secret
    assert security_status()["unreadable_credentials"] == 0

    post_recovery = client.post("/api/runtime/backups", json={"note": "Post-recovery verification"})
    assert post_recovery.status_code == 200
    assert post_recovery.json()["integrity"].lower() == "ok"
