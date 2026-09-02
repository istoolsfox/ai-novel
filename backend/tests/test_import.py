"""导入功能测试：整本按章节切分导入；片段自动分层并匹配章节。"""

import importlib

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return TestClient(main.app)


def create_project(client: TestClient, title: str = "导入测试") -> str:
    return client.post("/api/projects", json={"title": title}).json()["id"]


NOVEL = """第一章 风起

少年推开门，风雪灌了进来。他攥紧了手中的信。

第二章 旧友

茶馆里，故人早已等候多时。

第三章 抉择

灯下，他终于下定了决心。
"""


def test_preview_novel_detects_chapters(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)
    result = client.post(f"/api/projects/{project_id}/import/preview", json={"content": NOVEL}).json()
    assert result["mode"] == "novel"
    assert result["chapter_count"] == 3
    assert [item["title"] for item in result["items"]] == ["第一章 风起", "第二章 旧友", "第三章 抉择"]


def test_import_novel_creates_chapters(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)
    result = client.post(f"/api/projects/{project_id}/import", json={"content": NOVEL, "filename": "试写"}).json()
    assert result["mode"] == "novel"
    assert result["imported_chapters"] == 3
    chapters = client.get(f"/api/projects/{project_id}/chapters").json()
    assert [c["chapter_number"] for c in chapters] == [1, 2, 3]
    assert chapters[0]["title"] == "第一章 风起"
    assert chapters[0]["draft"].startswith("少年推开门")
    assert chapters[2]["word_count"] > 0


def test_import_continues_existing_numbering(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)
    client.post(
        f"/api/projects/{project_id}/chapters",
        json={"chapter_number": 1, "title": "已有章节", "draft": "已有内容"},
    )
    client.post(f"/api/projects/{project_id}/import", json={"content": NOVEL})
    chapters = client.get(f"/api/projects/{project_id}/chapters").json()
    assert [c["chapter_number"] for c in chapters] == [1, 2, 3, 4]


def test_fragment_prose_matches_existing_chapter(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)
    client.post(
        f"/api/projects/{project_id}/chapters",
        json={
            "chapter_number": 1,
            "title": "风起",
            "draft": "少年推开门，风雪灌了进来。他攥紧了手中的信，那是来自北境的密函。",
        },
    )
    fragment = "风雪更急了。少年回头望了一眼城门，把信塞进了怀里，头也不回地走进了风雪。"
    preview = client.post(f"/api/projects/{project_id}/import/preview", json={"content": fragment}).json()
    assert preview["mode"] == "fragment"
    assert preview["layer"] == "chapter"
    assert preview["matched_chapter"] is not None
    assert preview["matched_chapter"]["title"] == "风起"

    result = client.post(f"/api/projects/{project_id}/import", json={"content": fragment}).json()
    assert result["appended_to"]["title"] == "风起"
    chapters = client.get(f"/api/projects/{project_id}/chapters").json()
    assert len(chapters) == 1
    assert "头也不回地走进了风雪" in chapters[0]["draft"]


def test_fragment_character_goes_to_characters(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)
    fragment = "姓名：沈照夜\n年龄：二十四\n身份：前朝公主\n性格：冷静、警惕、重诺\n外貌：眉目清冷，常着玄色斗篷。"
    preview = client.post(f"/api/projects/{project_id}/import/preview", json={"content": fragment}).json()
    assert preview["layer"] == "character"
    result = client.post(f"/api/projects/{project_id}/import", json={"content": fragment, "filename": "沈照夜设定"}).json()
    assert result["layer"] == "character"
    records = client.get(f"/api/projects/{project_id}/character-profiles").json()
    assert len(records) == 1
    assert records[0]["title"] == "沈照夜设定"
    assert "前朝公主" in records[0]["content"]


def test_fragment_world_goes_to_world_settings(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)
    fragment = "世界观设定：九洲大陆，灵气充沛。修炼体系分炼气、筑基、金丹三境。宗门势力以青云宗为尊，货币用灵石。"
    result = client.post(f"/api/projects/{project_id}/import", json={"content": fragment}).json()
    assert result["layer"] == "world"
    records = client.get(f"/api/projects/{project_id}/world-settings").json()
    assert len(records) == 1
    assert "九洲大陆" in records[0]["content"]


def test_fragment_without_match_creates_new_chapter(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)
    client.post(
        f"/api/projects/{project_id}/chapters",
        json={"chapter_number": 1, "title": "风起", "draft": "少年推开门，风雪灌了进来。"},
    )
    fragment = "深海的灯笼鱼列成一线，幽蓝的光缓缓扫过沉船的桅杆，像是在给亡者点名。"
    result = client.post(f"/api/projects/{project_id}/import", json={"content": fragment}).json()
    assert "created_chapter" in result
    chapters = client.get(f"/api/projects/{project_id}/chapters").json()
    assert len(chapters) == 2


def test_import_rejects_empty(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)
    assert client.post(f"/api/projects/{project_id}/import", json={"content": "   "}).status_code == 400
    assert client.post(f"/api/projects/{project_id}/import/preview", json={"content": ""}).status_code == 400
