import importlib

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")

    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return TestClient(main.app)


def make_project(client: TestClient) -> dict:
    project = client.post(
        "/api/projects",
        json={
            "title": "雨夜玫瑰",
            "genre": "Modern Romance",
            "audience": "网文读者",
            "tone": "克制、悬疑",
            "target_chapter_count": 40,
            "target_words_per_chapter": 3000,
        },
    )
    assert project.status_code == 200
    return project.json()


def test_world_settings_crud(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = make_project(client)
    pid = project["id"]

    created = client.post(
        f"/api/projects/{pid}/world-settings",
        json={"title": "环球集团", "category": "Companies", "content": "林氏家族企业，全球五百强", "status": "active"},
    )
    assert created.status_code == 200
    record = created.json()
    assert record["title"] == "环球集团"
    assert record["category"] == "Companies"

    listed = client.get(f"/api/projects/{pid}/world-settings")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.patch(
        f"/api/projects/{pid}/world-settings/{record['id']}",
        json={"category": "Families", "content": "改为家族企业"},
    )
    assert updated.status_code == 200
    assert updated.json()["category"] == "Families"

    deleted = client.delete(f"/api/projects/{pid}/world-settings/{record['id']}")
    assert deleted.status_code == 200
    assert len(client.get(f"/api/projects/{pid}/world-settings").json()) == 0


def test_character_relationship_crud(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = make_project(client)
    pid = project["id"]

    created = client.post(
        f"/api/projects/{pid}/character-relationships",
        json={"title": "林默 → 苏晚", "category": "Romance", "content": "林默 → 苏晚", "payload": {"source_character": "林默", "target_character": "苏晚", "relationship_type": "Romance", "strength": 87}},
    )
    assert created.status_code == 200
    record = created.json()
    assert record["payload"]["source_character"] == "林默"
    assert record["payload"]["strength"] == 87

    updated = client.patch(
        f"/api/projects/{pid}/character-relationships/{record['id']}",
        json={"payload": {"source_character": "林默", "target_character": "苏晚", "relationship_type": "Rival", "strength": 40}},
    )
    assert updated.status_code == 200
    assert updated.json()["payload"]["relationship_type"] == "Rival"


def test_timeline_event_crud(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = make_project(client)
    pid = project["id"]

    created = client.post(
        f"/api/projects/{pid}/timeline-events",
        json={"title": "2025 父亲死亡", "category": "timeline", "content": "林国峰去世，股权争夺开始"},
    )
    assert created.status_code == 200
    record = created.json()
    assert record["title"] == "2025 父亲死亡"

    listed = client.get(f"/api/projects/{pid}/timeline-events")
    assert len(listed.json()) == 1

    deleted = client.delete(f"/api/projects/{pid}/timeline-events/{record['id']}")
    assert deleted.status_code == 200
    assert len(client.get(f"/api/projects/{pid}/timeline-events").json()) == 0


def test_foreshadowings_sync_to_wiki(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = make_project(client)
    pid = project["id"]

    record = client.post(
        f"/api/projects/{pid}/foreshadowings",
        json={"title": "神秘戒指", "category": "foreshadowing", "content": "来历不明，埋下伏笔", "status": "open"},
    ).json()

    wiki = client.get(f"/api/projects/{pid}/wiki/read", params={"path": "foreshadowing.md"})
    assert wiki.status_code == 200
    assert "神秘戒指" in wiki.json()["content"]


def test_records_are_project_scoped(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_a = make_project(client)
    project_b = client.post("/api/projects", json={"title": "另一部"}).json()

    client.post(f"/api/projects/{project_a['id']}/world-settings", json={"title": "A 独有实体", "category": "Locations"})

    a_list = client.get(f"/api/projects/{project_a['id']}/world-settings").json()
    b_list = client.get(f"/api/projects/{project_b['id']}/world-settings").json()
    assert len(a_list) == 1
    assert len(b_list) == 0
    assert any(r["title"] == "A 独有实体" for r in a_list)


def test_unknown_resource_rejected(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = make_project(client)
    pid = project["id"]

    response = client.get(f"/api/projects/{pid}/world-entities")
    assert response.status_code == 404


def test_generation_context_builds_chapter_assets(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = make_project(client)
    pid = project["id"]

    client.post(f"/api/projects/{pid}/character-profiles", json={"title": "林默", "category": "character", "content": "男主"})
    client.post(f"/api/projects/{pid}/foreshadowings", json={"title": "神秘戒指", "category": "foreshadowing", "status": "open"})
    chapter = client.post(f"/api/projects/{pid}/chapters", json={"chapter_number": 1, "title": "第 1 章"}).json()

    context = client.get(f"/api/projects/{pid}/memory/context")
    assert context.status_code == 200
    data = context.json()
    assert isinstance(data, dict)
