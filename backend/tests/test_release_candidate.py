import importlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'release.db'}")
    monkeypatch.setenv("AI_NOVEL_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("AI_NOVEL_MASTER_KEY_FILE", str(tmp_path / "master.key"))
    monkeypatch.setenv("AI_NOVEL_AUTO_MIGRATE", "1")
    monkeypatch.setenv("AI_NOVEL_RUNTIME_SYNC", "1")
    monkeypatch.setenv("AI_NOVEL_AUTOPILOT_SYNC", "1")
    monkeypatch.setenv("AI_NOVEL_AUTOPILOT_RETRY_DELAY_SECONDS", "0")
    monkeypatch.delenv("AI_NOVEL_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("AI_NOVEL_MASTER_KEY", raising=False)

    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return main, TestClient(main.app)


def deterministic_workflow(workflow: str):
    if workflow == "generate_chapter_brief":
        structured = {
            "chapter_title": "第 1 章 · 暴雨档案馆",
            "chapter_goal": "进入旧档案馆并发现失踪名单线索",
            "must_preserve": ["沈照夜左肩受伤"],
            "must_advance": ["旧档案馆主线"],
            "must_avoid": ["重复第一次发现档案馆"],
        }
        return {"workflow": workflow, "model": "release-test-model", "text": json.dumps(structured, ensure_ascii=False), "structured": structured, "status": "success"}
    if workflow == "check_consistency":
        structured = {"status": "pass", "score": 97, "issues": [], "continuity_summary": "时间、地点与人物状态一致"}
        return {"workflow": workflow, "model": "release-test-model", "text": json.dumps(structured, ensure_ascii=False), "structured": structured, "status": "success"}
    if workflow == "extract_memory":
        structured = {
            "summary": "沈照夜带伤进入旧档案馆，并发现监察司失踪名单的入口线索。",
            "ending_state": {
                "time": "凌晨两点十五分",
                "location": "旧档案馆入口",
                "weather": "暴雨",
                "current_action": "她正在破解入口终端",
                "current_danger": "监察司追兵接近",
            },
            "hard_facts": [{
                "fact_key": "archive_entry_found",
                "fact_text": "沈照夜已经找到旧档案馆入口。",
                "fact_status": "confirmed",
                "confidence": 1,
            }],
            "character_states": [{
                "character_id": "hero",
                "character_name": "沈照夜",
                "location": "旧档案馆入口",
                "physical_state": "左肩受伤",
                "emotional_state": "警惕但坚定",
                "current_goal": "进入深层档案室",
                "alive_status": "alive",
                "visibility_status": "public",
            }],
            "knowledge_changes": [],
            "relationship_changes": [],
            "item_changes": [{
                "item_key": "archive_phone",
                "item_name": "档案馆手机",
                "description": "保存着入口地图。",
                "item_status": "active",
                "change_type": "created",
                "owner_type": "character",
                "owner_name": "沈照夜",
                "location": "旧档案馆入口",
                "ownership_status": "held",
            }],
            "narrative_debt_changes": [{
                "debt_key": "archive_owner",
                "debt_type": "open_question",
                "description": "谁控制旧档案馆？",
                "status": "open",
                "priority": 0.8,
                "deadline_chapter": 3,
            }],
            "foreshadowing_changes": [{
                "foreshadowing_key": "phone_crack",
                "title": "手机裂纹",
                "description": "裂纹与监察司徽记一致。",
                "status": "planted",
                "setup_chapter": 1,
                "payoff_chapter": 3,
                "priority": 0.8,
            }],
            "story_thread_changes": [{
                "thread_key": "archive_main",
                "title": "旧档案馆主线",
                "thread_type": "main_plot",
                "status": "active",
                "priority": 1,
                "current_stage": "发现入口",
                "current_goal": "进入深层档案室",
                "next_target": "找到失踪名单",
                "stall_tolerance": 2,
            }],
            "story_node_changes": [
                {
                    "node_key": "find_archive_entry",
                    "thread_key": "archive_main",
                    "node_type": "reveal",
                    "title": "发现旧档案馆入口",
                    "description": "沈照夜破解入口终端。",
                    "status": "completed",
                    "importance": 0.9,
                    "planned_chapter": 1,
                    "actual_chapter": 1,
                },
                {
                    "node_key": "enter_deep_archive",
                    "thread_key": "archive_main",
                    "node_type": "goal",
                    "title": "进入深层档案室",
                    "description": "继续向档案馆深处推进。",
                    "status": "planned",
                    "importance": 0.8,
                    "planned_chapter": 2,
                    "actual_chapter": 0,
                },
            ],
            "story_edge_changes": [{
                "edge_key": "entry_causes_deep_archive",
                "source_node_key": "find_archive_entry",
                "target_node_key": "enter_deep_archive",
                "relation_type": "causes",
                "status": "active",
                "weight": 0.9,
            }],
            "story_progress": [{
                "thread_key": "archive_main",
                "progress_type": "advanced",
                "progress_summary": "旧档案馆入口已找到",
                "before_stage": "寻找入口",
                "after_stage": "发现入口",
                "progress_score": 0.9,
                "source_node_keys": ["find_archive_entry"],
            }],
            "open_actions": ["进入深层档案室"],
            "open_hooks": ["谁控制旧档案馆"],
            "emotional_residue": ["沈照夜仍然怀疑顾临舟"],
            "forbidden_repetition": ["不能再次第一次发现入口"],
            "next_chapter_seeds": ["追兵进入档案馆"],
        }
        return {"workflow": workflow, "model": "release-test-model", "text": json.dumps(structured, ensure_ascii=False), "structured": structured, "status": "success"}
    text = "暴雨灌入废弃通道，沈照夜捂着受伤的左肩，破解了旧档案馆入口终端。"
    return {"workflow": workflow, "model": "release-test-model", "text": text, "structured": None, "status": "success"}


def test_release_info_readiness_and_setup_lifecycle(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)

    info = client.get("/api/release/info")
    assert info.status_code == 200
    payload = info.json()
    assert payload["version"] == "1.0.0-rc.1"
    assert payload["release_channel"] == "release-candidate"
    assert payload["schema_version"] == payload["latest_schema_version"] == 4
    assert payload["setup_completed"] is False
    assert "autopilot" in payload["capabilities"]
    assert "encrypted-credentials" in payload["capabilities"]

    readiness = client.get("/api/release/readiness").json()
    assert readiness["status"] == "ready"
    assert readiness["ready"] is True
    assert not readiness["blockers"]
    assert any(item["id"] == "model" for item in readiness["warnings"])

    denied = client.post(
        "/api/setup/complete",
        json={"confirmation": "COMPLETE_SETUP", "acknowledge_without_model": False},
    )
    assert denied.status_code == 409

    completed = client.post(
        "/api/setup/complete",
        json={"confirmation": "COMPLETE_SETUP", "acknowledge_without_model": True},
    )
    assert completed.status_code == 200
    assert completed.json()["state"]["first_run_completed"] is True
    assert client.get("/api/release/info").json()["setup_completed"] is True

    reset = client.post("/api/setup/reset", json={"confirmation": "RESET_SETUP"})
    assert reset.status_code == 200
    assert reset.json()["first_run_completed"] is False
    assert reset.json()["setup_step"] == "welcome"


def test_release_candidate_golden_path(monkeypatch, tmp_path):
    main, client = make_client(monkeypatch, tmp_path)
    project = client.post(
        "/api/projects",
        json={
            "title": "发布黄金路径",
            "genre": "悬疑",
            "target_chapter_count": 3,
            "target_words_per_chapter": 1800,
        },
    ).json()

    secret = "sk-release-golden-path-secret"
    model = client.post(
        f"/api/projects/{project['id']}/model-configs",
        json={
            "title": "发布测试模型",
            "category": "OpenAI",
            "content": "release-test-model",
            "payload": {
                "provider": "OpenAI",
                "api_key": secret,
                "base_url": "https://example.invalid/v1",
                "model_name": "release-test-model",
                "temperature": 0.6,
                "max_tokens": 4096,
                "is_default": True,
            },
            "status": "active",
        },
    )
    assert model.status_code == 200
    assert model.json()["payload"]["api_key"] == ""
    assert model.json()["payload"]["credential_id"]
    assert secret not in model.text

    def fake_ai_workflow(project_id, workflow, payload):
        assert project_id == project["id"]
        return deterministic_workflow(workflow)

    monkeypatch.setattr(main, "run_ai_workflow", fake_ai_workflow)
    started = client.post(
        f"/api/projects/{project['id']}/autopilot/start",
        json={"start_chapter": 1, "end_chapter": 1, "max_retries": 0},
    )
    assert started.status_code == 200
    snapshot = started.json()
    assert snapshot["job"]["status"] == "completed"
    assert snapshot["progress"]["percent"] == 100

    chapters = client.get(f"/api/projects/{project['id']}/chapters").json()
    assert len(chapters) == 1
    assert chapters[0]["status"] == "final"
    assert "旧档案馆" in chapters[0]["draft"]

    facts = client.get(f"/api/projects/{project['id']}/memory/facts").json()
    graph = client.get(f"/api/projects/{project['id']}/story-graph").json()
    plan = client.get(f"/api/projects/{project['id']}/planning/current").json()
    assert any(item["fact_key"] == "archive_entry_found" for item in facts)
    assert any(item["thread_key"] == "archive_main" for item in graph["all_threads"])
    assert plan

    branch = client.post(
        f"/api/projects/{project['id']}/worldlines/fork",
        json={"name": "地面调查分支", "fork_chapter_number": 1, "description": "不进入深层档案室。"},
    )
    assert branch.status_code == 200
    assert branch.json()["project_id"] != project["id"]

    export = client.post(
        f"/api/projects/{project['id']}/obsidian/export",
        json={"include_drafts": True, "force_rebuild": False, "create_archive": True},
    )
    assert export.status_code == 200
    export_payload = export.json()
    assert export_payload.get("status") in {"completed", "success"}
    obsidian_status = client.get(f"/api/projects/{project['id']}/obsidian/status").json()
    assert obsidian_status["exists"] is True
    assert Path(obsidian_status["archive_path"]).is_file()

    backup = client.post("/api/runtime/backups", json={"note": "Golden path backup"})
    assert backup.status_code == 200
    assert backup.json()["integrity"].lower() == "ok"

    readiness = client.get("/api/release/readiness").json()
    assert readiness["ready"] is True
    assert not any(item["id"] == "model" for item in readiness["warnings"])
    completed = client.post(
        "/api/setup/complete",
        json={"confirmation": "COMPLETE_SETUP", "acknowledge_without_model": False},
    )
    assert completed.status_code == 200
    assert client.get("/api/release/info").json()["setup_completed"] is True

    database_bytes = (tmp_path / "release.db").read_bytes()
    assert secret.encode("utf-8") not in database_bytes


def test_release_artifact_builder_is_reproducible_and_secret_safe(tmp_path):
    root = Path(__file__).resolve().parents[2]
    output_a = tmp_path / "release-a"
    output_b = tmp_path / "release-b"
    environment = {**os.environ, "SOURCE_DATE_EPOCH": "1700000000", "GITHUB_SHA": "release-test-commit"}

    for output in (output_a, output_b):
        built = subprocess.run(
            [sys.executable, "scripts/build_release.py", "--output", str(output)],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert built.returncode == 0, built.stdout + built.stderr
        verified = subprocess.run(
            [sys.executable, "scripts/build_release.py", "--output", str(output), "--verify"],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert verified.returncode == 0, verified.stdout + verified.stderr

    result_a = json.loads((output_a / "release-result.json").read_text(encoding="utf-8"))
    result_b = json.loads((output_b / "release-result.json").read_text(encoding="utf-8"))
    assert result_a["version"] == "1.0.0-rc.1"
    assert result_a["archive_sha256"] == result_b["archive_sha256"]

    manifest = json.loads(Path(result_a["manifest"]).read_text(encoding="utf-8"))
    assert manifest["version"] == "1.0.0-rc.1"
    assert manifest["schema_version"] == 4
    assert manifest["commit"] == "release-test-commit"
    assert manifest["files"]

    archive = Path(result_a["archive"])
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        assert any(name.endswith("/VERSION") for name in names)
        assert any(name.endswith("/release-manifest.json") for name in names)
        assert not any("node_modules" in name for name in names)
        assert not any(name.endswith((".env", ".key", ".db", ".sqlite")) for name in names)
