import importlib

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")

    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return TestClient(main.app)


def test_project_creation_creates_local_memory_directories(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    response = client.post(
        "/api/projects",
        json={
            "title": "前朝公主",
            "topic": "被流放的公主发现能改写记忆的古籍",
            "genre": "奇幻",
            "audience": "网文读者",
            "tone": "克制、悬疑",
            "target_chapter_count": 5,
            "target_words_per_chapter": 3000,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    root = tmp_path / "data" / "projects" / payload["id"]
    assert payload["project_root_path"] == str(root)
    assert (root / "memory" / "raw_sources").is_dir()
    assert (root / "memory" / "wiki").is_dir()
    assert (root / "memory" / "index").is_dir()


def test_chapter_versions_are_bound_to_project_and_chapter(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    project = client.post("/api/projects", json={"title": "项目 A"}).json()
    other_project = client.post("/api/projects", json={"title": "项目 B"}).json()
    chapter = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={"chapter_number": 1, "title": "第一章"},
    ).json()

    version = client.post(
        f"/api/projects/{project['id']}/chapters/{chapter['id']}/versions",
        json={"label": "版本 A", "content": "她在边境小城修补古籍。"},
    )
    assert version.status_code == 200

    wrong_project_response = client.post(
        f"/api/projects/{other_project['id']}/chapters/{chapter['id']}/versions",
        json={"label": "错误版本", "content": "不应该写入。"},
    )
    assert wrong_project_response.status_code == 404

    select_response = client.post(
        f"/api/projects/{project['id']}/chapters/{chapter['id']}/versions/{version.json()['id']}/select"
    )
    assert select_response.status_code == 200
    assert select_response.json()["draft"] == "她在边境小城修补古籍。"


def test_wiki_write_blocks_path_traversal_and_records_revisions(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "记忆测试"}).json()

    traversal = client.post(
        f"/api/projects/{project['id']}/wiki/write",
        json={"path": "../outside.md", "content": "逃逸写入"},
    )
    assert traversal.status_code == 400

    write_response = client.post(
        f"/api/projects/{project['id']}/wiki/write",
        json={"path": "characters/heroine.md", "content": "# 女主\n\n她害怕失去记忆。"},
    )
    assert write_response.status_code == 200
    assert write_response.json()["path"] == "characters/heroine.md"

    read_response = client.get(
        f"/api/projects/{project['id']}/wiki/read",
        params={"path": "characters/heroine.md"},
    )
    assert read_response.status_code == 200
    assert "失去记忆" in read_response.json()["content"]

    revisions = client.get(
        f"/api/projects/{project['id']}/wiki/revisions",
        params={"path": "characters/heroine.md"},
    )
    assert revisions.status_code == 200
    assert len(revisions.json()) == 1


def test_export_only_contains_current_project_chapters(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "导出项目"}).json()
    other_project = client.post("/api/projects", json={"title": "其他项目"}).json()

    chapter = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={"chapter_number": 1, "title": "第一章", "draft": "这是当前项目正文。"},
    ).json()
    client.post(
        f"/api/projects/{other_project['id']}/chapters",
        json={"chapter_number": 1, "title": "外部章节", "draft": "不应导出。"},
    )

    client.post(f"/api/projects/{project['id']}/chapters/{chapter['id']}/finalize")

    markdown = client.get(f"/api/projects/{project['id']}/export/markdown")
    text = client.get(f"/api/projects/{project['id']}/export/txt")

    assert markdown.status_code == 200
    assert text.status_code == 200
    assert "这是当前项目正文" in markdown.text
    assert "不应导出" not in markdown.text
    assert "这是当前项目正文" in text.text
    assert "不应导出" not in text.text
