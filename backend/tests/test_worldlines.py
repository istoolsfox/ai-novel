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
    return TestClient(main.app)


def memory(number, stage, fact, completed, following):
    nodes = [{
        "node_key": completed, "thread_key": "archive_main", "node_type": "event",
        "title": completed, "description": fact, "status": "completed",
        "importance": .9, "planned_chapter": number, "actual_chapter": number,
    }]
    edges = []
    if following:
        nodes.append({
            "node_key": following, "thread_key": "archive_main", "node_type": "goal",
            "title": following, "description": following, "status": "planned",
            "importance": .8, "planned_chapter": number + 1, "actual_chapter": 0,
        })
        edges.append({
            "edge_key": f"{completed}_causes_{following}", "source_node_key": completed,
            "target_node_key": following, "relation_type": "causes", "status": "active", "weight": .9,
        })
    return {
        "summary": fact,
        "ending_state": {"time": f"第{number}夜", "location": "旧档案馆", "current_action": stage},
        "hard_facts": [{"fact_key": "archive_truth", "fact_text": fact, "fact_status": "confirmed", "confidence": 1}],
        "character_states": [{
            "character_id": "hero", "character_name": "沈照夜", "location": "旧档案馆",
            "physical_state": "左肩受伤", "emotional_state": stage,
            "current_goal": following or "确认真相", "alive_status": "alive", "visibility_status": "public",
        }],
        "knowledge_changes": [], "relationship_changes": [], "item_changes": [],
        "narrative_debt_changes": [{
            "debt_key": "archive_owner", "debt_type": "open_question",
            "description": "谁控制旧档案馆？", "status": "resolved" if number >= 3 else "open",
            "priority": .8, "deadline_chapter": 3,
        }],
        "foreshadowing_changes": [],
        "story_thread_changes": [{
            "thread_key": "archive_main", "title": "旧档案馆主线", "thread_type": "main_plot",
            "status": "active", "priority": 1, "current_stage": stage,
            "current_goal": following or "确认真相", "next_target": following, "stall_tolerance": 2,
        }],
        "story_node_changes": nodes, "story_edge_changes": edges,
        "story_progress": [{
            "thread_key": "archive_main", "progress_type": "advanced",
            "progress_summary": stage, "after_stage": stage, "progress_score": .9,
            "source_node_keys": [completed],
        }],
        "open_actions": [], "open_hooks": [], "emotional_residue": [],
        "forbidden_repetition": [], "next_chapter_seeds": [following] if following else [],
    }


def persist_state(project_id, chapter, payload):
    from backend.app.database import connect
    from backend.app.impact_engine import analyze_story_impact, persist_impact_analysis
    from backend.app.memory_compiler import persist_compiled_memory
    from backend.app.rolling_planner import build_rolling_plan_proposal, persist_rolling_plan
    step = {"project_id": project_id, "chapter_id": chapter["id"], "chapter_number": chapter["chapter_number"]}
    with connect() as conn:
        persist_compiled_memory(conn, step, payload, model="fake-model")
    analysis = analyze_story_impact(project_id, chapter["id"], chapter["chapter_number"])
    with connect() as conn:
        persist_impact_analysis(conn, analysis)
    proposal = build_rolling_plan_proposal(project_id, chapter["id"], chapter["chapter_number"], window_size=3)
    with connect() as conn:
        persist_rolling_plan(conn, proposal)


def add_chapter(client, project_id, number, stage, fact, completed, following, *, prefix="主世界线"):
    chapter = client.post(f"/api/projects/{project_id}/chapters", json={
        "chapter_number": number, "title": f"第 {number} 章", "draft": f"{prefix}第 {number} 章：{stage}",
        "summary": fact, "status": "final",
    }).json()
    client.post(f"/api/projects/{project_id}/chapters/{chapter['id']}/versions", json={
        "label": f"版本 {number}", "content": chapter["draft"], "model": "fake",
    })
    persist_state(project_id, chapter, memory(number, stage, fact, completed, following))
    return chapter


def test_worldline_fork_restores_fork_state_and_isolates_layers(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "世界线测试", "target_chapter_count": 6}).json()
    chapters = [
        add_chapter(client, project["id"], 1, "发现地图", "入口地图被发现。", "find_map", "enter_archive"),
        add_chapter(client, project["id"], 2, "进入档案馆", "主角已经进入旧档案馆。", "enter_archive", "find_list"),
        add_chapter(client, project["id"], 3, "找到名单", "失踪名单来自监察司。", "find_list", "confirm_owner"),
    ]
    branch = client.post(f"/api/projects/{project['id']}/worldlines/fork", json={
        "name": "拒绝进入档案馆", "fork_chapter_number": 2,
    })
    assert branch.status_code == 200
    branch = branch.json()
    branch_project = branch["project_id"]

    assert [row["chapter_number"] for row in client.get(f"/api/projects/{branch_project}/chapters").json()] == [1, 2]
    assert client.get(f"/api/projects/{branch_project}/memory/facts").json()[0]["fact_text"] == "主角已经进入旧档案馆。"
    graph = client.get(f"/api/projects/{branch_project}/story-graph").json()
    assert next(row for row in graph["all_threads"] if row["thread_key"] == "archive_main")["current_stage"] == "进入档案馆"
    assert {row["chapter_number"] for row in client.get(f"/api/projects/{branch_project}/impact/runs").json()} == {1, 2}
    assert client.get(f"/api/projects/{branch_project}/planning/current").json()

    branch_chapter_two = client.get(f"/api/projects/{branch_project}/chapters").json()[1]
    assert len(client.get(f"/api/projects/{branch_project}/chapters/{branch_chapter_two['id']}/versions").json()) == 1

    alternate = add_chapter(
        client, branch_project, 3, "转向地面调查",
        "主角拒绝深入档案馆，监察司名单尚未发现。",
        "reject_archive", "surface_investigation", prefix="分支世界线",
    )
    source_three = client.get(f"/api/projects/{project['id']}/chapters/{chapters[2]['id']}").json()
    assert "主世界线" in source_three["draft"] and "拒绝深入" not in source_three["draft"]
    assert client.get(f"/api/projects/{project['id']}/memory/facts").json()[0]["fact_text"] == "失踪名单来自监察司。"
    assert "尚未发现" in client.get(f"/api/projects/{branch_project}/memory/facts").json()[0]["fact_text"]

    branch_plan = client.get(f"/api/projects/{branch_project}/planning/current").json()
    lock_number = next(row["chapter_number"] for row in branch_plan if row["chapter_number"] > alternate["chapter_number"])
    assert client.post(f"/api/projects/{branch_project}/planning/chapters/{lock_number}/lock", json={"locked": True}).json()["locked"] is True
    source_plan = client.get(f"/api/projects/{project['id']}/planning/chapters/{lock_number}")
    if source_plan.status_code == 200:
        assert source_plan.json()["locked"] is False

    family = client.get(f"/api/projects/{project['id']}/worldlines").json()
    main = next(row for row in family["worldlines"] if row["project_id"] == project["id"])
    comparison = client.get(f"/api/projects/{project['id']}/worldlines/compare/{main['id']}/{branch['id']}").json()
    assert comparison["shared_prefix_chapter"] == 2
    assert comparison["chapter_differences"][0]["chapter_number"] == 3
    assert "archive_truth" in comparison["memory_facts"]["changed"]
    assert "archive_main" in comparison["story_threads"]["changed"]


def test_worldline_activation_promotion_and_archive_rules(monkeypatch, tmp_path):
    client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "世界线控制", "target_chapter_count": 3}).json()
    client.post(f"/api/projects/{project['id']}/chapters", json={
        "chapter_number": 1, "title": "第一章", "draft": "正文", "status": "final",
    })
    first = client.post(f"/api/projects/{project['id']}/worldlines/fork", json={
        "name": "第一分支", "fork_chapter_number": 1,
    }).json()
    second = client.post(f"/api/projects/{project['id']}/worldlines/fork", json={
        "name": "第二分支", "fork_chapter_number": 1,
    }).json()

    assert client.post(f"/api/projects/{project['id']}/worldlines/{first['id']}/activate").json()["is_active"] is True
    promoted = client.post(f"/api/projects/{project['id']}/worldlines/{first['id']}/promote").json()
    assert promoted["is_primary"] is True and promoted["is_active"] is True
    assert client.post(f"/api/projects/{project['id']}/worldlines/{first['id']}/archive").status_code == 409
    assert client.post(f"/api/projects/{project['id']}/worldlines/{second['id']}/archive").json()["status"] == "archived"

    family = client.get(f"/api/projects/{project['id']}/worldlines").json()
    assert family["active_worldline_id"] == first["id"]
    assert family["primary_worldline_id"] == first["id"]
    assert family["isolation_model"] == "project_backed"
    assert any(event["event_type"] == "worldline.promoted" for event in family["events"])
