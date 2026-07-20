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


def memory(number):
    return {
        "summary": f"第 {number} 章完成。",
        "ending_state": {"time": f"第 {number} 夜", "location": "旧档案馆", "weather": "雨", "current_action": "继续调查", "current_danger": "监察司接近"},
        "hard_facts": [], "character_states": [], "knowledge_changes": [],
        "relationship_changes": [], "item_changes": [], "narrative_debt_changes": [],
        "foreshadowing_changes": [], "story_thread_changes": [], "story_node_changes": [],
        "story_edge_changes": [], "story_progress": [], "open_actions": [], "open_hooks": [],
        "emotional_residue": [], "forbidden_repetition": [], "next_chapter_seeds": [],
    }


def seed_graph(client, project_id):
    assert client.post(f"/api/projects/{project_id}/story-graph/threads", json={
        "thread_key": "archive_main", "title": "旧档案馆主线", "thread_type": "main_plot",
        "status": "active", "priority": 1.0, "current_goal": "进入旧档案馆",
        "next_target": "找到失踪名单", "stall_tolerance": 2,
    }).status_code == 200
    for node in (
        {"node_key": "find_map", "thread_key": "archive_main", "node_type": "reveal", "title": "发现入口地图", "status": "active", "importance": .9, "planned_chapter": 1},
        {"node_key": "enter_archive", "thread_key": "archive_main", "node_type": "goal", "title": "进入旧档案馆", "status": "planned", "importance": .95, "planned_chapter": 2},
        {"node_key": "find_missing_list", "thread_key": "archive_main", "node_type": "reveal", "title": "找到失踪名单", "status": "planned", "importance": .85, "planned_chapter": 3},
    ):
        assert client.post(f"/api/projects/{project_id}/story-graph/nodes", json=node).status_code == 200
    for edge in (
        {"edge_key": "map_causes_entry", "source_node_key": "find_map", "target_node_key": "enter_archive", "relation_type": "causes", "status": "active", "weight": .9},
        {"edge_key": "entry_reveals_list", "source_node_key": "enter_archive", "target_node_key": "find_missing_list", "relation_type": "reveals", "status": "active", "weight": .85},
    ):
        assert client.post(f"/api/projects/{project_id}/story-graph/edges", json=edge).status_code == 200


def test_impact_and_plan_flow_into_next_chapter(monkeypatch, tmp_path):
    main, client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "影响传播测试", "target_chapter_count": 3}).json()
    seed_graph(client, project["id"])
    brief_plans, contracts = [], []

    def fake_ai(project_id, workflow, payload):
        chapter = main.require_chapter(project_id, payload.chapter_id)
        number = int(chapter["chapter_number"])
        if workflow == "generate_chapter_brief":
            if number == 2: brief_plans.append(payload.payload.get("rolling_plan"))
            return {"workflow": workflow, "model": "fake", "text": "brief", "structured": {"chapter_title": f"第 {number} 章", "chapter_goal": "推进主线"}, "status": "success"}
        if workflow == "generate_chapter_draft":
            if number == 2: contracts.append(payload.payload["chapter_contract"])
            return {"workflow": workflow, "model": "fake", "text": f"第 {number} 章正文。", "structured": None, "status": "success"}
        if workflow == "check_consistency":
            return {"workflow": workflow, "model": "fake", "text": "check", "structured": {"status": "pass", "score": 96, "issues": [], "continuity_summary": "通过"}, "status": "success"}
        if workflow == "extract_memory":
            result = memory(number)
            if number == 1:
                result["narrative_debt_changes"] = [{"debt_key": "map_source", "debt_type": "open_question", "description": "入口地图是谁留下的？", "status": "open", "priority": .8, "deadline_chapter": 1}]
                result["story_node_changes"] = [{"node_key": "find_map", "thread_key": "archive_main", "node_type": "reveal", "title": "发现入口地图", "status": "completed", "importance": .9, "actual_chapter": 1}]
                result["story_progress"] = [{"thread_key": "archive_main", "progress_type": "advanced", "progress_summary": "获得入口地图。", "progress_score": .9, "source_node_keys": ["find_map"]}]
            else:
                result["story_node_changes"] = [{"node_key": "enter_archive", "thread_key": "archive_main", "node_type": "goal", "title": "进入旧档案馆", "status": "completed", "importance": .95, "actual_chapter": 2}]
                result["story_progress"] = [{"thread_key": "archive_main", "progress_type": "advanced", "progress_summary": "进入旧档案馆。", "progress_score": .9, "source_node_keys": ["enter_archive"]}]
            return {"workflow": workflow, "model": "fake", "text": "memory", "structured": result, "status": "success"}
        raise AssertionError(workflow)

    monkeypatch.setattr(main, "run_ai_workflow", fake_ai)
    run = client.post(f"/api/projects/{project['id']}/autopilot/start", json={"start_chapter": 1, "end_chapter": 2, "max_retries": 0})
    assert run.status_code == 200 and run.json()["job"]["status"] == "completed"
    assert len(run.json()["steps"]) == 16
    plan = brief_plans[0]
    assert plan["primary_thread_key"] == "archive_main"
    assert "enter_archive" in plan["target_node_keys"]
    assert any("入口地图是谁留下" in item for item in plan["must_address"])
    assert contracts[0]["rolling_plan"]["chapter_number"] == 2

    chapter_one = next(row for row in client.get(f"/api/projects/{project['id']}/chapters").json() if row["chapter_number"] == 1)
    impact = client.get(f"/api/projects/{project['id']}/impact/chapters/{chapter_one['id']}").json()
    targets = {row["target_key"]: row for row in impact["targets"]}
    assert targets["enter_archive"]["depth"] == 1
    assert targets["find_missing_list"]["depth"] == 2
    assert targets["enter_archive"]["impact_score"] > targets["find_missing_list"]["impact_score"]
    assert any(row["observation_type"] == "narrative_debt_overdue" for row in impact["observations"])
    assert client.get(f"/api/projects/{project['id']}/planning/chapters/2").status_code == 200


def test_replanning_preserves_lock_and_is_idempotent(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "重排测试", "target_chapter_count": 6}).json()
    chapter = client.post(f"/api/projects/{project['id']}/chapters", json={"chapter_number": 1, "title": "第一章", "draft": "正文"}).json()
    for key, title in (("line_a", "A 线"), ("line_b", "B 线")):
        assert client.post(f"/api/projects/{project['id']}/story-graph/threads", json={"thread_key": key, "title": title, "thread_type": "subplot", "status": "active", "priority": .6, "current_goal": f"推进{title}", "stall_tolerance": 3}).status_code == 200
        assert client.post(f"/api/projects/{project['id']}/story-graph/nodes", json={"node_key": f"node_{key[-1]}", "thread_key": key, "node_type": "goal", "title": f"完成{title}目标", "status": "planned", "importance": .8}).status_code == 200

    def analyze(node):
        return client.post(f"/api/projects/{project['id']}/impact/analyze", json={"chapter_id": chapter["id"], "chapter_number": 1, "events": [{"subject_type": "node", "subject_key": node, "magnitude": 1.0}]})

    def reconcile():
        return client.post(f"/api/projects/{project['id']}/planning/reconcile", json={"source_chapter_id": chapter["id"], "source_chapter_number": 1, "window_size": 5})

    assert analyze("node_a").status_code == 200 and reconcile().status_code == 200
    before_two = client.get(f"/api/projects/{project['id']}/planning/chapters/2").json()
    before_three = client.get(f"/api/projects/{project['id']}/planning/chapters/3").json()
    assert before_two["primary_thread_key"] == "line_a" and before_three["primary_thread_key"] == "line_b"
    assert client.post(f"/api/projects/{project['id']}/planning/chapters/2/lock", json={"locked": True}).json()["locked"] is True

    assert analyze("node_b").status_code == 200 and reconcile().status_code == 200
    after_two = client.get(f"/api/projects/{project['id']}/planning/chapters/2").json()
    after_three = client.get(f"/api/projects/{project['id']}/planning/chapters/3").json()
    assert after_two["primary_thread_key"] == before_two["primary_thread_key"] and after_two["locked"] is True
    assert after_three["primary_thread_key"] != before_three["primary_thread_key"]
    history_before = client.get(f"/api/projects/{project['id']}/planning/history", params={"chapter_number": 3}).json()
    assert {row["action"] for row in history_before} == {"created", "replanned"}
    assert reconcile().status_code == 200
    history_after = client.get(f"/api/projects/{project['id']}/planning/history", params={"chapter_number": 3}).json()
    assert len(history_after) == len(history_before)

    from backend.app.database import connect
    with connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM impact_runs WHERE project_id = ? AND chapter_id = ?", (project["id"], chapter["id"])).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM rolling_plan_snapshots WHERE project_id = ? AND source_chapter_id = ?", (project["id"], chapter["id"])).fetchone()[0] == 1
