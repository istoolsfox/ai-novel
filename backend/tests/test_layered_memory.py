import importlib

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path, *, sync_worker: bool = True):
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("AI_NOVEL_AUTOPILOT_RETRY_DELAY_SECONDS", "0")
    if sync_worker:
        monkeypatch.setenv("AI_NOVEL_AUTOPILOT_SYNC", "1")
    else:
        monkeypatch.delenv("AI_NOVEL_AUTOPILOT_SYNC", raising=False)

    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return main, TestClient(main.app)


def test_layered_memory_flows_into_next_chapter_contract(monkeypatch, tmp_path):
    main, client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={"title": "分层记忆测试", "target_chapter_count": 2},
    ).json()
    chapter_two_contracts = []

    def fake_ai_workflow(project_id, workflow, payload):
        assert project_id == project["id"]
        chapter = main.require_chapter(project_id, payload.chapter_id)
        chapter_number = int(chapter["chapter_number"])

        if workflow == "generate_chapter_brief":
            return {
                "workflow": workflow,
                "model": "fake-model",
                "text": "brief",
                "structured": {
                    "chapter_title": f"第 {chapter_number} 章 · 测试",
                    "chapter_goal": "推进主线",
                },
                "status": "success",
            }

        if workflow == "generate_chapter_draft":
            if chapter_number == 2:
                chapter_two_contracts.append(payload.payload["chapter_contract"])
            return {
                "workflow": workflow,
                "model": "fake-model",
                "text": f"第 {chapter_number} 章正文。",
                "structured": None,
                "status": "success",
            }

        if workflow == "check_consistency":
            return {
                "workflow": workflow,
                "model": "fake-model",
                "text": '{"status":"pass","score":95,"issues":[],"continuity_summary":"通过"}',
                "structured": {
                    "status": "pass",
                    "score": 95,
                    "issues": [],
                    "continuity_summary": "通过",
                },
                "status": "success",
            }

        if workflow == "extract_memory":
            if chapter_number == 1:
                structured = {
                    "summary": "沈照夜在医院出口获得无主手机。",
                    "ending_state": {
                        "time": "凌晨两点",
                        "location": "医院地下出口",
                        "weather": "暴雨",
                        "current_action": "准备进入旧地铁",
                        "current_danger": "追兵接近",
                    },
                    "hard_facts": [
                        {
                            "fact_key": "phone_from_archive",
                            "fact_text": "无主手机来自旧档案馆。",
                            "fact_status": "confirmed",
                            "confidence": 0.9,
                        }
                    ],
                    "character_states": [],
                    "knowledge_changes": [],
                    "relationship_changes": [
                        {
                            "source_character_name": "沈照夜",
                            "target_character_name": "顾临舟",
                            "relation_type": "trust",
                            "value": 0.3,
                            "status": "active",
                            "reason": "暂时合作",
                        }
                    ],
                    "item_changes": [
                        {
                            "item_key": "unknown_phone",
                            "item_name": "无主手机",
                            "description": "来自旧档案馆",
                            "item_status": "active",
                            "change_type": "created",
                            "owner_type": "character",
                            "owner_name": "沈照夜",
                            "location": "医院地下出口",
                            "ownership_status": "held",
                        }
                    ],
                    "narrative_debt_changes": [
                        {
                            "debt_key": "who_left_phone",
                            "debt_type": "open_question",
                            "description": "谁留下了无主手机？",
                            "status": "open",
                            "priority": 0.8,
                            "deadline_chapter": 4,
                        }
                    ],
                    "foreshadowing_changes": [
                        {
                            "foreshadowing_key": "phone_crack",
                            "title": "手机屏幕裂纹",
                            "description": "裂纹形状与档案馆徽记一致。",
                            "status": "planted",
                            "setup_chapter": 1,
                            "payoff_chapter": 0,
                            "priority": 0.7,
                        }
                    ],
                    "open_actions": ["进入旧地铁"],
                    "open_hooks": ["谁留下手机"],
                    "emotional_residue": ["沈照夜仍不完全信任顾临舟"],
                    "forbidden_repetition": ["不要再次首次发现手机"],
                    "next_chapter_seeds": ["手机收到新的坐标"],
                }
            else:
                structured = {
                    "summary": "顾临舟承认手机由他留下。",
                    "ending_state": {
                        "time": "凌晨三点",
                        "location": "旧地铁站",
                        "weather": "暴雨",
                        "current_action": "查看手机坐标",
                        "current_danger": "",
                    },
                    "hard_facts": [
                        {
                            "fact_key": "phone_from_archive",
                            "fact_text": "无主手机由顾临舟从旧档案馆带出。",
                            "fact_status": "confirmed",
                            "confidence": 1.0,
                        }
                    ],
                    "character_states": [],
                    "knowledge_changes": [],
                    "relationship_changes": [
                        {
                            "source_character_name": "沈照夜",
                            "target_character_name": "顾临舟",
                            "relation_type": "trust",
                            "value": 0.6,
                            "status": "active",
                            "reason": "顾临舟坦白手机来源",
                        }
                    ],
                    "item_changes": [
                        {
                            "item_key": "unknown_phone",
                            "item_name": "无主手机",
                            "description": "来自旧档案馆",
                            "item_status": "active",
                            "change_type": "transferred",
                            "owner_type": "character",
                            "owner_name": "顾临舟",
                            "location": "旧地铁站",
                            "ownership_status": "held",
                        }
                    ],
                    "narrative_debt_changes": [
                        {
                            "debt_key": "who_left_phone",
                            "debt_type": "open_question",
                            "description": "谁留下了无主手机？",
                            "status": "resolved",
                            "priority": 0.8,
                            "deadline_chapter": 4,
                        }
                    ],
                    "foreshadowing_changes": [
                        {
                            "foreshadowing_key": "phone_crack",
                            "title": "手机屏幕裂纹",
                            "description": "裂纹对应档案馆徽记。",
                            "status": "paid_off",
                            "setup_chapter": 1,
                            "payoff_chapter": 2,
                            "priority": 0.7,
                        }
                    ],
                    "open_actions": [],
                    "open_hooks": [],
                    "emotional_residue": [],
                    "forbidden_repetition": ["不要再次追问手机来源"],
                    "next_chapter_seeds": ["追踪手机坐标"],
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
    assert len(response.json()["steps"]) == 16

    assert chapter_two_contracts
    contract = chapter_two_contracts[0]
    assert contract["hard_facts"][0]["fact_key"] == "phone_from_archive"
    assert contract["relationship_states"][0]["relation_type"] == "trust"
    assert contract["item_ownership"][0]["owner_name"] == "沈照夜"
    assert contract["narrative_debts"][0]["debt_key"] == "who_left_phone"
    assert contract["active_foreshadowings"][0]["foreshadowing_key"] == "phone_crack"

    facts = client.get(f"/api/projects/{project['id']}/memory/facts").json()
    assert facts[0]["source_chapter_number"] == 2
    assert "顾临舟" in facts[0]["fact_text"]

    relationships = client.get(f"/api/projects/{project['id']}/memory/relationships").json()
    assert relationships[0]["value"] == 0.6

    items = client.get(f"/api/projects/{project['id']}/memory/items").json()
    assert items[0]["owner_name"] == "顾临舟"

    assert client.get(
        f"/api/projects/{project['id']}/memory/debts",
        params={"open_only": True},
    ).json() == []
    assert client.get(
        f"/api/projects/{project['id']}/memory/foreshadowings",
        params={"active_only": True},
    ).json() == []

    compilations = client.get(f"/api/projects/{project['id']}/memory/compilations").json()
    assert len(compilations) == 2


def test_recompiling_same_chapter_replaces_derived_layers(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "重编译测试"}).json()
    chapter = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={"chapter_number": 1, "title": "第一章", "draft": "正文"},
    ).json()

    from backend.app.database import connect
    from backend.app.memory_compiler import persist_compiled_memory

    step = {
        "project_id": project["id"],
        "chapter_id": chapter["id"],
        "chapter_number": 1,
    }
    first = {
        "summary": "第一次",
        "ending_state": {},
        "character_states": [],
        "knowledge_changes": [],
        "hard_facts": [
            {
                "fact_key": "door_state",
                "fact_text": "门是关闭的。",
                "fact_status": "confirmed",
                "confidence": 0.8,
            }
        ],
        "relationship_changes": [],
        "item_changes": [],
        "narrative_debt_changes": [
            {
                "debt_key": "open_door",
                "debt_type": "unfinished_action",
                "description": "尚未打开门。",
                "status": "open",
                "priority": 0.5,
            }
        ],
        "foreshadowing_changes": [],
        "open_actions": [],
        "open_hooks": [],
        "emotional_residue": [],
        "forbidden_repetition": [],
        "next_chapter_seeds": [],
    }
    second = {
        **first,
        "summary": "第二次",
        "hard_facts": [
            {
                "fact_key": "door_state",
                "fact_text": "门已经打开。",
                "fact_status": "confirmed",
                "confidence": 1.0,
            }
        ],
        "narrative_debt_changes": [
            {
                "debt_key": "open_door",
                "debt_type": "unfinished_action",
                "description": "尚未打开门。",
                "status": "resolved",
                "priority": 0.5,
            }
        ],
    }

    with connect() as conn:
        persist_compiled_memory(conn, step, first, model="fake-model")
    with connect() as conn:
        persist_compiled_memory(conn, step, second, model="fake-model")

    with connect() as conn:
        compilation_count = conn.execute(
            "SELECT COUNT(*) FROM memory_compilations WHERE project_id = ? AND chapter_id = ?",
            (project["id"], chapter["id"]),
        ).fetchone()[0]
        fact_count = conn.execute(
            "SELECT COUNT(*) FROM story_facts WHERE project_id = ? AND source_chapter_id = ?",
            (project["id"], chapter["id"]),
        ).fetchone()[0]
        debt_count = conn.execute(
            "SELECT COUNT(*) FROM narrative_debts WHERE project_id = ? AND source_chapter_id = ?",
            (project["id"], chapter["id"]),
        ).fetchone()[0]

    assert compilation_count == 1
    assert fact_count == 1
    assert debt_count == 1
    assert client.get(f"/api/projects/{project['id']}/memory/facts").json()[0]["fact_text"] == "门已经打开。"
    assert client.get(f"/api/projects/{project['id']}/memory/debts").json()[0]["status"] == "resolved"
