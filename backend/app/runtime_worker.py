import argparse
import os
import signal
import socket
import time
from typing import Any

from .database import new_id
from .runtime_queue import (
    abandon_generation_claim,
    claim_generation_job,
    claim_runtime_task,
    clear_generation_claim,
    complete_runtime_task,
    fail_runtime_task,
    heartbeat_generation_job,
    heartbeat_pump,
    heartbeat_runtime_task,
    heartbeat_worker,
    recover_stale_generation_jobs,
    register_worker,
    stop_worker,
)
from .runtime_recovery import recover_stale_runtime_tasks


class RuntimeWorker:
    def __init__(self, *, worker_type: str = "all", poll_interval: float = 1.0, worker_id: str = "") -> None:
        if worker_type not in {"all", "autopilot", "exports"}:
            raise ValueError("worker_type must be all, autopilot, or exports")
        self.worker_type = worker_type
        self.poll_interval = max(0.1, float(poll_interval))
        self.worker_id = worker_id or f"{socket.gethostname()}-{os.getpid()}-{new_id()[:8]}"
        self.running = False
        self.initialized = False

    def initialize(self) -> None:
        if self.initialized:
            return
        from . import main

        main.init_app()
        register_worker(
            self.worker_id,
            self.worker_type,
            {"poll_interval": self.poll_interval, "runtime": "sqlite-lease-worker"},
        )
        self.initialized = True

    def _run_generation_job(self) -> bool:
        if self.worker_type not in {"all", "autopilot"}:
            return False
        job = claim_generation_job(self.worker_id)
        if not job:
            return False

        from . import autopilot

        job_id = str(job["id"])
        heartbeat_worker(self.worker_id, task_type="autopilot", task_id=job_id)
        try:
            with heartbeat_pump(
                [
                    lambda: heartbeat_worker(self.worker_id, task_type="autopilot", task_id=job_id),
                    lambda: heartbeat_generation_job(job_id, self.worker_id),
                ]
            ):
                autopilot._process_job(job_id)
        except Exception as exc:
            abandon_generation_claim(job_id, self.worker_id, str(exc))
        finally:
            clear_generation_claim(job_id, self.worker_id)
            heartbeat_worker(self.worker_id)
        return True

    def _execute_runtime_task(self, task: dict[str, Any]) -> dict[str, Any]:
        task_type = str(task.get("task_type") or "")
        payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
        if task_type == "obsidian_export":
            from .obsidian_exporter import export_obsidian_vault

            return export_obsidian_vault(
                str(task.get("project_id") or ""),
                include_drafts=bool(payload.get("include_drafts", True)),
                force_rebuild=bool(payload.get("force_rebuild", False)),
                create_archive=bool(payload.get("create_archive", True)),
            )
        raise RuntimeError(f"Unsupported runtime task type: {task_type}")

    def _run_runtime_task(self) -> bool:
        if self.worker_type not in {"all", "exports"}:
            return False
        task = claim_runtime_task(self.worker_id, ("obsidian_export",))
        if not task:
            return False
        task_id = str(task["id"])
        task_type = str(task.get("task_type") or "")
        heartbeat_worker(self.worker_id, task_type=task_type, task_id=task_id)
        try:
            with heartbeat_pump(
                [
                    lambda: heartbeat_worker(self.worker_id, task_type=task_type, task_id=task_id),
                    lambda: heartbeat_runtime_task(task_id, self.worker_id),
                ]
            ):
                result = self._execute_runtime_task(task)
            complete_runtime_task(task_id, self.worker_id, result)
        except Exception as exc:
            fail_runtime_task(task_id, self.worker_id, str(exc))
        finally:
            heartbeat_worker(self.worker_id)
        return True

    def run_once(self) -> bool:
        self.initialize()
        recover_stale_generation_jobs()
        recover_stale_runtime_tasks()
        heartbeat_worker(self.worker_id)
        return self._run_generation_job() or self._run_runtime_task()

    def run_forever(self) -> None:
        self.initialize()
        self.running = True
        while self.running:
            worked = self.run_once()
            if not worked:
                heartbeat_worker(self.worker_id)
                time.sleep(self.poll_interval)

    def stop(self) -> None:
        self.running = False
        if self.initialized:
            stop_worker(self.worker_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Novel independent SQLite runtime worker")
    parser.add_argument("--once", action="store_true", help="Claim at most one task and exit")
    parser.add_argument("--worker-type", choices=("all", "autopilot", "exports"), default="all")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    args = parser.parse_args()

    worker = RuntimeWorker(worker_type=args.worker_type, poll_interval=args.poll_interval)

    def stop_handler(_signum, _frame) -> None:
        worker.stop()

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)
    try:
        if args.once:
            worker.run_once()
        else:
            worker.run_forever()
    finally:
        worker.stop()


if __name__ == "__main__":
    main()
