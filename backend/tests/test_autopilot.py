import importlib

from fastapi.testclient import TestClient


def make_client(monkeypatch, tmp_path, *, sync_worker: bool = False, disable_worker: bool = False):
    monkeypatch.setenv("AI_NOVEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_NOVEL_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("AI_NOVEL_AUTOPILOT_RETRY_DELAY_SECONDS", "0")
    if sync_worker:
        monkeypatch.setenv("AI_NOVEL_AUTOPILOT_SYNC", "1")
    else:
        monkeypatch.delenv("AI_NOVEL_AUTOPILOT_SYNC", raising=False)
    if disable_worker:
        monkeypatch.setenv("AI_NOVEL_AUTOPILOT_DISABLE_WORKER", "1")
    else:
        monkeypatch.delenv("AI_NOVEL_AUTOPILOT_DISABLE_WORKER", raising=False)

    import backend.app.main as main

    importlib.reload(main)
    main.init_app()
    return main, TestClient(main.app)


def test_autopilot_runs_persisted_chapter_pipeline(monkeypatch, tmp_path):
    main, client = make_client(monkeypatch, tmp_path, sync_worker=True)
    project = client.post(
        "/api/projects",
        json={"title": "托管测试", "target_chapter_count": 1},
    ).json()

    def fake_ai_workflow(project_id, workflow, payload):
        assert project_id == project["id"]
        assert payload.chapter_id
        if workflow == "generate_chapter_brief":
            return {
                "workflow": workflow,
                "model": "fake-model",
                "text": '{"chapter_title":"第 1 章 · 暴雨出口","chapter_goal":"承接追捕并进入档案馆"}',
                "structured": {
                    "chapter_title": "第 1 章 · 暴雨出口",
                    "chapter_goal": "承接追捕并进入档案馆",
                },
                "status": "success",
            }
        return {
            "workflow": workflow,
            "model": "fake-model",
            "text": "雨水顺着地下出口灌进来，她捂住受伤的左肩继续向旧地铁站移动。",
            "structured": None,
            "status": "success",
        }

    monkeypatch.setattr(main, "run_ai_workflow", fake_ai_workflow)

    response = client.post(
        f"/api/projects/{project['id']}/autopilot/start",
        json={"start_chapter": 1, "end_chapter": 1, "max_retries": 0},
    )

    assert response.status_code == 200
    snapshot = response.json()
    assert snapshot["job"]["status"] == "completed"
    assert snapshot["progress"]["percent"] == 100
    assert [step["status"] for step in snapshot["steps"]] == ["completed", "completed", "completed"]

    chapters = client.get(f"/api/projects/{project['id']}/chapters").json()
    assert len(chapters) == 1
    assert chapters[0]["status"] == "final"
    assert chapters[0]["title"] == "第 1 章 · 暴雨出口"
    assert "受伤的左肩" in chapters[0]["draft"]

    versions = client.get(
        f"/api/projects/{project['id']}/chapters/{chapters[0]['id']}/versions"
    ).json()
    assert len(versions) == 1
    assert versions[0]["model"] == "fake-model"


def test_autopilot_can_pause_resume_and_stop_without_losing_steps(monkeypatch, tmp_path):
    _main, client = make_client(monkeypatch, tmp_path, disable_worker=True)
    project = client.post(
        "/api/projects",
        json={"title": "控制测试", "target_chapter_count": 2},
    ).json()

    started = client.post(
        f"/api/projects/{project['id']}/autopilot/start",
        json={"start_chapter": 1, "end_chapter": 2},
    )
    assert started.status_code == 200
    job_id = started.json()["job"]["id"]
    assert started.json()["job"]["status"] == "queued"
    assert len(started.json()["steps"]) == 6

    paused = client.post(f"/api/projects/{project['id']}/autopilot/jobs/{job_id}/pause")
    assert paused.status_code == 200
    assert paused.json()["job"]["status"] == "paused"

    resumed = client.post(f"/api/projects/{project['id']}/autopilot/jobs/{job_id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["job"]["status"] == "queued"
    assert len(resumed.json()["steps"]) == 6

    stopped = client.post(f"/api/projects/{project['id']}/autopilot/jobs/{job_id}/stop")
    assert stopped.status_code == 200
    assert stopped.json()["job"]["status"] == "cancelled"
    assert all(step["status"] == "cancelled" for step in stopped.json()["steps"])


def test_failed_autopilot_step_can_be_retried(monkeypatch, tmp_path):
    main, client = make_client(monkeypatch, tmp_path, sync_worker=True)
    project = client.post(
        "/api/projects",
        json={"title": "失败重试测试", "target_chapter_count": 1},
    ).json()

    def failing_ai_workflow(_project_id, _workflow, _payload):
        raise RuntimeError("temporary model failure")

    monkeypatch.setattr(main, "run_ai_workflow", failing_ai_workflow)
    failed = client.post(
        f"/api/projects/{project['id']}/autopilot/start",
        json={"start_chapter": 1, "end_chapter": 1, "max_retries": 0},
    )
    assert failed.status_code == 200
    failed_snapshot = failed.json()
    assert failed_snapshot["job"]["status"] == "failed"
    failed_step = next(step for step in failed_snapshot["steps"] if step["status"] == "failed")
    assert "temporary model failure" in failed_step["error_message"]

    def successful_ai_workflow(_project_id, workflow, _payload):
        if workflow == "generate_chapter_brief":
            return {
                "workflow": workflow,
                "model": "fake-model",
                "text": "brief",
                "structured": {"chapter_title": "第 1 章 · 重试成功", "chapter_goal": "继续推进"},
                "status": "success",
            }
        return {
            "workflow": workflow,
            "model": "fake-model",
            "text": "重试后生成的正文。",
            "structured": None,
            "status": "success",
        }

    monkeypatch.setattr(main, "run_ai_workflow", successful_ai_workflow)
    retried = client.post(
        f"/api/projects/{project['id']}/autopilot/jobs/{failed_snapshot['job']['id']}/steps/{failed_step['id']}/retry"
    )

    assert retried.status_code == 200
    assert retried.json()["job"]["status"] == "completed"
    assert all(step["status"] == "completed" for step in retried.json()["steps"])
