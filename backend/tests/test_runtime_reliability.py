import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("AI_NOVEL_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("AI_NOVEL_AUTOPILOT_RETRY_DELAY_SECONDS", "0")
    monkeypatch.setenv("AI_NOVEL_RUNTIME_LEASE_SECONDS", "15")
    monkeypatch.setenv("AI_NOVEL_RUNTIME_HEARTBEAT_SECONDS", "1")
    monkeypatch.delenv("AI_NOVEL_RUNTIME_SYNC", raising=False)
    monkeypatch.delenv("AI_NOVEL_AUTOPILOT_SYNC", raising=False)
    monkeypatch.delenv("AI_NOVEL_AUTOPILOT_DISABLE_WORKER", raising=False)
    monkeypatch.delenv("AI_NOVEL_AUTOPILOT_LEGACY_THREADS", raising=False)

    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return main, TestClient(main.app)


def workflow_response(workflow: str):
    if workflow == "generate_chapter_brief":
        return {
            "workflow": workflow,
            "model": "runtime-test",
            "text": "brief",
            "structured": {"chapter_title": "第 1 章 · Worker", "chapter_goal": "验证独立 Worker"},
            "status": "success",
        }
    if workflow == "check_consistency":
        return {
            "workflow": workflow,
            "model": "runtime-test",
            "text": "check",
            "structured": {"status": "pass", "score": 98, "issues": [], "continuity_summary": "正常"},
            "status": "success",
        }
    if workflow == "extract_memory":
        return {
            "workflow": workflow,
            "model": "runtime-test",
            "text": "memory",
            "structured": {
                "summary": "Worker 完成章节。",
                "ending_state": {"time": "夜", "location": "测试场景"},
                "character_states": [],
                "knowledge_changes": [],
                "relationship_changes": [],
                "hard_facts": [{"fact_key": "worker_done", "fact_text": "独立 Worker 已完成章节", "fact_status": "confirmed", "confidence": 1}],
                "item_changes": [],
                "narrative_debt_changes": [],
                "foreshadowing_changes": [],
                "story_thread_changes": [],
                "story_node_changes": [],
                "story_edge_changes": [],
                "story_progress": [],
                "open_actions": [],
                "open_hooks": [],
                "emotional_residue": [],
                "forbidden_repetition": [],
                "next_chapter_seeds": [],
            },
            "status": "success",
        }
    return {
        "workflow": workflow,
        "model": "runtime-test",
        "text": "独立 Worker 正在执行并完成章节正文。",
        "structured": None,
        "status": "success",
    }


def test_external_worker_claims_and_completes_autopilot(monkeypatch, tmp_path):
    main, client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "Worker 小说", "target_chapter_count": 1}).json()
    monkeypatch.setattr(main, "run_ai_workflow", lambda _project_id, workflow, _payload: workflow_response(workflow))

    started = client.post(
        f"/api/projects/{project['id']}/autopilot/start",
        json={"start_chapter": 1, "end_chapter": 1, "max_retries": 0},
    )
    assert started.status_code == 200
    assert started.json()["job"]["status"] == "queued"

    health = client.get("/api/runtime/health").json()
    assert health["status"] == "degraded"
    assert any("没有健康的独立 Worker" in warning for warning in health["warnings"])

    from backend.app.runtime_worker import RuntimeWorker

    worker = RuntimeWorker(worker_type="autopilot", worker_id="test-autopilot-worker")
    assert worker.run_once() is True
    worker.stop()

    completed = client.get(f"/api/projects/{project['id']}/autopilot/status").json()
    assert completed["job"]["status"] == "completed"
    assert completed["progress"]["percent"] == 100
    assert len(completed["steps"]) == 8
    assert all(step["status"] == "completed" for step in completed["steps"])
    assert completed["job"]["worker_id"] == ""
    workers = client.get("/api/runtime/workers").json()
    assert workers[0]["id"] == "test-autopilot-worker"
    assert workers[0]["status"] == "stopped"


def test_expired_generation_lease_is_requeued(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "恢复测试", "target_chapter_count": 1}).json()
    started = client.post(
        f"/api/projects/{project['id']}/autopilot/start",
        json={"start_chapter": 1, "end_chapter": 1},
    ).json()
    job_id = started["job"]["id"]
    step_id = started["steps"][0]["id"]

    from backend.app.database import connect, utc_now

    with connect() as conn:
        conn.execute(
            """
            UPDATE generation_jobs
            SET status='running', worker_id='dead-worker', claimed_at=?, heartbeat_at=?,
                lease_expires_at='2000-01-01T00:00:00+00:00'
            WHERE id=?
            """,
            (utc_now(), utc_now(), job_id),
        )
        conn.execute("UPDATE generation_steps SET status='running' WHERE id=?", (step_id,))

    recovered = client.post("/api/runtime/recover").json()
    assert recovered["recovered"]["generation_jobs"] == 1
    snapshot = client.get(f"/api/projects/{project['id']}/autopilot/status").json()
    assert snapshot["job"]["status"] == "queued"
    assert snapshot["job"]["worker_id"] == ""
    assert snapshot["job"]["recovery_count"] == 1
    assert snapshot["steps"][0]["status"] == "pending"
    assert any(event["event_type"] == "job.lease_recovered" for event in snapshot["events"])


def test_obsidian_export_runs_as_worker_task(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "异步知识库"}).json()
    client.post(
        f"/api/projects/{project['id']}/chapters",
        json={"chapter_number": 1, "title": "第一章", "draft": "异步导出正文", "status": "final"},
    )

    queued = client.post(f"/api/projects/{project['id']}/obsidian/export", json={})
    assert queued.status_code == 200
    assert queued.json()["status"] == "queued"
    task_id = queued.json()["task_id"]

    from backend.app.runtime_worker import RuntimeWorker

    worker = RuntimeWorker(worker_type="exports", worker_id="test-export-worker")
    assert worker.run_once() is True
    worker.stop()

    task = client.get(f"/api/projects/{project['id']}/obsidian/jobs/{task_id}").json()
    assert task["status"] == "completed"
    status = client.get(f"/api/projects/{project['id']}/obsidian/status").json()
    assert status["status"] == "completed"
    assert status["file_count"] > 0
    assert Path(status["archive_path"]).is_file()


def test_database_backup_and_restore_round_trip(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path)
    project = client.post("/api/projects", json={"title": "备份前标题"}).json()

    backup = client.post("/api/runtime/backups", json={"note": "阶段十恢复测试"})
    assert backup.status_code == 200
    backup_id = backup.json()["id"]
    assert Path(backup.json()["file_path"]).is_file()
    assert client.get(f"/api/runtime/backups/{backup_id}?verify=true").json()["verified"] is True

    updated = client.patch(f"/api/projects/{project['id']}", json={"title": "备份后标题"})
    assert updated.json()["title"] == "备份后标题"

    restored = client.post(
        f"/api/runtime/backups/{backup_id}/restore",
        json={"confirmation": "RESTORE"},
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "restored"
    assert restored.json()["safety_backup"]["kind"] == "pre_restore"
    assert client.get(f"/api/projects/{project['id']}").json()["title"] == "备份前标题"
