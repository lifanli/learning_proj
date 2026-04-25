import json
import threading
import time

from src.core.progress import raise_if_cancel_requested, report_progress
from src.webapi.task_runtime import BackgroundTaskRegistry


def _wait_for_task(registry: BackgroundTaskRegistry, task_id: str, timeout: float = 3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = registry.get(task_id)
        if task and task.status in {"succeeded", "failed", "canceled", "interrupted"}:
            return task
        time.sleep(0.02)
    raise AssertionError("task did not finish in time")


def test_background_task_registry_persists_completed_tasks(tmp_path):
    storage_path = tmp_path / "tasks.json"
    registry = BackgroundTaskRegistry(max_workers=1, storage_path=storage_path)
    try:
        task = registry.submit("test.large_result", lambda: {"status": "ok", "payload": "x" * 1000})
        finished = _wait_for_task(registry, task.id)
        assert finished.status == "succeeded"
    finally:
        registry.shutdown()

    reloaded = BackgroundTaskRegistry(max_workers=1, storage_path=storage_path)
    try:
        loaded = reloaded.get(task.id)
        listed = reloaded.list()

        assert loaded is not None
        assert loaded.status == "succeeded"
        assert loaded.progress == 100
        assert loaded.result["payload"] == "x" * 1000
        assert listed[0]["id"] == task.id
        assert listed[0]["has_result"] is True
        assert listed[0]["result_summary"]
        assert "result" not in listed[0]
    finally:
        reloaded.shutdown()


def test_background_task_registry_marks_incomplete_tasks_interrupted(tmp_path):
    storage_path = tmp_path / "tasks.json"
    storage_path.write_text(
        json.dumps(
            {
                "version": 1,
                "tasks": [
                    {
                        "id": "abc123",
                        "kind": "publish.book",
                        "status": "running",
                        "created_at": 1.0,
                        "updated_at": 2.0,
                        "message": "publish.book started",
                        "error": "",
                        "progress": 25,
                        "result": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    registry = BackgroundTaskRegistry(max_workers=1, storage_path=storage_path)
    try:
        task = registry.get("abc123")
        persisted = json.loads(storage_path.read_text(encoding="utf-8"))

        assert task is not None
        assert task.status == "interrupted"
        assert task.progress == 100
        assert "interrupted" in task.message
        assert persisted["tasks"][0]["status"] == "interrupted"
    finally:
        registry.shutdown()


def test_background_task_registry_cancels_queued_task(tmp_path):
    storage_path = tmp_path / "tasks.json"
    started = threading.Event()
    release = threading.Event()

    def blocking_task():
        started.set()
        release.wait(timeout=3)
        return {"done": True}

    registry = BackgroundTaskRegistry(max_workers=1, storage_path=storage_path)
    try:
        first = registry.submit("test.blocking", blocking_task)
        assert started.wait(timeout=3)
        queued = registry.submit("test.queued", lambda: {"should_not_run": True})

        canceled = registry.cancel(queued.id)
        release.set()
        finished_first = _wait_for_task(registry, first.id)
        finished_queued = _wait_for_task(registry, queued.id)

        assert canceled is not None
        assert canceled.status == "canceled"
        assert canceled.progress == 100
        assert finished_first.status == "succeeded"
        assert finished_queued.status == "canceled"
        assert finished_queued.result is None
    finally:
        release.set()
        registry.shutdown()


def test_background_task_registry_cooperatively_cancels_running_task(tmp_path):
    storage_path = tmp_path / "tasks.json"
    started = threading.Event()

    def cancellable_task():
        started.set()
        for _ in range(300):
            raise_if_cancel_requested()
            time.sleep(0.01)
        return {"done": True}

    registry = BackgroundTaskRegistry(max_workers=1, storage_path=storage_path)
    try:
        task = registry.submit("test.cancellable", cancellable_task)
        assert started.wait(timeout=3)

        canceled = registry.cancel(task.id)
        finished = _wait_for_task(registry, task.id)

        assert canceled is not None
        assert canceled.status in {"cancel_requested", "canceled"}
        assert finished.status == "canceled"
        assert finished.progress == 100
        assert finished.result is None
    finally:
        registry.shutdown()


def test_background_task_registry_summarizes_errors_in_listing(tmp_path):
    storage_path = tmp_path / "tasks.json"

    def failing_task():
        raise RuntimeError("first line failure")

    registry = BackgroundTaskRegistry(max_workers=1, storage_path=storage_path)
    try:
        task = registry.submit("test.failing", failing_task)
        failed = _wait_for_task(registry, task.id)

        listed = registry.list()[0]
        detail = registry.to_dict(failed)

        assert failed.status == "failed"
        assert listed["error"] == "first line failure"
        assert listed["has_error_detail"] is True
        assert "Traceback" not in listed["error"]
        assert "Traceback" in detail["error"]
    finally:
        registry.shutdown()


def test_background_task_registry_retries_failed_task(tmp_path):
    storage_path = tmp_path / "tasks.json"
    calls = []

    def flaky_task(value):
        calls.append(value)
        if len(calls) == 1:
            raise RuntimeError("first attempt failed")
        return {"value": value, "attempts": len(calls)}

    registry = BackgroundTaskRegistry(max_workers=1, storage_path=storage_path)
    try:
        failed = registry.submit("test.flaky", flaky_task, "ok")
        failed = _wait_for_task(registry, failed.id)
        retried = registry.retry(failed.id)
        succeeded = _wait_for_task(registry, retried.id)

        assert failed.status == "failed"
        assert retried.retry_of == failed.id
        assert succeeded.status == "succeeded"
        assert succeeded.result == {"value": "ok", "attempts": 2}
    finally:
        registry.shutdown()


def test_background_task_registry_applies_in_task_progress_reports(tmp_path):
    storage_path = tmp_path / "tasks.json"
    reached_middle = threading.Event()
    release = threading.Event()

    def staged_task():
        report_progress(42, "middle stage")
        reached_middle.set()
        release.wait(timeout=3)
        return {"done": True}

    registry = BackgroundTaskRegistry(max_workers=1, storage_path=storage_path)
    try:
        task = registry.submit("test.staged", staged_task)
        assert reached_middle.wait(timeout=3)
        current = registry.get(task.id)

        assert current is not None
        assert current.progress == 42
        assert current.message == "middle stage"

        release.set()
        finished = _wait_for_task(registry, task.id)
        assert finished.status == "succeeded"
        assert finished.progress == 100
    finally:
        release.set()
        registry.shutdown()
