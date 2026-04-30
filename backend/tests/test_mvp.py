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
