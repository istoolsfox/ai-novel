import importlib

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("AI_NOVEL_AUTOPILOT_RETRY_DELAY_SECONDS", "0")
    monkeypatch.setenv("AI_NOVEL_AUTOPILOT_SYNC", "1")

    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return main, TestClient(main.app)


def test_next_chapter_contract_uses_previous_bridge_and_knowledge(monkeypatch, tmp_path):
    main, client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={"title": "连续性测试", "target_chapter_count": 2},
    ).json()

    generated_prompts = []
    memory_count = 0

    def fake_ai_workflow(_project_id, workflow, payload):
        nonlocal memory_count
        if workflow == "generate_chapter_brief":
            chapter = client.get(
                f"/api/projects/{project['id']}/chapters/{payload.chapter_id}"
            ).json()
            number = chapter["chapter_number"]
            return {
                "workflow": workflow,
                "model": "fake-model",
                "text": "brief",
                "structured": {
                    "chapter_title": f"第 {number} 章 · 连续推进",
                    "chapter_goal": "继续追查地下档案馆",
                },
                "status": "success",
            }
        if workflow == "generate_chapter_draft":
            generated_prompts.append(payload.prompt)
            return {
                "workflow": workflow,
                "model": "fake-model",
                "text": "她捂住左肩，在旧城区医院地下出口继续躲避监察司，并向旧地铁站移动。",
                "structured": None,
                "status": "success",
            }
        if workflow == "check_consistency":
            return {
                "workflow": workflow,
                "model": "fake-model",
                "text": "check",
                "structured": {
                    "status": "pass",
                    "score": 95,
                    "issues": [],
                    "continuity_summary": "状态承接正常",
                },
                "status": "success",
            }
        if workflow == "extract_memory":
            memory_count += 1
            if memory_count == 1:
                structured = {
                    "summary": "沈照夜带伤离开医院地下出口。",
                    "ending_state": {
                        "time": "凌晨两点十五分",
                        "location": "旧城区医院地下出口",
                        "weather": "暴雨",
                        "current_action": "正在逃向旧地铁站",
                        "current_danger": "监察司仍在追捕",
                    },
                    "character_states": [
                        {
                            "character_id": "hero",
                            "character_name": "沈照夜",
                            "location": "旧城区医院地下出口",
                            "physical_state": "左肩受伤",
                            "emotional_state": "开始怀疑顾临舟",
                            "current_goal": "进入地下档案馆",
                            "alive_status": "alive",
                            "visibility_status": "public",
                        }
                    ],
                    "knowledge_changes": [
                        {
                            "character_id": "hero",
                            "character_name": "沈照夜",
                            "fact_key": "gu_route_source",
                            "fact_text": "顾临舟提前知道医院出口",
                            "knowledge_status": "suspected",
                            "confidence": 0.7,
                        }
                    ],
                    "relationship_changes": [],
                    "open_actions": ["继续逃离医院"],
                    "open_hooks": ["监察司为何提前知道出口"],
                    "emotional_residue": ["尚未公开质问顾临舟"],
                    "forbidden_repetition": ["不能再次第一次发现地下档案馆"],
                    "next_chapter_seeds": ["追逐继续"],
                }
            else:
                structured = {
                    "summary": "两人抵达旧地铁站。",
                    "ending_state": {
                        "time": "凌晨两点三十分",
                        "location": "旧地铁站入口",
                        "weather": "暴雨",
                        "current_action": "准备进入档案馆",
                        "current_danger": "追兵逼近",
                    },
                    "character_states": [],
                    "knowledge_changes": [],
                    "relationship_changes": [],
                    "open_actions": [],
                    "open_hooks": [],
                    "emotional_residue": [],
                    "forbidden_repetition": [],
                    "next_chapter_seeds": [],
                }
            return {
                "workflow": workflow,
                "model": "fake-model",
                "text": "memory",
                "structured": structured,
                "status": "success",
            }
        raise AssertionError(f"unexpected workflow: {workflow}")

    monkeypatch.setattr(main, "run_ai_workflow", fake_ai_workflow)

    response = client.post(
        f"/api/projects/{project['id']}/autopilot/start",
        json={"start_chapter": 1, "end_chapter": 2, "max_retries": 0},
    )

    assert response.status_code == 200
    assert response.json()["job"]["status"] == "completed"
    assert len(generated_prompts) == 2
    second_prompt = generated_prompts[1]
    assert "旧城区医院地下出口" in second_prompt
    assert "左肩受伤" in second_prompt
    assert "顾临舟提前知道医院出口" in second_prompt
    assert "尚未公开质问顾临舟" in second_prompt

    chapters = client.get(f"/api/projects/{project['id']}/chapters").json()
    first_chapter = chapters[0]
    second_chapter = chapters[1]

    bridge = client.get(
        f"/api/projects/{project['id']}/continuity/chapters/{first_chapter['id']}/bridge"
    )
    assert bridge.status_code == 200
    assert bridge.json()["payload"]["ending_state"]["location"] == "旧城区医院地下出口"

    contract = client.get(
        f"/api/projects/{project['id']}/continuity/chapters/{second_chapter['id']}/contract"
    )
    assert contract.status_code == 200
    assert contract.json()["payload"]["must_continue_from"]["current_action"] == "正在逃向旧地铁站"

    states = client.get(f"/api/projects/{project['id']}/continuity/character-states").json()
    assert any(item["physical_state"] == "左肩受伤" for item in states)

    knowledge = client.get(f"/api/projects/{project['id']}/continuity/character-knowledge").json()
    assert any(item["fact_key"] == "gu_route_source" for item in knowledge)


def test_high_risk_continuity_issue_is_repaired_and_rechecked(monkeypatch, tmp_path):
    main, client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={"title": "自动修复测试", "target_chapter_count": 1},
    ).json()

    check_calls = 0

    def fake_ai_workflow(_project_id, workflow, payload):
        nonlocal check_calls
        if workflow == "generate_chapter_brief":
            return {
                "workflow": workflow,
                "model": "fake-model",
                "text": "brief",
                "structured": {
                    "chapter_title": "第 1 章 · 错误知识",
                    "chapter_goal": "推进调查",
                },
                "status": "success",
            }
        if workflow == "generate_chapter_draft":
            return {
                "workflow": workflow,
                "model": "fake-model",
                "text": "沈照夜直接说出了她尚未得知的幕后名单。",
                "structured": None,
                "status": "success",
            }
        if workflow == "check_consistency":
            check_calls += 1
            if check_calls == 1:
                structured = {
                    "status": "fail",
                    "score": 35,
                    "issues": [
                        {
                            "type": "knowledge",
                            "severity": "high",
                            "description": "角色说出了尚未知晓的信息",
                            "evidence": "幕后名单",
                            "suggestion": "改为根据现场痕迹进行猜测",
                        }
                    ],
                    "continuity_summary": "存在知识越界",
                }
            else:
                structured = {
                    "status": "pass",
                    "score": 92,
                    "issues": [],
                    "continuity_summary": "知识边界已修复",
                }
            return {
                "workflow": workflow,
                "model": "fake-model",
                "text": "check",
                "structured": structured,
                "status": "success",
            }
        if workflow == "revise_selection":
            assert "知识" in payload.prompt or "knowledge" in payload.prompt
            return {
                "workflow": workflow,
                "model": "repair-model",
                "text": "沈照夜从现场痕迹中推测，幕后可能存在一份名单。",
                "structured": None,
                "status": "success",
            }
        if workflow == "extract_memory":
            return {
                "workflow": workflow,
                "model": "fake-model",
                "text": "memory",
                "structured": {
                    "summary": "沈照夜开始怀疑幕后名单存在。",
                    "ending_state": {
                        "time": "当夜",
                        "location": "档案室",
                        "weather": "",
                        "current_action": "继续调查",
                        "current_danger": "",
                    },
                    "character_states": [],
                    "knowledge_changes": [
                        {
                            "character_id": "hero",
                            "character_name": "沈照夜",
                            "fact_key": "hidden_list",
                            "fact_text": "幕后可能存在名单",
                            "knowledge_status": "suspected",
                            "confidence": 0.6,
                        }
                    ],
                    "relationship_changes": [],
                    "open_actions": [],
                    "open_hooks": ["名单是否真实存在"],
                    "emotional_residue": [],
                    "forbidden_repetition": [],
                    "next_chapter_seeds": [],
                },
                "status": "success",
            }
        raise AssertionError(f"unexpected workflow: {workflow}")

    monkeypatch.setattr(main, "run_ai_workflow", fake_ai_workflow)

    response = client.post(
        f"/api/projects/{project['id']}/autopilot/start",
        json={"start_chapter": 1, "end_chapter": 1, "max_retries": 0},
    )

    assert response.status_code == 200
    snapshot = response.json()
    assert snapshot["job"]["status"] == "completed"
    assert check_calls == 2

    chapter = client.get(f"/api/projects/{project['id']}/chapters").json()[0]
    assert chapter["status"] == "final"
    assert "推测" in chapter["draft"]
    assert "直接说出" not in chapter["draft"]

    versions = client.get(
        f"/api/projects/{project['id']}/chapters/{chapter['id']}/versions"
    ).json()
    assert len(versions) == 2
    assert any("连续性修复" in item["label"] for item in versions)

    checks = client.get(
        f"/api/projects/{project['id']}/continuity/chapters/{chapter['id']}/checks"
    ).json()
    assert {item["stage"] for item in checks} == {"initial", "recheck"}
    assert any(item["status"] == "pass" for item in checks)
