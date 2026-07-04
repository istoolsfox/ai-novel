import importlib
import json
from pathlib import Path

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")

    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return TestClient(main.app)


def create_story_prerequisites(client: TestClient, project_id: str, chapter_number: int = 1, chapter_title: str = "第一章"):
    client.post(
        f"/api/projects/{project_id}/character-profiles",
        json={"title": "沈照夜", "category": "character", "content": "主角", "payload": {"name": "沈照夜"}},
    )
    client.post(
        f"/api/projects/{project_id}/outlines",
        json={
            "title": f"{chapter_title}大纲",
            "category": "chapter_outline",
            "content": "主角发现关键线索并付出代价。",
            "payload": {
                "chapter_number": str(chapter_number),
                "chapter_title": chapter_title,
                "chapter_goal": "发现关键线索",
            },
        },
    )


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


def test_wiki_count_reports_project_memory_page_count(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "记忆计数"}).json()

    assert client.get(f"/api/projects/{project['id']}/wiki/count").json()["count"] == 0

    client.post(
        f"/api/projects/{project['id']}/wiki/write",
        json={"path": "characters/heroine.md", "content": "# 女主\n\n她记得停摆日。"},
    )
    client.post(
        f"/api/projects/{project['id']}/wiki/write",
        json={"path": "outline.md", "content": "# 大纲\n\n一百章完本。"},
    )

    count = client.get(f"/api/projects/{project['id']}/wiki/count")

    assert count.status_code == 200
    assert count.json()["count"] == 2


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


def test_export_manifest_reports_deliverable_status(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={"title": "交付清单", "target_chapter_count": 2},
    ).json()
    first = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={
            "chapter_number": 1,
            "title": "第一章",
            "draft": "第一章正文。" * 120,
            "status": "final",
        },
    ).json()
    second = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={
            "chapter_number": 2,
            "title": "第二章",
            "draft": "第二章正文。" * 120,
            "status": "final",
        },
    ).json()
    from backend.app.infrastructure.database import create_chapter_quality_score

    create_chapter_quality_score(project["id"], first["id"], {"total_score": 92, "ok": True, "metrics": {}})
    create_chapter_quality_score(project["id"], second["id"], {"total_score": 88, "ok": True, "metrics": {}})

    manifest = client.get(f"/api/projects/{project['id']}/export/manifest")

    assert manifest.status_code == 200
    data = manifest.json()
    assert data["deliverable"] is True
    assert data["chapter_count"] == 2
    assert data["final_chapter_count"] == 2
    assert data["average_quality_score"] == 90
    assert data["missing_chapter_numbers"] == []
    assert data["unfinished_chapters"] == []
    manifest_path = Path(project["project_root_path"]) / "exports" / "manifest.json"
    assert manifest_path.exists()
    assert "交付清单" in manifest_path.read_text(encoding="utf-8")


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


def test_outline_sync_uses_single_aggregate_wiki_page(monkeypatch, tmp_path):
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

    per_chapter_page = client.get(f"/api/projects/{project['id']}/wiki/read", params={"path": "outlines/第一章大纲.md"})
    count_before_delete = client.get(f"/api/projects/{project['id']}/wiki/count")
    deleted = client.delete(f"/api/projects/{project['id']}/outlines/{first['id']}")
    outline_index = client.get(f"/api/projects/{project['id']}/wiki/read", params={"path": "outline.md"})

    assert per_chapter_page.status_code == 404
    assert count_before_delete.json()["count"] == 1
    assert deleted.status_code == 200
    assert "发现古籍" not in outline_index.json()["content"]
    assert "追查线索" in outline_index.json()["content"]


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


def test_local_chapter_draft_generates_chapter_specific_prose(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={
            "title": "百章完本压力测试",
            "target_chapter_count": 100,
            "target_words_per_chapter": 1200,
            "logline": "修档师在一百个记忆档案中追查城市停摆真相。",
        },
    ).json()
    chapter = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={
            "chapter_number": 37,
            "title": "第37章 灰塔回声",
            "brief": "扩展：闻岚处理第 37 份记忆档案，围绕“灰塔回声”推进主线，并发现上一卷的胜利其实留下新的代价。",
        },
    ).json()
    client.post(
        f"/api/projects/{project['id']}/character-profiles",
        json={"title": "沈照夜", "category": "character", "content": "主角", "payload": {"name": "沈照夜"}},
    )
    client.post(
        f"/api/projects/{project['id']}/outlines",
        json={
            "title": "第37章 灰塔回声大纲",
            "category": "chapter_outline",
            "content": "沈照夜在灰塔发现上一卷胜利留下的反噬证词。",
            "payload": {
                "chapter_number": "37",
                "chapter_title": "灰塔回声",
                "chapter_goal": "找到反噬证词",
            },
        },
    )

    response = client.post(
        f"/api/projects/{project['id']}/ai/generate_chapter_draft",
        json={"chapter_id": chapter["id"], "prompt": "写出本章正文，承接前文但推进新冲突。"},
    )

    assert response.status_code == 200
    text = response.json()["text"]
    assert "本地 MVP 的可编辑 AI 占位结果" not in text
    assert "第 37 章" in text or "第37章" in text
    assert "灰塔回声" in text
    assert "沈照夜" in text
    assert "反噬证词" in text
    assert len(text) > 500
    assert "。“" in text or "？”" in text or "！”" in text
    outline_like_phrases = [
        "本章目标",
        "这一章属于",
        "本章任务",
        "下一章",
        "任务记录",
        "从任务变成",
        "推进主线",
        "埋下将在",
        "开端建立",
    ]
    assert not any(phrase in text for phrase in outline_like_phrases)


def test_generation_context_recent_chapters_excludes_current_chapter(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "上下文连续性"}).json()
    client.post(
        f"/api/projects/{project['id']}/chapters",
        json={
            "chapter_number": 1,
            "title": "第1章 第一封信",
            "brief": "主角发现来信。",
            "summary": "主角发现写着明天日期的来信。",
        },
    )
    second = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={
            "chapter_number": 2,
            "title": "第2章 灰塔门禁",
            "brief": "主角进入灰塔。",
        },
    ).json()
    create_story_prerequisites(client, project["id"], 2, "灰塔门禁")

    response = client.post(
        f"/api/projects/{project['id']}/ai/generate_chapter_draft",
        json={"chapter_id": second["id"], "prompt": "写第二章"},
    )

    assert response.status_code == 200
    text = response.json()["text"]
    assert "上一章《第1章 第一封信》" in text
    assert "上一章《第2章 灰塔门禁》" not in text


def test_chapter_draft_requires_saved_characters_and_outline(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "顺序约束"}).json()
    chapter = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={"chapter_number": 1, "title": "第一章 雨夜"},
    ).json()

    missing_all = client.post(
        f"/api/projects/{project['id']}/ai/generate_chapter_draft",
        json={"chapter_id": chapter["id"], "prompt": "直接写正文"},
    )
    client.post(
        f"/api/projects/{project['id']}/character-profiles",
        json={"title": "沈照夜", "category": "character", "content": "主角", "payload": {"name": "沈照夜"}},
    )
    missing_outline = client.post(
        f"/api/projects/{project['id']}/ai/generate_chapter_draft",
        json={"chapter_id": chapter["id"], "prompt": "直接写正文"},
    )

    assert missing_all.status_code == 409
    assert "先生成并保存角色" in missing_all.json()["detail"]
    assert missing_outline.status_code == 409
    assert "再生成并保存大纲" in missing_outline.json()["detail"]


def test_story_generation_flow_uses_saved_outline_for_distinct_chapter_memory(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "真实链路"}).json()
    first = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={"chapter_number": 1, "title": "第1章 雨夜古籍"},
    ).json()
    second = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={"chapter_number": 2, "title": "第2章 灰塔证词"},
    ).json()

    character_ai = client.post(
        f"/api/projects/{project['id']}/ai/generate_characters",
        json={"prompt": "生成主角闻岚"},
    ).json()
    character_payload = character_ai["structured"]
    client.post(
        f"/api/projects/{project['id']}/character-profiles",
        json={
            "title": character_payload["name"],
            "category": "character",
            "content": character_payload["desire"],
            "payload": character_payload,
        },
    )

    outlines = []
    for chapter, clue in [(first, "雨夜古籍"), (second, "灰塔证词")]:
        outline_ai = client.post(
            f"/api/projects/{project['id']}/ai/generate_outline",
            json={"chapter_id": chapter["id"], "prompt": f"生成{clue}章节大纲"},
        ).json()
        outline_payload = outline_ai["structured"]
        outlines.append(outline_payload)
        client.post(
            f"/api/projects/{project['id']}/outlines",
            json={
                "title": outline_payload["chapter_title"],
                "category": "chapter_outline",
                "content": outline_payload["key_events"],
                "payload": outline_payload | {"chapter_number": str(chapter["chapter_number"])},
            },
        )

    assert outlines[0]["key_events"] != outlines[1]["key_events"]
    assert "雨夜古籍" in json.dumps(outlines[0], ensure_ascii=False)
    assert "灰塔证词" in json.dumps(outlines[1], ensure_ascii=False)

    drafts = []
    for chapter in [first, second]:
        draft_ai = client.post(
            f"/api/projects/{project['id']}/ai/generate_chapter_draft",
            json={"chapter_id": chapter["id"], "prompt": "一键生成本章正文"},
        ).json()
        drafts.append(draft_ai["text"])
        updated = client.patch(
            f"/api/projects/{project['id']}/chapters/{chapter['id']}",
            json={**chapter, "draft": draft_ai["text"]},
        ).json()
        assert updated["draft"] == draft_ai["text"]
        client.post(f"/api/projects/{project['id']}/chapters/{chapter['id']}/finalize")

    assert drafts[0] != drafts[1]
    assert "雨夜古籍" in drafts[0]
    assert "灰塔证词" in drafts[1]

    key_memory = client.get(f"/api/projects/{project['id']}/wiki/read", params={"path": "关键记忆.md"}).json()["content"]
    assert "雨夜古籍" in key_memory
    assert "灰塔证词" in key_memory
    first_section = key_memory.split("## 第 1 章", 1)[1].split("## 第 2 章", 1)[0]
    second_section = key_memory.split("## 第 2 章", 1)[1]
    assert first_section != second_section


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
    client.post(
        f"/api/projects/{project['id']}/outlines",
        json={
            "title": "第一章大纲",
            "category": "chapter_outline",
            "content": "雨夜发现古籍并付出记忆代价。",
            "payload": {"chapter_number": "1", "chapter_title": "第一章"},
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
    assert "quality_score" in finalized.json()
    scores = client.get(f"/api/projects/{project['id']}/chapters/{chapter['id']}/quality-scores")
    assert scores.status_code == 200
    assert len(scores.json()) == 1
    assert "metrics" in scores.json()[0]["payload"]
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


def test_finalized_chapters_rebuild_single_body_markdown_without_duplicate_sections(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "卷级记忆"}).json()
    first = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={
            "chapter_number": 1,
            "title": "第一章 旧书夜市",
            "brief": "发现古籍",
            "draft": "主角在旧书夜市发现无题古籍，并第一次付出记忆代价。",
            "summary": "主角发现无题古籍，确认改写会吞噬记忆。",
        },
    ).json()
    second = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={
            "chapter_number": 2,
            "title": "第二章 缺失的三分钟",
            "brief": "确认交易生效",
            "draft": "主角追查缺失的三分钟，发现借阅卡背面有警告。",
            "summary": "主角确认古籍交易已经生效，并发现借阅卡背面的警告。",
        },
    ).json()

    assert client.post(f"/api/projects/{project['id']}/chapters/{first['id']}/finalize").status_code == 200
    assert client.post(f"/api/projects/{project['id']}/chapters/{second['id']}/finalize").status_code == 200
    assert client.post(f"/api/projects/{project['id']}/chapters/{first['id']}/finalize").status_code == 200

    volume = client.get(f"/api/projects/{project['id']}/wiki/read", params={"path": "关键记忆.md"})
    body_page = client.get(f"/api/projects/{project['id']}/wiki/read", params={"path": "正文.md"})
    legacy_index = client.get(f"/api/projects/{project['id']}/wiki/read", params={"path": "chapters/index.md"})
    legacy_global = client.get(f"/api/projects/{project['id']}/wiki/read", params={"path": "global-summary.md"})

    assert volume.status_code == 200
    assert body_page.status_code == 404
    assert legacy_index.status_code == 404
    assert legacy_global.status_code == 404
    content = volume.json()["content"]
    assert "# 关键记忆" in content
    assert "## 第 1 章 · 第一章 旧书夜市" in content
    assert "## 第 2 章 · 第二章 缺失的三分钟" in content
    assert "吞噬记忆" in content
    assert "借阅卡背面的警告" in content
    assert content.count("## 第 1 章") == 1
    assert "不要重复" in content
    assert "推进主线" not in content


def test_remote_generation_prompt_includes_volume_memory_to_avoid_repetition(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "卷级上下文"}).json()
    first = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={
            "chapter_number": 1,
            "title": "第一章 旧书夜市",
            "draft": "主角发现无题古籍。",
            "summary": "主角发现无题古籍，确认改写会吞噬记忆。",
        },
    ).json()
    second = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={"chapter_number": 2, "title": "第二章 缺失的三分钟", "brief": "追查后果"},
    ).json()
    client.post(f"/api/projects/{project['id']}/chapters/{first['id']}/finalize")
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
        return FakeResponse()

    monkeypatch.setattr(main.urllib.request, "urlopen", fake_urlopen)

    response = client.post(
        f"/api/projects/{project['id']}/ai/generate_outline",
        json={"chapter_id": second["id"], "prompt": "生成第二章大纲"},
    )

    assert response.status_code == 200
    body = captured["body"]
    assert "关键记忆.md" in body
    assert "主角发现无题古籍" in body
    assert "避免重复本卷已发生事件" in body


def test_generation_context_lazily_rebuilds_missing_volume_memory(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "懒重建卷级记忆"}).json()
    first = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={
            "chapter_number": 1,
            "title": "第一章 旧书夜市",
            "draft": "主角发现无题古籍。",
            "summary": "主角发现无题古籍，确认改写会吞噬记忆。",
        },
    ).json()
    second = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={"chapter_number": 2, "title": "第二章 缺失的三分钟"},
    ).json()
    client.post(f"/api/projects/{project['id']}/chapters/{first['id']}/finalize")

    import backend.app.main as main

    create_story_prerequisites(client, project["id"], 2, "第二章 缺失的三分钟")
    main.delete_wiki_page(project["id"], "关键记忆.md")

    response = client.post(
        f"/api/projects/{project['id']}/ai/generate_chapter_draft",
        json={"chapter_id": second["id"], "prompt": "写第二章"},
    )
    volume = client.get(f"/api/projects/{project['id']}/wiki/read", params={"path": "关键记忆.md"})

    assert response.status_code == 200
    assert volume.status_code == 200
    assert "主角发现无题古籍" in response.json()["context"]["volume_memory"]["content"]


def test_generation_job_params_normalize_generation_modes(monkeypatch, tmp_path):
    make_client(monkeypatch, tmp_path)

    from backend.app.application.job_service import normalize_job_params

    fast = normalize_job_params({"generation_mode": "fast"})
    standard = normalize_job_params({})
    deep = normalize_job_params({"generation_mode": "deep"})
    merged = normalize_job_params({"generation_mode": "deep", "skip_steps": ["anti_ai"]})
    unknown = normalize_job_params({"generation_mode": "experimental"})

    assert fast["generation_mode"] == "fast"
    assert fast["skip_steps"] == ["anti_ai", "dialogue", "reader_pull"]
    assert standard["generation_mode"] == "standard"
    assert standard["skip_steps"] == ["anti_ai", "dialogue", "reader_pull"]
    assert deep["generation_mode"] == "deep"
    assert deep["skip_steps"] == []
    assert merged["skip_steps"] == ["anti_ai"]
    assert unknown["generation_mode"] == "standard"


def test_orchestrator_resume_detects_completed_required_steps_by_step_status(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "断点恢复"}).json()

    from backend.app.engine.orchestrator import Orchestrator
    from backend.app.infrastructure.database import create_job, create_step, update_step

    job = create_job(
        project["id"],
        {
            "start_chapter_number": 1,
            "target_chapter_count": 1,
            "checkpoint_strategy": "none",
            "auto_finalize": 1,
            "params": {},
        },
    )
    required_steps = ["brief", "seed", "draft", "archaeology", "deepen", "finalize"]
    for step_name in required_steps:
        step = create_step(job["id"], project["id"], "chapter-1", 1, step_name)
        update_step(step["id"], "completed", {"ok": True})

    assert Orchestrator(job["id"])._is_chapter_complete(1) is True

    incomplete_job = create_job(
        project["id"],
        {
            "start_chapter_number": 2,
            "target_chapter_count": 1,
            "checkpoint_strategy": "none",
            "auto_finalize": 1,
            "params": {},
        },
    )
    step = create_step(incomplete_job["id"], project["id"], "chapter-2", 2, "brief")
    update_step(step["id"], "completed", {"ok": True})

    assert Orchestrator(incomplete_job["id"])._is_chapter_complete(2) is False


def test_job_detail_derives_durable_progress_from_steps(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "进度派生"}).json()

    from backend.app.infrastructure.database import create_job, create_step, update_step

    job = create_job(
        project["id"],
        {
            "start_chapter_number": 1,
            "target_chapter_count": 2,
            "checkpoint_strategy": "none",
            "auto_finalize": 1,
            "params": {},
        },
    )
    for step_name in ["brief", "seed", "draft", "archaeology", "deepen", "finalize"]:
        step = create_step(job["id"], project["id"], "chapter-1", 1, step_name)
        update_step(step["id"], "completed", {"ok": True})
    failed = create_step(job["id"], project["id"], "chapter-2", 2, "draft")
    update_step(failed["id"], "failed", error="正文质量检查失败")

    detail = client.get(f"/api/projects/{project['id']}/jobs/{job['id']}").json()
    listing = client.get(f"/api/projects/{project['id']}/jobs").json()

    assert detail["completed_chapter_count"] == 1
    assert detail["progress_percent"] == 50
    assert detail["current_chapter_number"] == 2
    assert detail["failed_chapter_number"] == 2
    assert detail["failed_step"] == "draft"
    assert detail["last_step_error"] == "正文质量检查失败"
    assert listing[0]["completed_chapter_count"] == 1


def test_orchestrator_target_words_prefers_blueprint_then_project(monkeypatch, tmp_path):
    make_client(monkeypatch, tmp_path)

    from backend.app.engine.orchestrator import _target_words_for_job

    assert _target_words_for_job(
        {"generation_params": {"words_per_chapter": 1200}},
        {"target_words_per_chapter": 800},
    ) == 1200
    assert _target_words_for_job(
        {"generation_params": {}},
        {"target_words_per_chapter": 800},
    ) == 800
    assert _target_words_for_job(
        {"generation_params": {"words_per_chapter": "bad"}},
        {"target_words_per_chapter": 0},
    ) == 3000


def test_checkpoint_word_count_tolerance_defaults_to_autonomous_friendly_range():
    from backend.app.engine.checkpoint import CheckpointManager

    manager = CheckpointManager()
    assert manager._check_word_count({"target_words": 800, "draft": "字" * 1116}) == ""
    assert manager._check_word_count({"target_words": 800, "draft": "字" * 1400, "word_count_tolerance": 0.2})


def test_generation_job_uses_saved_remote_model_config_instead_of_stub(monkeypatch, tmp_path):
    import time

    client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={
            "title": "远程模型托管",
            "target_chapter_count": 1,
            "target_words_per_chapter": 120,
            "global_summary": "生成一章真正正文，不要使用本地占位。",
        },
    ).json()
    create_story_prerequisites(client, project["id"], 1, "第一章 雨夜名单")
    blueprint = client.post(
        f"/api/projects/{project['id']}/blueprints",
        json={
            "volume_number": 1,
            "volume_title": "第一卷",
            "volume_arc": "完成一次短闭环。",
            "chapter_range": {"start": 1, "end": 1},
            "generation_params": {"word_count_tolerance": 1.0},
        },
    ).json()
    client.post(f"/api/projects/{project['id']}/blueprints/{blueprint['id']}/approve")
    client.post(
        f"/api/projects/{project['id']}/model-configs",
        json={
            "title": "writer-model",
            "category": "OpenAI",
            "content": "default",
            "payload": {
                "api_key": "test-key",
                "base_url": "https://example.test/v1",
                "model_name": "writer-model",
                "is_default": True,
            },
        },
    )

    import backend.app.main as main

    calls: list[str] = []

    class FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": self.text}}]}).encode("utf-8")

    def fake_urlopen(request, timeout=0):
        body = json.loads(request.data.decode("utf-8"))
        content = body["messages"][1]["content"]
        workflow = content.split("工作流：", 1)[1].split("\n", 1)[0]
        calls.append(workflow)
        if workflow == "generate_chapter_brief":
            return FakeResponse(json.dumps({
                "chapter_title": "第一章 雨夜名单",
                "chapter_goal": "顾栖月发现失踪名单，并决定进入灰塔。",
                "main_conflict": "她必须在遗忘扩散前确认名单来源。",
            }, ensure_ascii=False))
        if workflow == "generate_emotion_seed":
            return FakeResponse(json.dumps({
                "emotion_seed": {
                    "core_tension": "想保存痛苦记忆，却害怕被痛苦吞没",
                    "scene_temperature": "雨夜、冷光、潮湿纸页",
                    "open_question": "名单为什么只剩她还记得？",
                }
            }, ensure_ascii=False))
        if workflow == "generate_chapter_draft":
            assert '"is_final_chapter": true' in content
            assert "不得写成未完待续" in content
            return FakeResponse(
                "远程正文标记：雨夜的名单贴在档案柜内侧，顾栖月读到自己的名字时没有立刻后退。"
                "她先把柜门合上一半，听见走廊尽头的脚步声从近处擦过去，像有人拖着一把没有影子的伞。"
                "钟楼在雾里敲了一声，街上的人同时忘记了刚才的雨，只有窗玻璃还保留着水痕。"
                "名单最后一栏写着灰塔归档，归档日期却是明天。顾栖月把纸页折进掌心，纸边割破了她的指腹，"
                "那一点疼反而让她安静下来。她没有再等巡夜人离开，而是取下钥匙，关灯，走向灰塔。"
                "如果整座城只剩她还记得这些名字，她就不能把记得也交出去。"
            )
        if workflow == "emotion_archaeology":
            return FakeResponse(json.dumps({
                "reader_felt_map": {"rupture_points": []},
                "subconscious_leads": [],
                "motif_echoes": {"existing_motifs": [], "new_seeds": []},
            }, ensure_ascii=False))
        if workflow == "deepen_and_bury":
            return FakeResponse(json.dumps({
                "revised_text": (
                    "远程正文标记：雨夜的名单贴在档案柜内侧，顾栖月读到自己的名字时没有后退。"
                    "她把柜门合上一半，听见巡夜人的脚步从门外擦过去，皮鞋踩过积水，却没有留下声音。"
                    "钟楼在雾里敲了一声，街上的人同时忘记了刚才的雨，只有窗玻璃还保留着密密的水痕。"
                    "名单最后一栏写着灰塔归档，日期却是明天。她把纸页折进掌心，纸边割破指腹，"
                    "疼痛让她终于确认自己还在这里。她取下钥匙，关灯，走向灰塔。"
                    "如果整座城只剩她还记得这些名字，她就不能把记得也交出去。"
                    "门在身后合上时，雨声忽然变小，像有人终于承认这份名单不是梦。"
                )
            }, ensure_ascii=False))
        if workflow == "summarize_and_bridge":
            return FakeResponse(json.dumps({
                "summary": "顾栖月发现失踪名单并决定去灰塔。",
                "ending_state": {
                    "time": "雨夜",
                    "location": "档案室门口",
                    "characters_present": "顾栖月",
                    "situation": "她握着名单准备出发",
                    "last_action": "她把名单折进掌心",
                },
                "open_hooks": [{"hook": "灰塔为何保存失踪名单", "urgency": "高"}],
                "emotional_residue": [{"character": "顾栖月", "emotion": "克制的恐惧", "intensity": 7}],
            }, ensure_ascii=False))
        return FakeResponse("{}")

    monkeypatch.setattr(main.urllib.request, "urlopen", fake_urlopen)

    job = client.post(
        f"/api/projects/{project['id']}/jobs",
        json={
            "blueprint_id": blueprint["id"],
            "start_chapter": 1,
            "count": 1,
            "checkpoint_strategy": "none",
            "auto_finalize": True,
            "params": {"generation_mode": "fast"},
        },
    ).json()
    for _ in range(80):
        current = client.get(f"/api/projects/{project['id']}/jobs/{job['id']}").json()
        if current["status"] in {"completed", "failed", "checkpoint", "aborted"}:
            break
        time.sleep(0.05)

    assert current["status"] == "completed"
    chapters = client.get(f"/api/projects/{project['id']}/chapters").json()
    assert len(chapters) == 1
    assert "远程正文标记" in chapters[0]["draft"]
    assert "（stub）" not in chapters[0]["draft"]
    assert calls.count("generate_emotion_seed") == 1

    from backend.app.infrastructure.database import connect, rows_to_dicts

    with connect() as conn:
        step_rows = rows_to_dicts(
            conn.execute(
                "SELECT step_name, step_output FROM chapter_generation_steps WHERE job_id = ?",
                (job["id"],),
            ).fetchall()
        )
    outputs = [json.loads(row["step_output"]) for row in step_rows if row.get("step_output")]
    assert outputs
    assert all(output.get("model") == "writer-model" for output in outputs)


def test_chapter_prose_quality_gate_rejects_outline_like_text():
    from backend.app.engine.quality import validate_chapter_prose

    outline_like = """
    本章目标：主角发现失踪名单。
    主要冲突：她必须进入灰塔。
    关键事件：
    1. 找到名单
    2. 与守夜人争执
    3. 结尾留下钩子
    写作建议：多描写雨夜氛围。
    """
    prose = (
        "雨声贴着灰塔外墙往上爬。顾栖月把名单摊在灯下，看见自己的名字夹在一串陌生人之间。"
        "她没有立刻喊人，只把纸角压平，像这样就能把心里的褶皱也压下去。门外有人停了一下，"
        "脚步声又慢慢远了。她知道再等下去，名单上的人会一个一个从城市里消失，而她会成为最后一个还记得的人。"
        "钟楼在雾里轻轻震了一下，没有钟声，只有玻璃柜里的旧钥匙跟着响。她伸手去拿钥匙，"
        "指尖碰到金属时才发现自己一直在发抖。不是害怕名单，而是害怕名单是真的。"
        "如果它是真的，那么她过去三个月修复的每一份档案，都可能只是替别人擦掉最后的痕迹。"
    )

    assert not validate_chapter_prose(outline_like).ok
    assert validate_chapter_prose(prose).ok


def test_chapter_quality_report_flags_final_open_hooks():
    from backend.app.engine.quality import build_chapter_quality_report

    draft = (
        "雨声贴着灰塔外墙往下落。顾栖月把最后一页档案放回铁柜，听见钟针重新向前挪了一格。"
        "她没有立刻离开，而是把那些被删去的名字重新抄在纸上。每写下一个名字，城里就有一扇窗亮起来，"
        "像有人终于记起回家的路。守夜人站在门口，没有再阻止她，只把旧钥匙放在桌角。"
        "她知道这些记忆不会让失去变轻，却能让失去有一个可以被承认的位置。天快亮时，灰塔的门开了，"
        "街道没有恢复成从前的样子，但人们开始彼此叫出名字。顾栖月把最后一页合上，走进清晨。"
    )
    report = build_chapter_quality_report(
        {"draft": draft},
        {"bridge_json": {"open_hooks": [{"hook": "灰塔深处还有另一本名单"}]}},
        is_final_chapter=True,
    )

    assert report["ok"] is False
    assert report["metrics"]["open_hook_count"] == 1
    assert "终章仍有未回收钩子" in "；".join(report["issues"])


def test_blueprint_approval_syncs_foreshadowing_registry(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "伏笔注册"}).json()
    blueprint = client.post(
        f"/api/projects/{project['id']}/blueprints",
        json={
            "volume_number": 1,
            "volume_title": "第一卷",
            "volume_arc": "从埋设白页到终章回收。",
            "chapter_range": {"start": 1, "end": 3},
            "key_foreshadowings": [
                {
                    "name": "白页名单",
                    "planted_in": "第 1 章",
                    "payoff_in": "第 3 章",
                    "description": "白页会在终章显示被删除者姓名。",
                }
            ],
        },
    ).json()

    approved = client.post(f"/api/projects/{project['id']}/blueprints/{blueprint['id']}/approve")

    assert approved.status_code == 200
    foreshadowings = client.get(f"/api/projects/{project['id']}/foreshadowings").json()
    assert len(foreshadowings) == 1
    payload = foreshadowings[0]["payload"]
    assert payload["name"] == "白页名单"
    assert payload["blueprint_id"] == blueprint["id"]
    assert payload["status"] == "计划回收"
    wiki = client.get(f"/api/projects/{project['id']}/wiki/read", params={"path": "foreshadowing.md"})
    assert wiki.status_code == 200
    assert "白页名单" in wiki.json()["content"]


def test_chapter_quality_report_flags_unresolved_blueprint_foreshadowings():
    from backend.app.engine.quality import build_chapter_quality_report

    draft = (
        "雨声贴着灰塔外墙往下落。顾栖月把最后一页档案放回铁柜，听见钟针重新向前挪了一格。"
        "她没有立刻离开，而是把那些被删去的名字重新抄在纸上。每写下一个名字，城里就有一扇窗亮起来，"
        "像有人终于记起回家的路。守夜人站在门口，没有再阻止她，只把旧钥匙放在桌角。"
        "她知道这些记忆不会让失去变轻，却能让失去有一个可以被承认的位置。天快亮时，灰塔的门开了，"
        "街道没有恢复成从前的样子，但人们开始彼此叫出名字。顾栖月把最后一页合上，走进清晨。"
    )
    report = build_chapter_quality_report(
        {"draft": draft},
        {"bridge_json": {"open_hooks": []}},
        is_final_chapter=True,
        foreshadowings=[
            {
                "title": "白页名单",
                "category": "blueprint_foreshadowing",
                "payload": {"name": "白页名单", "status": "计划回收", "source": "blueprint"},
            }
        ],
    )

    assert report["ok"] is False
    assert report["metrics"]["unresolved_foreshadowing_count"] == 1
    assert report["unresolved_foreshadowings"] == ["白页名单"]


def test_generation_job_fails_instead_of_persisting_outline_like_draft(monkeypatch, tmp_path):
    import time

    client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={"title": "坏正文拦截", "target_chapter_count": 1, "target_words_per_chapter": 500},
    ).json()
    create_story_prerequisites(client, project["id"], 1, "第一章 坏输出")
    blueprint = client.post(
        f"/api/projects/{project['id']}/blueprints",
        json={
            "volume_number": 1,
            "volume_title": "第一卷",
            "volume_arc": "测试质量门禁。",
            "chapter_range": {"start": 1, "end": 1},
            "generation_params": {"word_count_tolerance": 1.0},
        },
    ).json()
    client.post(f"/api/projects/{project['id']}/blueprints/{blueprint['id']}/approve")
    client.post(
        f"/api/projects/{project['id']}/model-configs",
        json={
            "title": "writer-model",
            "category": "OpenAI",
            "content": "default",
            "payload": {
                "api_key": "test-key",
                "base_url": "https://example.test/v1",
                "model_name": "writer-model",
                "is_default": True,
            },
        },
    )

    import backend.app.main as main

    class FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": self.text}}]}).encode("utf-8")

    def fake_urlopen(request, timeout=0):
        body = json.loads(request.data.decode("utf-8"))
        content = body["messages"][1]["content"]
        workflow = content.split("工作流：", 1)[1].split("\n", 1)[0]
        if workflow == "generate_chapter_brief":
            return FakeResponse(json.dumps({"chapter_title": "第一章 坏输出", "chapter_goal": "测试"}, ensure_ascii=False))
        if workflow == "generate_emotion_seed":
            return FakeResponse(json.dumps({"emotion_seed": {"core_tension": "测试", "scene_temperature": "冷雨", "open_question": "会失败吗？"}}, ensure_ascii=False))
        if workflow == "generate_chapter_draft":
            return FakeResponse(
                "本章目标：主角发现线索。\n主要冲突：她必须选择。\n关键事件：\n1. 找到线索\n2. 进入灰塔\n3. 留下钩子\n写作建议：增强氛围。"
            )
        return FakeResponse("{}")

    monkeypatch.setattr(main.urllib.request, "urlopen", fake_urlopen)

    job = client.post(
        f"/api/projects/{project['id']}/jobs",
        json={
            "blueprint_id": blueprint["id"],
            "start_chapter": 1,
            "count": 1,
            "checkpoint_strategy": "none",
            "auto_finalize": True,
            "params": {"generation_mode": "fast"},
        },
    ).json()
    for _ in range(80):
        current = client.get(f"/api/projects/{project['id']}/jobs/{job['id']}").json()
        if current["status"] in {"completed", "failed", "checkpoint", "aborted"}:
            break
        time.sleep(0.05)

    assert current["status"] == "failed"
    assert "正文质量检查失败" in current["error_message"]
    chapters = client.get(f"/api/projects/{project['id']}/chapters").json()
    assert len(chapters) == 1
    assert chapters[0]["draft"] == ""


def test_failed_generation_job_can_resume_from_failed_step(monkeypatch, tmp_path):
    import time

    client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={"title": "失败续跑", "target_chapter_count": 1, "target_words_per_chapter": 500},
    ).json()
    create_story_prerequisites(client, project["id"], 1, "第一章 续跑")
    blueprint = client.post(
        f"/api/projects/{project['id']}/blueprints",
        json={
            "volume_number": 1,
            "volume_title": "第一卷",
            "volume_arc": "测试失败续跑。",
            "chapter_range": {"start": 1, "end": 1},
            "generation_params": {"word_count_tolerance": 1.0},
        },
    ).json()
    client.post(f"/api/projects/{project['id']}/blueprints/{blueprint['id']}/approve")
    client.post(
        f"/api/projects/{project['id']}/model-configs",
        json={
            "title": "writer-model",
            "category": "OpenAI",
            "content": "default",
            "payload": {
                "api_key": "test-key",
                "base_url": "https://example.test/v1",
                "model_name": "writer-model",
                "is_default": True,
            },
        },
    )

    import backend.app.main as main

    calls: list[str] = []
    draft_attempts = {"count": 0}

    class FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": self.text}}]}).encode("utf-8")

    good_prose = (
        "雨声贴着灰塔外墙往上爬。顾栖月把名单摊在灯下，看见自己的名字夹在一串陌生人之间。"
        "她没有立刻喊人，只把纸角压平，像这样就能把心里的褶皱也压下去。门外有人停了一下，"
        "脚步声又慢慢远了。她知道再等下去，名单上的人会一个一个从城市里消失，而她会成为最后一个还记得的人。"
        "钟楼在雾里轻轻震了一下，没有钟声，只有玻璃柜里的旧钥匙跟着响。她伸手去拿钥匙，"
        "指尖碰到金属时才发现自己一直在发抖。不是害怕名单，而是害怕名单是真的。"
        "如果它是真的，那么她过去三个月修复的每一份档案，都可能只是替别人擦掉最后的痕迹。"
    )

    def fake_urlopen(request, timeout=0):
        body = json.loads(request.data.decode("utf-8"))
        content = body["messages"][1]["content"]
        workflow = content.split("工作流：", 1)[1].split("\n", 1)[0]
        calls.append(workflow)
        if workflow == "generate_chapter_brief":
            return FakeResponse(json.dumps({"chapter_title": "第一章 续跑", "chapter_goal": "发现名单"}, ensure_ascii=False))
        if workflow == "generate_emotion_seed":
            return FakeResponse(json.dumps({"emotion_seed": {"core_tension": "记得与遗忘", "scene_temperature": "雨夜", "open_question": "名单真假？"}}, ensure_ascii=False))
        if workflow == "generate_chapter_draft":
            draft_attempts["count"] += 1
            if draft_attempts["count"] == 1:
                return FakeResponse("本章目标：发现名单。\n主要冲突：确认真假。\n关键事件：\n1. 找到名单\n2. 走向灰塔")
            return FakeResponse(good_prose)
        if workflow == "emotion_archaeology":
            return FakeResponse(json.dumps({"reader_felt_map": {"rupture_points": []}}, ensure_ascii=False))
        if workflow == "deepen_and_bury":
            return FakeResponse(json.dumps({"revised_text": good_prose}, ensure_ascii=False))
        if workflow == "summarize_and_bridge":
            return FakeResponse(json.dumps({
                "summary": "顾栖月发现名单并确认必须记住被删除者。",
                "ending_state": {"time": "雨夜", "location": "灰塔门口", "last_action": "她握住旧钥匙"},
                "open_hooks": [],
            }, ensure_ascii=False))
        return FakeResponse("{}")

    monkeypatch.setattr(main.urllib.request, "urlopen", fake_urlopen)

    job = client.post(
        f"/api/projects/{project['id']}/jobs",
        json={
            "blueprint_id": blueprint["id"],
            "start_chapter": 1,
            "count": 1,
            "checkpoint_strategy": "none",
            "auto_finalize": True,
            "params": {"generation_mode": "fast"},
        },
    ).json()
    for _ in range(80):
        current = client.get(f"/api/projects/{project['id']}/jobs/{job['id']}").json()
        if current["status"] in {"completed", "failed", "checkpoint", "aborted"}:
            break
        time.sleep(0.05)

    assert current["status"] == "failed"
    assert client.post(f"/api/projects/{project['id']}/jobs/{job['id']}/resume").status_code == 200
    for _ in range(80):
        current = client.get(f"/api/projects/{project['id']}/jobs/{job['id']}").json()
        if current["status"] in {"completed", "failed", "checkpoint", "aborted"}:
            break
        time.sleep(0.05)

    assert current["status"] == "completed"
    assert calls.count("generate_chapter_brief") == 1
    assert calls.count("generate_emotion_seed") == 1
    assert draft_attempts["count"] == 2
    chapters = client.get(f"/api/projects/{project['id']}/chapters").json()
    assert chapters[0]["status"] == "final"
    assert "雨声贴着灰塔外墙" in chapters[0]["draft"]


def test_local_final_chapter_draft_closes_instead_of_adding_next_hook():
    from backend.app.domain.models import AiWorkflowIn
    from backend.app.workflows.generation import build_local_chapter_draft

    draft = build_local_chapter_draft(
        AiWorkflowIn(prompt="终章"),
        {
            "chapter": {"chapter_number": 15, "title": "第 15 章 明天之后", "brief": "终止记忆停摆"},
            "generation_contract": {"is_final_chapter": True, "ending_required": True},
        },
    )

    assert "故事到这里停住" in draft
    assert "她在等——等的不是天亮" not in draft
    assert "继续活下去" in draft


def test_pure_hosted_generation_can_finish_15_chapters_and_export_closed_story(monkeypatch, tmp_path):
    import time

    client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={
            "title": "十五章闭环烟测",
            "topic": "记忆停摆的城市",
            "genre": "都市奇幻悬疑",
            "target_chapter_count": 15,
            "target_words_per_chapter": 800,
            "synopsis": "顾栖月追查失忆名单，最终终止记忆停摆。",
            "global_summary": "第15章必须收束主要冲突，不得未完待续。",
        },
    ).json()
    client.post(
        f"/api/projects/{project['id']}/character-profiles",
        json={"title": "顾栖月", "category": "主角", "content": "档案修复员，必须保存痛苦记忆。", "payload": {"name": "顾栖月"}},
    )
    for chapter_number in range(1, 16):
        client.post(
            f"/api/projects/{project['id']}/outlines",
            json={
                "title": f"第 {chapter_number} 章大纲",
                "category": "chapter_outline",
                "content": f"第 {chapter_number} 章推进记忆停摆调查。",
                "payload": {
                    "chapter_number": str(chapter_number),
                    "chapter_title": f"第 {chapter_number} 章",
                    "chapter_goal": "终章收束主要冲突" if chapter_number == 15 else f"推进第 {chapter_number} 阶段线索",
                },
            },
        )
    blueprint = client.post(
        f"/api/projects/{project['id']}/blueprints",
        json={
            "volume_number": 1,
            "volume_title": "记忆停摆",
            "volume_arc": "从发现失踪名单，到终止城市记忆停摆。",
            "chapter_range": {"start": 1, "end": 15},
            "recurring_motifs": ["雨声", "停摆钟针", "白页"],
            "taboo_list": ["不要挑起现实政治立场对立", "不要写成未完待续"],
            "generation_params": {"ending_required": True, "word_count_tolerance": 1.0},
        },
    ).json()
    client.post(f"/api/projects/{project['id']}/blueprints/{blueprint['id']}/approve")

    job = client.post(
        f"/api/projects/{project['id']}/jobs",
        json={
            "blueprint_id": blueprint["id"],
            "start_chapter": 1,
            "count": 15,
            "checkpoint_strategy": "none",
            "auto_finalize": True,
            "params": {"hosting_mode": "pure", "generation_mode": "fast"},
        },
    ).json()
    for _ in range(300):
        current = client.get(f"/api/projects/{project['id']}/jobs/{job['id']}").json()
        if current["status"] in {"completed", "failed", "checkpoint", "aborted"}:
            break
        time.sleep(0.05)

    assert current["status"] == "completed"
    chapters = client.get(f"/api/projects/{project['id']}/chapters").json()
    assert len(chapters) == 15
    assert {chapter["status"] for chapter in chapters} == {"final"}
    assert all(chapter["word_count"] > 300 for chapter in chapters)
    assert all(chapter["quality_score"] >= 70 for chapter in chapters)
    final_draft = chapters[-1]["draft"]
    assert "故事到这里停住" in final_draft
    assert "她在等——等的不是天亮" not in final_draft

    exported = client.get(f"/api/projects/{project['id']}/export/markdown")
    assert exported.status_code == 200
    markdown = exported.text
    assert markdown.startswith("# 十五章闭环烟测")
    assert markdown.count("## 第 ") == 15
    assert "## 第 15 章" in markdown
    assert "故事到这里停住" in markdown
    assert "第 15 章 · 第 15 章" not in markdown

    manifest = client.get(f"/api/projects/{project['id']}/export/manifest")
    assert manifest.status_code == 200
    manifest_payload = manifest.json()
    assert manifest_payload["deliverable"] is True
    assert manifest_payload["chapter_count"] == 15
    assert manifest_payload["final_chapter_count"] == 15
    assert manifest_payload["missing_chapter_numbers"] == []
    assert manifest_payload["low_quality_chapters"] == []

    volume = client.get(f"/api/projects/{project['id']}/wiki/read", params={"path": "关键记忆.md"})
    assert volume.status_code == 200
    memory = volume.json()["content"]
    assert "## 第 15 章" in memory
    assert len(memory) < len(markdown)
    assert "故事到这里停住" not in memory

    from backend.app.infrastructure.database import connect, rows_to_dicts

    with connect() as conn:
        score_rows = rows_to_dicts(
            conn.execute(
                "SELECT * FROM chapter_scores WHERE project_id = ? ORDER BY created_at",
                (project["id"],),
            ).fetchall()
        )
    assert len(score_rows) == 15
    final_score_payload = score_rows[-1]["payload"]
    assert final_score_payload["metrics"]["is_final_chapter"] is True
    assert final_score_payload["metrics"]["open_hook_count"] == 0
    assert final_score_payload["ok"] is True
    score_endpoint = client.get(f"/api/projects/{project['id']}/chapters/{chapters[-1]['id']}/quality-scores")
    assert score_endpoint.status_code == 200
    assert score_endpoint.json()[0]["payload"]["metrics"]["is_final_chapter"] is True


def test_autopilot_prepares_bare_project_and_starts_hosted_generation(monkeypatch, tmp_path):
    import time

    client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={
            "title": "一键托管烟测",
            "topic": "记忆停摆的城市",
            "target_chapter_count": 3,
            "target_words_per_chapter": 600,
            "synopsis": "顾栖月追查失踪名单并在终章终止停摆。",
        },
    ).json()

    response = client.post(
        f"/api/projects/{project['id']}/jobs/autopilot",
        json={"count": 3, "generation_mode": "fast"},
    )
    assert response.status_code == 200
    payload = response.json()
    job = payload["job"]
    assert payload["prepared"]["characters"] >= 1
    assert payload["prepared"]["outlines"] >= 3
    assert payload["prepared"]["taboo_rules"] >= 2
    assert payload["blueprint"]["status"] == "active"

    for _ in range(120):
        current = client.get(f"/api/projects/{project['id']}/jobs/{job['id']}").json()
        if current["status"] in {"completed", "failed", "checkpoint", "aborted"}:
            break
        time.sleep(0.05)

    assert current["status"] == "completed"
    chapters = client.get(f"/api/projects/{project['id']}/chapters").json()
    assert len(chapters) == 3
    assert {chapter["status"] for chapter in chapters} == {"final"}
    assert "故事到这里停住" in chapters[-1]["draft"]


def test_generation_job_auto_exports_when_enabled(monkeypatch, tmp_path):
    import time
    from backend.app.engine.orchestrator import consume_events

    client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={
            "title": "自动导出烟测",
            "topic": "记忆停摆",
            "target_chapter_count": 2,
            "target_words_per_chapter": 500,
        },
    ).json()

    response = client.post(
        f"/api/projects/{project['id']}/jobs/autopilot",
        json={
            "count": 2,
            "generation_mode": "fast",
            "params": {"hosting_mode": "pure", "generation_mode": "fast", "auto_export": True},
        },
    )
    assert response.status_code == 200
    job = response.json()["job"]
    for _ in range(120):
        current = client.get(f"/api/projects/{project['id']}/jobs/{job['id']}").json()
        if current["status"] in {"completed", "failed", "checkpoint", "aborted"}:
            break
        time.sleep(0.05)

    assert current["status"] == "completed"
    export_dir = Path(project["project_root_path"]) / "exports"
    assert (export_dir / "novel.md").exists()
    assert (export_dir / "novel.txt").exists()
    assert (export_dir / "manifest.json").exists()
    manifest = json.loads((export_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["deliverable"] is True
    assert manifest["chapter_count"] == 2
    events = consume_events(job["id"], 0)
    auto_export_events = [event for event in events if event["type"] == "auto_export_completed"]
    assert auto_export_events
    assert auto_export_events[-1]["manifest"]["deliverable"] is True
