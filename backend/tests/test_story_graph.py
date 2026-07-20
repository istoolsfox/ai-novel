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


def base_memory(chapter_number: int) -> dict:
    return {
        "summary": f"第 {chapter_number} 章完成。",
        "ending_state": {
            "time": f"第 {chapter_number} 夜",
            "location": "旧档案馆",
            "weather": "雨",
            "current_action": "继续调查",
            "current_danger": "监察司接近",
        },
        "hard_facts": [],
        "character_states": [],
        "knowledge_changes": [],
        "relationship_changes": [],
        "item_changes": [],
        "narrative_debt_changes": [],
        "foreshadowing_changes": [],
        "open_actions": [],
        "open_hooks": [],
        "emotional_residue": [],
        "forbidden_repetition": [],
        "next_chapter_seeds": [],
    }


def test_story_graph_flows_into_next_chapter_contract(monkeypatch, tmp_path):
    main, client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={"title": "剧情图谱测试", "target_chapter_count": 2},
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
                    "chapter_title": f"第 {chapter_number} 章 · 图谱",
                    "chapter_goal": "推进档案馆主线",
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
                "text": "check",
                "structured": {
                    "status": "pass",
                    "score": 96,
                    "issues": [],
                    "continuity_summary": "通过",
                },
                "status": "success",
            }
        if workflow == "extract_memory":
            memory = base_memory(chapter_number)
            if chapter_number == 1:
                memory.update(
                    {
                        "story_thread_changes": [
                            {
                                "thread_key": "archive_main",
                                "title": "旧档案馆主线",
                                "thread_type": "main_plot",
                                "status": "active",
                                "priority": 1.0,
                                "current_stage": "获得入口线索",
                                "current_goal": "进入旧档案馆",
                                "next_target": "找到失踪名单",
                                "stall_tolerance": 2,
                            },
                            {
                                "thread_key": "trust_arc",
                                "title": "沈照夜与顾临舟的信任线",
                                "thread_type": "character_arc",
                                "status": "active",
                                "priority": 0.7,
                                "current_stage": "有限合作",
                                "current_goal": "判断顾临舟是否可信",
                                "next_target": "发现一次善意隐瞒",
                                "stall_tolerance": 3,
                            },
                        ],
                        "story_node_changes": [
                            {
                                "node_key": "find_archive_map",
                                "thread_key": "archive_main",
                                "node_type": "reveal",
                                "title": "发现档案馆地图",
                                "description": "手机中出现入口地图。",
                                "status": "completed",
                                "importance": 0.8,
                                "planned_chapter": 1,
                                "actual_chapter": 1,
                            },
                            {
                                "node_key": "enter_archive",
                                "thread_key": "archive_main",
                                "node_type": "goal",
                                "title": "进入旧档案馆",
                                "description": "通过旧地铁入口进入档案馆。",
                                "status": "planned",
                                "importance": 0.9,
                                "planned_chapter": 2,
                                "actual_chapter": 0,
                            },
                        ],
                        "story_edge_changes": [
                            {
                                "edge_key": "map_causes_entry",
                                "source_node_key": "find_archive_map",
                                "target_node_key": "enter_archive",
                                "relation_type": "causes",
                                "status": "active",
                                "weight": 0.9,
                            }
                        ],
                        "story_progress": [
                            {
                                "thread_key": "archive_main",
                                "progress_type": "advanced",
                                "progress_summary": "获得进入档案馆的地图。",
                                "before_stage": "寻找入口",
                                "after_stage": "获得入口线索",
                                "progress_score": 0.8,
                                "source_node_keys": ["find_archive_map"],
                            },
                            {
                                "thread_key": "trust_arc",
                                "progress_type": "introduced",
                                "progress_summary": "两人开始有限合作。",
                                "before_stage": "互不信任",
                                "after_stage": "有限合作",
                                "progress_score": 0.4,
                                "source_node_keys": [],
                            },
                        ],
                    }
                )
            else:
                memory.update(
                    {
                        "story_thread_changes": [
                            {
                                "thread_key": "archive_main",
                                "title": "旧档案馆主线",
                                "thread_type": "main_plot",
                                "status": "active",
                                "priority": 1.0,
                                "current_stage": "进入档案馆",
                                "current_goal": "找到失踪名单",
                                "next_target": "确认名单来源",
                                "stall_tolerance": 2,
                            }
                        ],
                        "story_node_changes": [
                            {
                                "node_key": "enter_archive",
                                "thread_key": "archive_main",
                                "node_type": "goal",
                                "title": "进入旧档案馆",
                                "description": "通过旧地铁入口进入档案馆。",
                                "status": "completed",
                                "importance": 0.9,
                                "planned_chapter": 2,
                                "actual_chapter": 2,
                            }
                        ],
                        "story_edge_changes": [],
                        "story_progress": [
                            {
                                "thread_key": "archive_main",
                                "progress_type": "advanced",
                                "progress_summary": "成功进入旧档案馆。",
                                "before_stage": "获得入口线索",
                                "after_stage": "进入档案馆",
                                "progress_score": 0.9,
                                "source_node_keys": ["enter_archive"],
                            }
                        ],
                    }
                )
            return {
                "workflow": workflow,
                "model": "fake-model",
                "text": "memory",
                "structured": memory,
                "status": "success",
            }
        raise AssertionError(f"unexpected workflow: {workflow}")

    monkeypatch.setattr(main, "run_ai_workflow", fake_ai_workflow)
    result = client.post(
        f"/api/projects/{project['id']}/autopilot/start",
        json={"start_chapter": 1, "end_chapter": 2, "max_retries": 0},
    )
    assert result.status_code == 200
    assert result.json()["job"]["status"] == "completed"
    assert len(result.json()["steps"]) == 16

    assert chapter_two_contracts
    contract = chapter_two_contracts[0]
    archive_thread = next(item for item in contract["story_threads"] if item["thread_key"] == "archive_main")
    assert archive_thread["current_stage"] == "获得入口线索"
    assert contract["story_focus"][0]["thread_key"] == "archive_main"
    assert any(item["node_key"] == "enter_archive" for item in contract["story_nodes"])
    assert contract["story_edges"][0]["relation_type"] == "causes"

    graph = client.get(f"/api/projects/{project['id']}/story-graph").json()
    assert graph["stats"]["thread_count"] == 2
    assert graph["stats"]["node_count"] == 2
    assert graph["stats"]["edge_count"] == 1
    current_main = next(item for item in graph["all_threads"] if item["thread_key"] == "archive_main")
    assert current_main["current_stage"] == "进入档案馆"

    chapters = client.get(f"/api/projects/{project['id']}/chapters").json()
    first_progress = client.get(
        f"/api/projects/{project['id']}/story-graph/chapters/{chapters[0]['id']}/progress"
    ).json()
    assert {item["thread_key"] for item in first_progress} == {"archive_main", "trust_arc"}


def test_story_graph_manual_focus_and_recompilation_are_stable(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "手动图谱测试"}).json()

    thread = client.post(
        f"/api/projects/{project['id']}/story-graph/threads",
        json={
            "thread_key": "mystery_line",
            "title": "失踪名单谜团",
            "thread_type": "mystery",
            "priority": 0.8,
            "current_stage": "尚未调查",
            "current_goal": "确认名单来源",
            "stall_tolerance": 1,
        },
    )
    assert thread.status_code == 200
    node = client.post(
        f"/api/projects/{project['id']}/story-graph/nodes",
        json={
            "node_key": "inspect_list",
            "thread_key": "mystery_line",
            "node_type": "goal",
            "title": "检查失踪名单",
            "status": "planned",
            "importance": 0.9,
        },
    )
    assert node.status_code == 200

    focus = client.get(
        f"/api/projects/{project['id']}/story-graph/focus",
        params={"chapter_number": 3},
    ).json()
    assert focus["story_focus"][0]["thread_key"] == "mystery_line"
    assert focus["stalled_threads"][0]["stalled"] is True

    chapter = client.post(
        f"/api/projects/{project['id']}/chapters",
        json={"chapter_number": 1, "title": "第一章", "draft": "正文"},
    ).json()
    from backend.app.database import connect
    from backend.app.memory_compiler import persist_compiled_memory

    step = {"project_id": project["id"], "chapter_id": chapter["id"], "chapter_number": 1}
    first = {
        **base_memory(1),
        "story_thread_changes": [
            {
                "thread_key": "mystery_line",
                "title": "失踪名单谜团",
                "thread_type": "mystery",
                "status": "active",
                "priority": 0.8,
                "current_stage": "发现名单",
                "current_goal": "确认名单来源",
                "next_target": "追查档案编号",
                "stall_tolerance": 1,
            }
        ],
        "story_node_changes": [
            {
                "node_key": "inspect_list",
                "thread_key": "mystery_line",
                "node_type": "goal",
                "title": "检查失踪名单",
                "status": "completed",
                "importance": 0.9,
                "actual_chapter": 1,
            }
        ],
        "story_edge_changes": [],
        "story_progress": [
            {
                "thread_key": "mystery_line",
                "progress_type": "advanced",
                "progress_summary": "发现名单中的异常编号。",
                "after_stage": "发现名单",
                "progress_score": 0.7,
                "source_node_keys": ["inspect_list"],
            }
        ],
    }
    second = {
        **first,
        "story_thread_changes": [
            {**first["story_thread_changes"][0], "current_stage": "锁定档案编号"}
        ],
        "story_node_changes": [
            {
                "node_key": "trace_archive_number",
                "thread_key": "mystery_line",
                "node_type": "goal",
                "title": "追查档案编号",
                "status": "active",
                "importance": 0.8,
            }
        ],
        "story_progress": [
            {
                "thread_key": "mystery_line",
                "progress_type": "advanced",
                "progress_summary": "锁定档案编号。",
                "after_stage": "锁定档案编号",
                "progress_score": 0.8,
                "source_node_keys": ["trace_archive_number"],
            }
        ],
    }

    with connect() as conn:
        persist_compiled_memory(conn, step, first, model="fake-model")
    with connect() as conn:
        persist_compiled_memory(conn, step, second, model="fake-model")

    with connect() as conn:
        compilation_count = conn.execute(
            "SELECT COUNT(*) FROM story_graph_compilations WHERE project_id = ? AND chapter_id = ?",
            (project["id"], chapter["id"]),
        ).fetchone()[0]
        state_count = conn.execute(
            "SELECT COUNT(*) FROM story_thread_states WHERE project_id = ? AND source_chapter_id = ?",
            (project["id"], chapter["id"]),
        ).fetchone()[0]
        generated_node_count = conn.execute(
            "SELECT COUNT(*) FROM story_node_states WHERE project_id = ? AND source_chapter_id = ?",
            (project["id"], chapter["id"]),
        ).fetchone()[0]
        progress_count = conn.execute(
            "SELECT COUNT(*) FROM chapter_story_progress WHERE project_id = ? AND chapter_id = ?",
            (project["id"], chapter["id"]),
        ).fetchone()[0]

    assert compilation_count == 1
    assert state_count == 1
    assert generated_node_count == 1
    assert progress_count == 1
    threads = client.get(f"/api/projects/{project['id']}/story-graph/threads").json()
    assert threads[0]["current_stage"] == "锁定档案编号"
    nodes = client.get(f"/api/projects/{project['id']}/story-graph/nodes").json()
    assert {item["node_key"] for item in nodes} == {"inspect_list", "trace_archive_number"}
    generated = next(item for item in nodes if item["node_key"] == "trace_archive_number")
    assert generated["status"] == "active"
