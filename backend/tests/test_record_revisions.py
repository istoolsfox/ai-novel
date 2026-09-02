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
    response = client.post("/api/projects", json={"title": "版本历史测试"})
    assert response.status_code == 200
    return response.json()["id"]


def test_create_record_snapshots_initial_revision(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)

    created = client.post(
        f"/api/projects/{project_id}/characters",
        json={"title": "沈照夜", "category": "主角", "content": "初版设定", "payload": {"name": "沈照夜"}},
    ).json()

    revisions = client.get(f"/api/projects/{project_id}/characters/{created['id']}/revisions").json()
    assert len(revisions) == 1
    assert revisions[0]["origin"] == "create"
    assert revisions[0]["content"] == "初版设定"
    assert revisions[0]["payload"] == {"name": "沈照夜"}


def test_update_record_appends_revision_and_restore_returns_previous_state(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)

    created = client.post(
        f"/api/projects/{project_id}/characters",
        json={"title": "沈照夜", "category": "主角", "content": "初版设定"},
    ).json()
    client.patch(
        f"/api/projects/{project_id}/characters/{created['id']}",
        json={"title": "沈照夜", "category": "主角", "content": "第二版设定：增加身世线索"},
    )
    client.patch(
        f"/api/projects/{project_id}/characters/{created['id']}",
        json={"title": "沈照夜", "category": "主角", "content": "第三版设定：改写动机"},
    )

    revisions = client.get(f"/api/projects/{project_id}/characters/{created['id']}/revisions").json()
    assert [item["origin"] for item in revisions] == ["update", "update", "create"]
    assert revisions[0]["content"] == "第三版设定：改写动机"
    assert revisions[-1]["content"] == "初版设定"

    restored = client.post(
        f"/api/projects/{project_id}/characters/{created['id']}/revisions/{revisions[-1]['id']}/restore"
    ).json()
    assert restored["content"] == "初版设定"

    after = client.get(f"/api/projects/{project_id}/characters/{created['id']}/revisions").json()
    assert after[0]["origin"] == "restore"
    assert after[0]["content"] == "初版设定"
    assert len(after) == 4


def test_restore_record_updates_wiki_mirror(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)

    created = client.post(
        f"/api/projects/{project_id}/characters",
        json={"title": "灰塔守夜人", "category": "主角", "content": "旧版描述"},
    ).json()
    client.patch(
        f"/api/projects/{project_id}/characters/{created['id']}",
        json={"title": "灰塔守夜人", "category": "主角", "content": "新版描述"},
    )

    revisions = client.get(f"/api/projects/{project_id}/characters/{created['id']}/revisions").json()
    client.post(f"/api/projects/{project_id}/characters/{created['id']}/revisions/{revisions[-1]['id']}/restore")

    mirrored = client.get(f"/api/projects/{project_id}/wiki/search", params={"q": "旧版描述"})
    assert mirrored.status_code == 200
    pages = mirrored.json()
    assert pages and any("旧版描述" in page["content"] for page in pages)


def test_restored_state_is_snapshot_so_new_edits_do_not_lose_history(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)

    created = client.post(
        f"/api/projects/{project_id}/characters",
        json={"title": "角色", "content": "v1"},
    ).json()
    client.patch(f"/api/projects/{project_id}/characters/{created['id']}", json={"title": "角色", "content": "v2"})
    revisions = client.get(f"/api/projects/{project_id}/characters/{created['id']}/revisions").json()
    client.post(f"/api/projects/{project_id}/characters/{created['id']}/revisions/{revisions[1]['id']}/restore")
    client.patch(f"/api/projects/{project_id}/characters/{created['id']}", json={"title": "角色", "content": "v3"})

    revisions = client.get(f"/api/projects/{project_id}/characters/{created['id']}/revisions").json()
    contents = [item["content"] for item in revisions]
    assert contents[0] == "v3"
    assert "v1" in contents and "v2" in contents


def test_delete_record_removes_its_revisions(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)

    created = client.post(
        f"/api/projects/{project_id}/characters",
        json={"title": "被删除角色", "content": "设定"},
    ).json()
    client.patch(f"/api/projects/{project_id}/characters/{created['id']}", json={"title": "被删除角色", "content": "改"})
    client.delete(f"/api/projects/{project_id}/characters/{created['id']}")

    response = client.get(f"/api/projects/{project_id}/characters/{created['id']}/revisions")
    assert response.status_code == 404


def test_revision_endpoints_reject_unknown_record_or_revision(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)

    missing_record = client.get(f"/api/projects/{project_id}/characters/not-a-record/revisions")
    assert missing_record.status_code == 404

    created = client.post(
        f"/api/projects/{project_id}/characters",
        json={"title": "角色", "content": "设定"},
    ).json()
    missing_revision = client.post(
        f"/api/projects/{project_id}/characters/{created['id']}/revisions/not-a-revision/restore"
    )
    assert missing_revision.status_code == 404


def test_revisions_are_project_scoped(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_a = create_project(client)
    project_b = client.post("/api/projects", json={"title": "另一个项目"}).json()["id"]

    created = client.post(
        f"/api/projects/{project_a}/characters",
        json={"title": "角色", "content": "设定"},
    ).json()

    response = client.get(f"/api/projects/{project_b}/characters/{created['id']}/revisions")
    assert response.status_code == 404
