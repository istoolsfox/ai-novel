"""AI 工作流在未配置远程模型时的本地占位兜底测试。"""

import importlib

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")

    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return TestClient(main.app)


def create_project(client: TestClient) -> str:
    return client.post("/api/projects", json={"title": "本地占位测试"}).json()["id"]


def test_generate_characters_falls_back_to_structured_stub_without_model_config(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)

    response = client.post(
        f"/api/projects/{project_id}/ai/generate_characters",
        json={"prompt": "一位背负秘密的守夜人", "existing_character_names": ["沈照夜", "顾临舟", "苏晚"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "local"
    assert data["model"] == "local-stub"
    assert isinstance(data["structured"], list) and data["structured"]
    character = data["structured"][0]
    assert character["name"] == "谢无咎"
    assert "name" in character and "role" in character


def test_generate_setting_stub_returns_world_entities(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)

    response = client.post(
        f"/api/projects/{project_id}/ai/generate_setting",
        json={"prompt": "记忆改写的灰塔之城"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "local"
    entities = data["structured"]
    assert isinstance(entities, list) and len(entities) >= 3
    categories = {entity["category"] for entity in entities}
    assert {"Locations", "Organizations", "Rules"} <= categories
    assert all(entity.get("name") and entity.get("description") for entity in entities)


def test_extract_relationships_stub_returns_relationship_payload(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)
    client.post(
        f"/api/projects/{project_id}/character-profiles",
        json={"title": "沈照夜", "content": "主角", "payload": {"name": "沈照夜"}},
    )
    client.post(
        f"/api/projects/{project_id}/character-profiles",
        json={"title": "苏晚", "content": "抄录员", "payload": {"name": "苏晚"}},
    )

    response = client.post(f"/api/projects/{project_id}/ai/extract_relationships", json={"prompt": "梳理当前关系"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "local"
    relationships = data["structured"]
    assert isinstance(relationships, list) and relationships
    relation = relationships[0]
    for key in ("source_character", "target_character", "relationship_type", "strength"):
        assert key in relation


def test_stub_fallback_still_records_ai_run(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)

    response = client.post(f"/api/projects/{project_id}/ai/generate_setting", json={"prompt": "测试"})
    assert response.status_code == 200
    assert response.json()["status"] == "local"
