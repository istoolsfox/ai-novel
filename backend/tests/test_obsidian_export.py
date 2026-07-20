import importlib
import io
import json
import zipfile
from pathlib import Path

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


def memory_payload(number: int, fact_text: str, *, stage: str = "发现入口") -> dict:
    return {
        "summary": fact_text,
        "ending_state": {
            "time": f"第 {number} 夜",
            "location": "旧档案馆",
            "weather": "暴雨",
            "current_action": stage,
            "current_danger": "监察司接近",
        },
        "hard_facts": [{"fact_key": "archive_truth", "fact_text": fact_text, "fact_status": "confirmed", "confidence": 1}],
        "character_states": [{
            "character_id": "hero", "character_name": "沈照夜", "location": "旧档案馆",
            "physical_state": "左肩受伤", "emotional_state": "警惕",
            "current_goal": "查明名单来源", "alive_status": "alive", "visibility_status": "public",
        }],
        "knowledge_changes": [{
            "character_id": "hero", "character_name": "沈照夜", "fact_key": "archive_truth",
            "fact_text": fact_text, "knowledge_status": "confirmed", "confidence": 1,
        }],
        "relationship_changes": [{
            "source_character_name": "沈照夜", "target_character_name": "顾临舟",
            "relation_type": "trust", "value": 0.4, "status": "active", "reason": "暂时合作",
        }],
        "item_changes": [{
            "item_key": "archive_phone", "item_name": "档案馆手机",
            "description": "手机中保存着入口地图。", "item_status": "active", "change_type": "created",
            "owner_type": "character", "owner_name": "沈照夜", "location": "旧档案馆", "ownership_status": "held",
        }],
        "narrative_debt_changes": [{
            "debt_key": "phone_owner", "debt_type": "open_question",
            "description": "谁留下了档案馆手机？", "status": "open", "priority": 0.8, "deadline_chapter": 3,
        }],
        "foreshadowing_changes": [{
            "foreshadowing_key": "phone_crack", "title": "手机裂纹",
            "description": "裂纹与监察司徽记一致。", "status": "planted",
            "setup_chapter": number, "payoff_chapter": 3, "priority": 0.8,
        }],
        "story_thread_changes": [{
            "thread_key": "archive_main", "title": "旧档案馆主线", "thread_type": "main_plot",
            "status": "active", "priority": 1, "current_stage": stage,
            "current_goal": "找到失踪名单", "next_target": "进入深层档案室", "stall_tolerance": 2,
        }],
        "story_node_changes": [
            {
                "node_key": f"chapter_{number}_event", "thread_key": "archive_main", "node_type": "reveal",
                "title": f"第 {number} 章关键发现", "description": fact_text, "status": "completed",
                "importance": 0.9, "planned_chapter": number, "actual_chapter": number,
            },
            {
                "node_key": "enter_deep_archive", "thread_key": "archive_main", "node_type": "goal",
                "title": "进入深层档案室", "description": "进入档案馆最深处。", "status": "planned",
                "importance": 0.8, "planned_chapter": number + 1, "actual_chapter": 0,
            },
        ],
        "story_edge_changes": [{
            "edge_key": f"chapter_{number}_causes_deep_archive", "source_node_key": f"chapter_{number}_event",
            "target_node_key": "enter_deep_archive", "relation_type": "causes", "status": "active", "weight": 0.9,
        }],
        "story_progress": [{
            "thread_key": "archive_main", "progress_type": "advanced", "progress_summary": stage,
            "before_stage": "寻找入口", "after_stage": stage, "progress_score": 0.9,
            "source_node_keys": [f"chapter_{number}_event"],
        }],
        "open_actions": ["继续调查"], "open_hooks": ["手机主人是谁"],
        "emotional_residue": ["沈照夜仍然怀疑顾临舟"], "forbidden_repetition": [],
        "next_chapter_seeds": ["进入深层档案室"],
    }


def persist_state(project_id: str, chapter: dict, payload: dict) -> None:
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


def add_chapter(client: TestClient, project_id: str, number: int, draft: str, fact: str) -> dict:
    chapter = client.post(
        f"/api/projects/{project_id}/chapters",
        json={
            "chapter_number": number, "title": f"第 {number} 章 · 档案馆",
            "brief": "推进旧档案馆主线", "draft": draft, "summary": fact, "status": "final",
        },
    ).json()
    persist_state(project_id, chapter, memory_payload(number, fact, stage=f"第 {number} 章推进"))
    return chapter


def test_obsidian_export_builds_incremental_vault_canvas_and_zip(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={"title": "Obsidian 导出测试", "genre": "悬疑", "target_chapter_count": 5},
    ).json()
    client.post(
        f"/api/projects/{project['id']}/characters",
        json={"title": "沈照夜", "content": "冷静、敏锐，正在追查失踪名单。", "payload": {"character_key": "hero"}},
    )
    chapter = add_chapter(
        client, project["id"], 1,
        "沈照夜在暴雨中进入旧档案馆。",
        "沈照夜发现入口地图来自监察司。",
    )

    response = client.post(f"/api/projects/{project['id']}/obsidian/export", json={})
    assert response.status_code == 200
    exported = response.json()
    assert exported["status"] == "completed"
    assert exported["file_count"] > 15
    assert exported["created_count"] == exported["file_count"]

    vault = Path(exported["vault_path"])
    assert vault.is_dir()
    assert (vault / "README.md").is_file()
    assert "主世界线" in (vault / "README.md").read_text(encoding="utf-8")

    chapter_file = next(row for row in exported["files"] if row["source_type"] == "chapter")
    chapter_text = (vault / chapter_file["relative_path"]).read_text(encoding="utf-8")
    assert "沈照夜在暴雨中进入旧档案馆" in chapter_text
    assert "旧档案馆主线" in chapter_text

    story_canvas = json.loads((vault / "Canvas/剧情网络.canvas").read_text(encoding="utf-8"))
    assert story_canvas["nodes"]
    assert story_canvas["edges"]
    assert all(node.get("file", "").endswith(".md") for node in story_canvas["nodes"])

    manifest = client.get(f"/api/projects/{project['id']}/obsidian/manifest")
    assert manifest.status_code == 200
    assert manifest.json()["worldline"]["name"] == "主世界线"
    assert manifest.json()["stats"]["chapters"] == 1

    archive = client.get(f"/api/projects/{project['id']}/obsidian/download")
    assert archive.status_code == 200
    with zipfile.ZipFile(io.BytesIO(archive.content)) as zipped:
        assert "manifest.json" in zipped.namelist()
        assert "Canvas/剧情网络.canvas" in zipped.namelist()

    unchanged = client.post(f"/api/projects/{project['id']}/obsidian/export", json={}).json()
    assert unchanged["created_count"] == 0
    assert unchanged["updated_count"] == 0
    assert unchanged["unchanged_count"] == unchanged["file_count"]

    from backend.app.database import connect, utc_now

    with connect() as conn:
        conn.execute(
            "UPDATE chapters SET draft = ?, updated_at = ? WHERE id = ?",
            ("沈照夜改为从地下水道进入档案馆。", utc_now(), chapter["id"]),
        )
        conn.execute(
            "DELETE FROM narrative_debts WHERE project_id = ? AND debt_key = 'phone_owner'",
            (project["id"],),
        )

    changed = client.post(f"/api/projects/{project['id']}/obsidian/export", json={}).json()
    assert changed["updated_count"] >= 2
    assert changed["deleted_count"] == 1
    updated_chapter_file = next(row for row in changed["files"] if row["source_type"] == "chapter")
    assert "地下水道" in (vault / updated_chapter_file["relative_path"]).read_text(encoding="utf-8")
    assert not any(row["source_type"] == "narrative-debt" for row in changed["files"])


def test_obsidian_exports_are_isolated_per_worldline(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={"title": "世界线知识库", "target_chapter_count": 4},
    ).json()
    add_chapter(client, project["id"], 1, "主线第一章。", "主线发现入口地图。")

    branch = client.post(
        f"/api/projects/{project['id']}/worldlines/fork",
        json={"name": "地面调查线", "fork_chapter_number": 1},
    ).json()
    branch_project_id = branch["project_id"]
    add_chapter(
        client, branch_project_id, 2,
        "分支第二章改为调查地面监察站。",
        "分支确认监察站藏有名单副本。",
    )

    main_export = client.post(f"/api/projects/{project['id']}/obsidian/export", json={}).json()
    branch_export = client.post(f"/api/projects/{branch_project_id}/obsidian/export", json={}).json()
    assert main_export["vault_path"] != branch_export["vault_path"]
    assert main_export["archive_path"] != branch_export["archive_path"]

    main_vault = Path(main_export["vault_path"])
    branch_vault = Path(branch_export["vault_path"])
    main_chapters = [row for row in main_export["files"] if row["source_type"] == "chapter"]
    branch_chapters = [row for row in branch_export["files"] if row["source_type"] == "chapter"]
    assert len(main_chapters) == 1
    assert len(branch_chapters) == 2
    assert "地面调查线" in (branch_vault / "README.md").read_text(encoding="utf-8")
    assert "地面调查线" not in (main_vault / "README.md").read_text(encoding="utf-8")
    assert not any("分支第二章" in (main_vault / row["relative_path"]).read_text(encoding="utf-8") for row in main_chapters)
    assert any("分支第二章" in (branch_vault / row["relative_path"]).read_text(encoding="utf-8") for row in branch_chapters)
