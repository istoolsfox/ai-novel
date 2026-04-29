import importlib
import json

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


def test_delete_chapter_removes_only_current_project_chapter_and_versions(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    project = client.post("/api/projects", json={"title": "项目 A"}).json()
    other_project = client.post("/api/projects", json={"title": "项目 B"}).json()
    chapter = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={"chapter_number": 1, "title": "第一章"},
    ).json()
    other_chapter = client.post(
        f"/api/projects/{other_project['id']}/chapters",
        json={"chapter_number": 1, "title": "外部章节"},
    ).json()
    client.post(
        f"/api/projects/{project['id']}/chapters/{chapter['id']}/versions",
        json={"label": "版本 A", "content": "应随章节删除。"},
    )

    wrong_project_delete = client.delete(f"/api/projects/{other_project['id']}/chapters/{chapter['id']}")
    assert wrong_project_delete.status_code == 404

    deleted = client.delete(f"/api/projects/{project['id']}/chapters/{chapter['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True

    assert client.get(f"/api/projects/{project['id']}/chapters/{chapter['id']}").status_code == 404
    assert client.get(f"/api/projects/{other_project['id']}/chapters/{other_chapter['id']}").status_code == 200
    assert client.get(f"/api/projects/{project['id']}/chapters/{chapter['id']}/versions").status_code == 404


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


def test_auth_endpoints_keep_local_mode_optional(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)

    status = client.get("/api/auth/status")
    assert status.status_code == 200
    assert status.json()["mode"] == "local"
    assert status.json()["authenticated"] is False

    start = client.get("/api/auth/oauth/openai/start")
    assert start.status_code == 200
    assert start.json()["provider"] == "openai"
    assert start.json()["requires_redirect"] is False

    callback = client.get("/api/auth/oauth/openai/callback", params={"code": "mock-code"})
    assert callback.status_code == 200
    assert callback.json()["authenticated"] is True
    assert callback.json()["user"]["provider"] == "openai"

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200
    assert logout.json()["mode"] == "local"


def test_project_delete_requires_password(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_NOVEL_DELETE_PASSWORD", "123456")
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "危险项目"}).json()

    wrong_password = client.request(
        "DELETE",
        f"/api/projects/{project['id']}",
        json={"password": "wrong"},
    )
    assert wrong_password.status_code == 403

    still_exists = client.get(f"/api/projects/{project['id']}")
    assert still_exists.status_code == 200

    deleted = client.request(
        "DELETE",
        f"/api/projects/{project['id']}",
        json={"password": "123456"},
    )
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True

    missing = client.get(f"/api/projects/{project['id']}")
    assert missing.status_code == 404


def test_character_profile_save_syncs_to_llmwiki(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "角色同步"}).json()

    response = client.post(
        f"/api/projects/{project['id']}/character-profiles",
        json={
            "title": "沈照夜",
            "category": "character",
            "content": "流放公主",
            "payload": {
                "name": "沈照夜",
                "role": "前朝公主",
                "desire": "夺回被篡改的记忆",
                "voice": "克制、冷静",
            },
            "status": "active",
        },
    )

    assert response.status_code == 200
    wiki = client.get(
        f"/api/projects/{project['id']}/wiki/read",
        params={"path": "characters/沈照夜.md"},
    )
    assert wiki.status_code == 200
    assert "前朝公主" in wiki.json()["content"]
    assert "夺回被篡改的记忆" in wiki.json()["content"]

    relationship = client.post(
        f"/api/projects/{project['id']}/character-relationships",
        json={
            "title": "沈照夜 → 主线剧情",
            "category": "主线关联",
            "content": "她是改写记忆古籍的持有者",
            "payload": {
                "source_character": "沈照夜",
                "target_character": "主线剧情",
                "relationship_type": "主线关联",
                "conflict": "她是改写记忆古籍的持有者",
            },
            "status": "active",
        },
    )

    assert relationship.status_code == 200
    relationship_wiki = client.get(
        f"/api/projects/{project['id']}/wiki/read",
        params={"path": "relationships.md"},
    )
    assert relationship_wiki.status_code == 200
    assert "沈照夜 → 主线剧情" in relationship_wiki.json()["content"]
    assert "改写记忆古籍" in relationship_wiki.json()["content"]


def test_outline_wiki_rebuilds_without_duplicate_chapter_sections(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "大纲去重"}).json()

    client.post(
        f"/api/projects/{project['id']}/outlines",
        json={
            "title": "第一章 旧书夜市",
            "category": "chapter_outline",
            "content": "旧版目标：发现一本普通旧书。",
            "payload": {
                "chapter_number": "1",
                "chapter_title": "第一章 旧书夜市",
                "chapter_goal": "旧版目标",
            },
        },
    )
    client.post(
        f"/api/projects/{project['id']}/outlines",
        json={
            "title": "第1章 旧书夜市",
            "category": "chapter_outline",
            "content": "新版目标：发现古籍并付出记忆代价。",
            "payload": {
                "chapter_number": "1",
                "chapter_title": "第1章 旧书夜市",
                "chapter_goal": "新版目标",
            },
        },
    )

    wiki = client.get(
        f"/api/projects/{project['id']}/wiki/read",
        params={"path": "outline.md"},
    )

    assert wiki.status_code == 200
    content = wiki.json()["content"]
    assert "新版目标" in content
    assert "旧版目标" not in content
    assert content.count("旧书夜市") == 1


def test_deleting_outline_removes_synced_wiki_page_and_rebuilds_index(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "删除大纲"}).json()
    first = client.post(
        f"/api/projects/{project['id']}/outlines",
        json={
            "title": "第一章大纲",
            "category": "chapter_outline",
            "content": "发现古籍",
            "payload": {"chapter_number": "1", "chapter_title": "第一章"},
        },
    ).json()
    client.post(
        f"/api/projects/{project['id']}/outlines",
        json={
            "title": "第二章大纲",
            "category": "chapter_outline",
            "content": "追查线索",
            "payload": {"chapter_number": "2", "chapter_title": "第二章"},
        },
    )

    deleted = client.delete(f"/api/projects/{project['id']}/outlines/{first['id']}")
    outline_index = client.get(f"/api/projects/{project['id']}/wiki/read", params={"path": "outline.md"})
    removed_page = client.get(f"/api/projects/{project['id']}/wiki/read", params={"path": "outlines/第一章大纲.md"})

    assert deleted.status_code == 200
    assert "发现古籍" not in outline_index.json()["content"]
    assert "追查线索" in outline_index.json()["content"]
    assert removed_page.status_code == 404


def test_remote_outline_generation_prompt_requires_title_focus_and_no_duplicate_events(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "远程大纲"}).json()
    chapter = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={"chapter_number": 3, "title": "第三章 旧盟重逢", "brief": "主角见到旧盟友"},
    ).json()
    client.post(
        f"/api/projects/{project['id']}/model-configs",
        json={
            "title": "测试模型",
            "category": "OpenAI",
            "payload": {
                "api_key": "test-key",
                "base_url": "https://example.test/v1",
                "model_name": "writer-model",
                "is_default": True,
            },
        },
    )
    client.post(
        f"/api/projects/{project['id']}/timeline-events",
        json={"title": "发现古籍", "category": "event", "content": "第一章已经发现古籍"},
    )

    import backend.app.main as main

    captured: dict[str, str] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "{}"}}]}).encode("utf-8")

    def fake_urlopen(request, timeout=0):
        captured["body"] = request.data.decode("utf-8")
        captured["timeout"] = str(timeout)
        return FakeResponse()

    monkeypatch.setattr(main.urllib.request, "urlopen", fake_urlopen)

    response = client.post(
        f"/api/projects/{project['id']}/ai/generate_outline",
        json={
            "chapter_id": chapter["id"],
            "prompt": "生成第三章大纲",
            "generation_contract": {
                "use_llmwiki": True,
                "avoid_duplicate_events": True,
                "focus_chapter_title": "第三章 旧盟重逢",
            },
        },
    )

    assert response.status_code == 200
    body = captured["body"]
    assert "第三章 旧盟重逢" in body
    assert "不得生成与已有大纲、时间线或 llmwiki 页面相同或高度相似的事件" in body
    assert "必须围绕当前章节标题" in body
    assert int(captured["timeout"]) >= 600


def test_generation_timeout_message_treats_slow_model_as_still_generating(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "慢生成"}).json()
    client.post(
        f"/api/projects/{project['id']}/model-configs",
        json={
            "title": "测试模型",
            "category": "OpenAI",
            "payload": {
                "api_key": "test-key",
                "base_url": "https://example.test/v1",
                "model_name": "writer-model",
                "is_default": True,
            },
        },
    )

    import backend.app.main as main

    def fake_urlopen(_request, timeout=0):
        raise TimeoutError("timed out")

    monkeypatch.setattr(main.urllib.request, "urlopen", fake_urlopen)

    response = client.post(
        f"/api/projects/{project['id']}/ai/generate_outline",
        json={"prompt": "生成 5 章大纲"},
    )

    assert response.status_code == 200
    output = response.json()
    assert output["status"] == "fallback"
    assert "仍可能在生成" in output["error"]
    assert "调小生成长度" not in output["error"]


def test_ai_workflow_returns_structured_json_and_generation_context(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "上下文项目"}).json()
    chapter = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={"chapter_number": 1, "title": "第一章", "brief": "发现古籍", "draft": "她发现古籍。"},
    ).json()
    client.post(
        f"/api/projects/{project['id']}/character-profiles",
        json={"title": "沈照夜", "category": "character", "content": "主角", "payload": {"name": "沈照夜"}},
    )
    client.post(
        f"/api/projects/{project['id']}/outlines",
        json={
            "title": "第一章大纲",
            "category": "chapter_outline",
            "content": "发现古籍并付出代价",
            "payload": {"chapter_title": "第一章", "chapter_goal": "发现古籍"},
        },
    )

    character_ai = client.post(
        f"/api/projects/{project['id']}/ai/generate_characters",
        json={"prompt": "生成一位女主角"},
    ).json()
    assert character_ai["structured"]["name"]
    assert character_ai["items"][0]["content"].startswith("{")

    draft_ai = client.post(
        f"/api/projects/{project['id']}/ai/generate_chapter_draft",
        json={"chapter_id": chapter["id"], "prompt": "写第一章"},
    ).json()
    context = draft_ai["context"]
    assert "characters" in context
    assert "outlines" in context
    assert "wiki_pages" in context
    assert any(item["title"] == "沈照夜" for item in context["characters"])
    assert draft_ai["status"] == "local"
    assert "本地占位" in draft_ai["error"]


def test_remote_chapter_draft_drops_frontend_generation_context_from_model_prompt(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "远程正文上下文"}).json()
    chapter = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={
            "chapter_number": 1,
            "title": "第一章",
            "brief": "雨夜发现古籍",
            "draft": "旧稿" * 8000,
        },
    ).json()
    client.post(
        f"/api/projects/{project['id']}/model-configs",
        json={
            "title": "测试模型",
            "category": "OpenAI",
            "payload": {
                "api_key": "test-key",
                "base_url": "https://example.test/v1",
                "model_name": "writer-model",
                "temperature": 0.7,
                "max_tokens": 1200,
                "is_default": True,
            },
        },
    )
    client.post(
        f"/api/projects/{project['id']}/character-profiles",
        json={
            "title": "沈照夜",
            "category": "character",
            "content": "主角",
            "payload": {"name": "沈照夜", "desire": "查清古籍代价"},
        },
    )

    import backend.app.main as main

    captured: dict[str, str] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "雨夜里，她第一次听见古籍翻页。"}}]},
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout=0):
        captured["body"] = request.data.decode("utf-8")
        captured["timeout"] = str(timeout)
        return FakeResponse()

    monkeypatch.setattr(main.urllib.request, "urlopen", fake_urlopen)

    response = client.post(
        f"/api/projects/{project['id']}/ai/generate_chapter_draft",
        json={
            "chapter_id": chapter["id"],
            "chapter_number": 1,
            "prompt": "写第一章",
            "current_draft": "旧稿" * 8000,
            "generation_context": {
                "wiki_pages": [{"path": "huge.md", "content": "FRONTEND_DUPLICATE_CONTEXT" * 1000}]
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["text"].startswith("雨夜里")
    body = captured["body"]
    assert "FRONTEND_DUPLICATE_CONTEXT" not in body
    assert len(body) < 30000
    assert int(captured["timeout"]) >= 180


def test_model_connection_test_requires_real_model_config_and_does_not_fallback(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "连接测试"}).json()

    missing = client.post(
        f"/api/projects/{project['id']}/ai/test-connection",
        json={"base_url": "https://api.example.com/v1", "model_name": ""},
    )
    assert missing.status_code == 400
    assert "API Key" in missing.json()["detail"]


def test_model_connection_timeout_reports_local_proxy_layer(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "连接测试"}).json()

    import backend.app.main as main

    def fake_urlopen(_request, timeout=0):
        raise TimeoutError("timed out")

    monkeypatch.setattr(main.urllib.request, "urlopen", fake_urlopen)

    response = client.post(
        f"/api/projects/{project['id']}/ai/test-connection",
        json={
            "api_key": "test-key",
            "base_url": "http://127.0.0.1:8317/v1",
            "model_name": "gpt-5.5",
        },
    )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "本地模型代理" in detail
    assert "127.0.0.1:8317" in detail
    assert "上游" in detail


def test_local_character_generation_avoids_existing_character_names(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "不重复角色"}).json()
    client.post(
        f"/api/projects/{project['id']}/character-profiles",
        json={"title": "沈照夜", "category": "character", "content": "主角", "payload": {"name": "沈照夜"}},
    )

    character_ai = client.post(
        f"/api/projects/{project['id']}/ai/generate_characters",
        json={
            "prompt": "生成一位新角色",
            "existing_character_names": ["沈照夜"],
            "generation_contract": {"avoid_duplicate_names": True},
        },
    ).json()

    assert character_ai["structured"]["name"] != "沈照夜"
    assert "沈照夜" not in character_ai["text"].split('"name":', 1)[1].split(",", 1)[0]


def test_finalize_chapter_extracts_memory_to_structured_records_and_wiki(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "定稿记忆"}).json()
    chapter = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={
            "chapter_number": 1,
            "title": "雨夜",
            "brief": "主角发现古籍",
            "draft": "雨夜，沈照夜发现古籍，并埋下古籍会吞噬记忆的伏笔。",
        },
    ).json()

    finalized = client.post(f"/api/projects/{project['id']}/chapters/{chapter['id']}/finalize")

    assert finalized.status_code == 200
    timeline = client.get(f"/api/projects/{project['id']}/timeline-events").json()
    foreshadowings = client.get(f"/api/projects/{project['id']}/foreshadowings").json()
    assert timeline
    assert foreshadowings
    wiki_timeline = client.get(
        f"/api/projects/{project['id']}/wiki/read",
        params={"path": "timeline.md"},
    )
    wiki_foreshadowing = client.get(
        f"/api/projects/{project['id']}/wiki/read",
        params={"path": "foreshadowing.md"},
    )
    assert wiki_timeline.status_code == 200
    assert wiki_foreshadowing.status_code == 200
