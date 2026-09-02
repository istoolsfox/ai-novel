"""单账号登录与 API 鉴权测试：存在账号即启用登录，无账号时保持开放。"""

import importlib

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path, admin_user: str | None = None, admin_password: str | None = None):
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    if admin_user is None:
        monkeypatch.delenv("AI_NOVEL_ADMIN_USER", raising=False)
        monkeypatch.delenv("AI_NOVEL_ADMIN_PASSWORD", raising=False)
    else:
        monkeypatch.setenv("AI_NOVEL_ADMIN_USER", admin_user)
        monkeypatch.setenv("AI_NOVEL_ADMIN_PASSWORD", admin_password or "secret-password")

    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return TestClient(main.app), main


def test_without_account_api_stays_open(monkeypatch, tmp_path):
    client, main = make_client(monkeypatch, tmp_path)
    assert not main.accounts_exist()
    response = client.post("/api/projects", json={"title": "无需登录"})
    assert response.status_code == 200


def test_env_bootstrap_creates_account_and_protects_api(monkeypatch, tmp_path):
    client, main = make_client(monkeypatch, tmp_path, "lyq", "strong-pass")
    assert main.accounts_exist()

    # 未带 token → 401
    assert client.get("/api/projects").status_code == 401

    # 公开路径不受限
    assert client.get("/api/health").status_code == 200

    # 错误密码 → 401
    bad = client.post("/api/auth/login", json={"username": "lyq", "password": "wrong"})
    assert bad.status_code == 401

    # 正确登录 → token → 访问成功
    ok = client.post("/api/auth/login", json={"username": "lyq", "password": "strong-pass"})
    assert ok.status_code == 200
    token = ok.json()["token"]
    assert ok.json()["username"] == "lyq"

    authorized = client.get("/api/projects", headers={"Authorization": f"Bearer {token}"})
    assert authorized.status_code == 200

    status = client.get("/api/auth/status", headers={"Authorization": f"Bearer {token}"}).json()
    assert status["account_mode"] is True
    assert status["authenticated"] is True
    assert status["username"] == "lyq"


def test_logout_revokes_session(monkeypatch, tmp_path):
    client, _main = make_client(monkeypatch, tmp_path, "lyq", "pw-123456")
    token = client.post("/api/auth/login", json={"username": "lyq", "password": "pw-123456"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/projects", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/projects", headers=headers).status_code == 401


def test_env_password_change_syncs_account_hash(monkeypatch, tmp_path):
    client, _main = make_client(monkeypatch, tmp_path, "lyq", "old-password")
    assert client.post("/api/auth/login", json={"username": "lyq", "password": "old-password"}).status_code == 200

    # 重启（reload + init）时环境变量里的新密码会同步到账号
    import os

    os.environ["AI_NOVEL_ADMIN_PASSWORD"] = "new-password"
    try:
        import backend.app.main as main

        importlib.reload(main)
        main.init_app()
        reopened = TestClient(main.app)
        assert reopened.post("/api/auth/login", json={"username": "lyq", "password": "old-password"}).status_code == 401
        assert reopened.post("/api/auth/login", json={"username": "lyq", "password": "new-password"}).status_code == 200
    finally:
        os.environ.pop("AI_NOVEL_ADMIN_PASSWORD", None)


def test_bootstrap_is_idempotent_and_unique(monkeypatch, tmp_path):
    client, main = make_client(monkeypatch, tmp_path, "lyq", "same-pass")
    main.init_app()
    main.init_app()

    from backend.app.database import connect

    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM user_accounts").fetchone()[0]
    assert count == 1
