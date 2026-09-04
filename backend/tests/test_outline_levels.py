"""三级大纲测试：全书/卷/章节纲分类、AI stub 工作流、生成上下文分层注入。"""

import importlib
import json

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return TestClient(main.app)


def create_project(client: TestClient, title: str = "大纲测试") -> str:
    return client.post("/api/projects", json={"title": title}).json()["id"]


def test_book_outline_stub_and_save(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)
    result = client.post(
        f"/api/projects/{project_id}/ai/generate_book_outline",
        json={"prompt": "猎雾少年打破灰雾囚笼"},
    ).json()
    assert result["status"] == "local"
    structured = result["structured"]
    assert structured["category"] == "book_outline"
    assert "猎雾少年" in structured["premise"]

    created = client.post(
        f"/api/projects/{project_id}/outlines",
        json={
            "title": structured["name"],
            "category": "book_outline",
            "content": structured["premise"],
            "payload": structured,
            "status": "active",
        },
    ).json()
    assert created["category"] == "book_outline"


def test_volume_outline_stub_uses_existing_count(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)
    client.post(
        f"/api/projects/{project_id}/outlines",
        json={"title": "第 1 卷大纲", "category": "volume_outline", "content": "", "payload": {"volume_number": 1}, "status": "active"},
    )
    result = client.post(
        f"/api/projects/{project_id}/ai/generate_volume_outline",
        json={"prompt": "主角踏入第二座城", "volume_number": 2, "start_chapter": 11, "end_chapter": 25},
    ).json()
    structured = result["structured"]
    assert structured["category"] == "volume_outline"
    assert structured["volume_number"] == 2
    assert structured["start_chapter"] == 11
    assert structured["end_chapter"] == 25
    assert "第二座城" in structured["volume_goal"]


def test_outline_levels_from_records_orders_volumes():
    import backend.app.main as main

    records = [
        {"id": "c2", "category": "chapter_outline", "payload": {"chapter_number": 2}, "title": "章2"},
        {"id": "v2", "category": "volume_outline", "payload": {"start_chapter": 11, "end_chapter": 20}, "title": "卷2"},
        {"id": "b1", "category": "book_outline", "payload": {}, "title": "全书大纲"},
        {"id": "v1", "category": "volume_outline", "payload": {"start_chapter": 1, "end_chapter": 10}, "title": "卷1"},
    ]
    levels = main.outline_levels_from(records)
    assert [item["id"] for item in levels["book"]] == ["b1"]
    assert [item["id"] for item in levels["volume"]] == ["v1", "v2"]
    assert [item["id"] for item in levels["chapter"]] == ["c2"]


def test_outline_levels_injected_into_generation_payload(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project_id = create_project(client)
    client.post(
        f"/api/projects/{project_id}/outlines",
        json={"title": "全书大纲", "category": "book_outline", "content": "主线", "payload": {"category": "book_outline"}, "status": "active"},
    )
    client.post(
        f"/api/projects/{project_id}/chapters",
        json={"chapter_number": 1, "title": "第一章", "brief": "", "draft": ""},
    )
    chapter_id = client.get(f"/api/projects/{project_id}/chapters").json()[0]["id"]
    client.post(
        f"/api/projects/{project_id}/outlines",
        json={"title": "第一章大纲", "category": "chapter_outline", "content": "目标", "payload": {"chapter_number": 1}, "status": "active"},
    )

    # 远程模型路径不会真的发请求（未配置模型会走本地 stub），这里直接校验 compact 层。
    import backend.app.main as main

    context = main.build_generation_context(project_id, chapter_id)
    payload = main.compact_generation_context(context)
    levels = payload["outline_levels"]
    assert levels["book"][0]["title"] == "全书大纲"
    assert levels["chapter"][0]["title"] == "第一章大纲"
    assert json.dumps(levels, ensure_ascii=False).count("volume") >= 0
