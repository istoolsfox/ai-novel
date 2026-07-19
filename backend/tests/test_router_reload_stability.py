import importlib

from fastapi.testclient import TestClient


def test_dynamic_api_routes_survive_repeated_app_reloads(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'routes.db'}")
    monkeypatch.setenv("AI_NOVEL_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("AI_NOVEL_MASTER_KEY_FILE", str(tmp_path / "master.key"))
    monkeypatch.setenv("AI_NOVEL_AUTO_MIGRATE", "1")
    monkeypatch.setenv("AI_NOVEL_RUNTIME_SYNC", "1")

    import backend.app.main as main

    for index in range(6):
        importlib.reload(main)
        main.init_app()
        with TestClient(main.app) as client:
            project = client.post("/api/projects", json={"title": f"路由重载 {index}"}).json()
            project_id = project["id"]

            responses = {
                "story_graph": client.get(f"/api/projects/{project_id}/story-graph"),
                "worldlines": client.get(f"/api/projects/{project_id}/worldlines"),
                "memory": client.get(f"/api/projects/{project_id}/memory/facts"),
                "planning": client.get(f"/api/projects/{project_id}/planning/current"),
                "obsidian": client.get(f"/api/projects/{project_id}/obsidian/status"),
                "runtime": client.get("/api/runtime/health"),
                "security": client.get("/api/security/status"),
                "migrations": client.get("/api/migrations/status"),
                "release": client.get("/api/release/info"),
            }

            assert all(response.status_code == 200 for response in responses.values()), {
                key: (response.status_code, response.text) for key, response in responses.items()
            }
            assert "stats" in responses["story_graph"].json()
            assert "worldlines" in responses["worldlines"].json()
            assert isinstance(responses["memory"].json(), list)
            assert isinstance(responses["planning"].json(), list)
            assert "exists" in responses["obsidian"].json()
            assert responses["migrations"].json()["current_version"] == 4
            assert responses["release"].json()["version"] == "1.0.0"
            assert responses["release"].json()["release_channel"] == "stable"
