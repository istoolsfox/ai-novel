"""后端托管 SPA 时，通用资源 GET 路由绝不能被 SPA 兜底吞掉。

回归背景：release_bootstrap 的启动路由重排会把 /api/projects/{id}/{resource}
移到路由表末尾；旧实现用 catch-all 路由托管 SPA，会抢走这些 GET 请求并返回
index.html，导致生产模式下人物等列表页永远为空（开发模式无 SPA 挂载测不出）。
"""

import importlib

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path) -> TestClient:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>spa-index</body></html>", encoding="utf-8")
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("AI_NOVEL_FRONTEND_DIR", str(dist))

    import backend.app.main as main

    importlib.reload(main)
    main.init_app()

    # 复现启动期路由重排：通用资源路由被移到路由表最后
    from backend.app.router_install import move_legacy_generic_project_routes_last

    move_legacy_generic_project_routes_last(main.app)
    return TestClient(main.app)


def test_api_routes_win_over_spa_fallback(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    # 未知 API 路径：必须是 JSON 404，而不是 index.html
    response = client.get("/api/projects/nonexistent/character-profiles")
    assert response.status_code == 404
    assert "text/html" not in response.headers.get("content-type", "")
    assert response.json()["detail"] == "Project not found"

    # 已有项目的资源列表：返回真实 JSON
    project_id = client.post("/api/projects", json={"title": "SPA 回归"}).json()["id"]
    created = client.post(
        f"/api/projects/{project_id}/character-profiles",
        json={"title": "沈照夜", "category": "主角"},
    ).json()
    listing = client.get(f"/api/projects/{project_id}/character-profiles")
    assert listing.headers["content-type"].startswith("application/json")
    assert [item["title"] for item in listing.json()] == ["沈照夜"]
    assert created["title"] == "沈照夜"


def test_unknown_frontend_path_serves_index_html(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    page = client.get("/dashboard")
    assert page.status_code == 200
    assert "spa-index" in page.text
