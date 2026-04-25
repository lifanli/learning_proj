from __future__ import annotations

import json
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from src.core.progress import (
    reset_cancel_checker,
    reset_progress_reporter,
    set_cancel_checker,
    set_progress_reporter,
)

DEFAULT_TASK_STORAGE_PATH = Path("data") / "webapi_tasks.json"
INTERRUPTIBLE_STATUSES = {"queued", "running", "cancel_requested"}
CANCELABLE_STATUSES = {"queued", "running"}
RETRYABLE_STATUSES = {"failed", "canceled", "interrupted"}


def _summarize_value(value: Any, limit: int = 240) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        interesting = []
        for key in ("status", "title", "output_dir", "output_path", "completed", "failed", "skipped", "total"):
            if key in value:
                interesting.append(f"{key}={value[key]}")
        if interesting:
            return ", ".join(interesting)[:limit]
    text = json.dumps(value, ensure_ascii=False, default=str) if not isinstance(value, str) else value
    text = " ".join(text.split())
    if len(text) > limit:
        return f"{text[:limit]}..."
    return text


def _summarize_error(error: str, limit: int = 320) -> str:
    if not error:
        return ""
    first_line = next((line.strip() for line in error.splitlines() if line.strip()), "")
    if not first_line:
        return ""
    if len(first_line) > limit:
        return f"{first_line[:limit]}..."
    return first_line


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


@dataclass
class TaskRecord:
    id: str
    kind: str
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    message: str = ""
    error: str = ""
    result: Any = None
    progress: int = 0
    args: list[Any] = field(default_factory=list)
    kwargs: dict[str, Any] = field(default_factory=dict)
    retry_of: Optional[str] = None

    def to_dict(self, *, include_result: bool = True, handler_available: bool = False) -> dict:
        payload = {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message": self.message,
            "error": self.error if include_result else _summarize_error(self.error),
            "has_error_detail": bool(self.error),
            "progress": self.progress,
            "retry_of": self.retry_of,
            "has_result": self.result is not None,
            "result_summary": _summarize_value(self.result),
            "request_summary": _summarize_value({"args": self.args, "kwargs": self.kwargs}),
            "can_cancel": self.status in CANCELABLE_STATUSES,
            "can_retry": self.status in RETRYABLE_STATUSES and handler_available,
        }
        if include_result:
            payload["result"] = self.result
        return payload


class BackgroundTaskRegistry:
    def __init__(
        self,
        max_workers: int = 2,
        storage_path: Optional[str | Path] = DEFAULT_TASK_STORAGE_PATH,
        max_history: int = 200,
    ):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="study-proj-task")
        self._tasks: Dict[str, TaskRecord] = {}
        self._futures: Dict[str, Future] = {}
        self._handlers: Dict[str, Callable[..., Any]] = {}
        self._lock = threading.Lock()
        self._storage_path = Path(storage_path) if storage_path else None
        self._max_history = max_history
        self._load_persisted()

    def register(self, kind: str, func: Callable[..., Any]) -> None:
        with self._lock:
            self._handlers[kind] = func

    def has_handler(self, kind: str) -> bool:
        with self._lock:
            return kind in self._handlers

    def submit(
        self,
        kind: str,
        func: Optional[Callable[..., Any]] = None,
        *args,
        retry_of: Optional[str] = None,
        **kwargs,
    ) -> TaskRecord:
        if func is None:
            with self._lock:
                func = self._handlers.get(kind)
        if func is None:
            raise ValueError(f"No task handler registered for {kind}")

        self.register(kind, func)
        task = TaskRecord(
            id=uuid.uuid4().hex[:12],
            kind=kind,
            status="queued",
            message="Task queued",
            progress=0,
            args=_json_safe(list(args)),
            kwargs=_json_safe(dict(kwargs)),
            retry_of=retry_of,
        )
        with self._lock:
            self._tasks[task.id] = task
            self._trim_locked()
            self._persist_locked()

        def runner():
            current = self.get(task.id)
            if not current or current.status == "canceled":
                return
            token = set_progress_reporter(
                lambda progress=None, message=None: self.update(task.id, progress=progress, message=message)
            )
            cancel_token = set_cancel_checker(lambda: self.is_cancel_requested(task.id))
            try:
                if self.is_cancel_requested(task.id):
                    self.update(task.id, status="canceled", message=f"{kind} canceled before start", progress=100)
                    return
                self.update(task.id, status="running", message=f"{kind} started", progress=5)
                result = func(*args, **kwargs)
                if self.is_cancel_requested(task.id):
                    self.update(task.id, status="canceled", message=f"{kind} canceled", progress=100)
                else:
                    self.update(task.id, status="succeeded", message=f"{kind} finished", result=result, progress=100)
            except Exception as exc:
                if self.is_cancel_requested(task.id):
                    self.update(task.id, status="canceled", message=f"{kind} canceled", progress=100)
                else:
                    self.update(
                        task.id,
                        status="failed",
                        message=f"{kind} failed",
                        error=f"{exc}\n{traceback.format_exc()}".strip(),
                        progress=100,
                    )
            finally:
                reset_cancel_checker(cancel_token)
                reset_progress_reporter(token)

        future = self._executor.submit(runner)
        with self._lock:
            self._futures[task.id] = future
        return task

    def retry(self, task_id: str) -> TaskRecord:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise KeyError(task_id)
            if task.status not in RETRYABLE_STATUSES:
                raise ValueError(f"Task {task_id} cannot be retried while status={task.status}")
            func = self._handlers.get(task.kind)
            if not func:
                raise ValueError(f"No task handler registered for {task.kind}")
            args = list(task.args)
            kwargs = dict(task.kwargs)
        return self.submit(task.kind, func, *args, retry_of=task.id, **kwargs)

    def cancel(self, task_id: str) -> Optional[TaskRecord]:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            if task.status not in CANCELABLE_STATUSES:
                return task

            future = self._futures.get(task_id)
            if task.status == "queued" and future and future.cancel():
                task.status = "canceled"
                task.message = f"{task.kind} canceled before start"
                task.progress = 100
            else:
                task.status = "cancel_requested"
                task.message = "Cancellation requested. Running Python work will stop when it reaches a safe boundary."
            task.updated_at = time.time()
            self._persist_locked()
            return task

    def is_cancel_requested(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            return bool(task and task.status == "cancel_requested")

    def update(
        self,
        task_id: str,
        *,
        status: Optional[str] = None,
        message: Optional[str] = None,
        result: Any = None,
        error: Optional[str] = None,
        progress: Optional[int] = None,
    ) -> Optional[TaskRecord]:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            if status is not None:
                task.status = status
            if message is not None:
                task.message = message
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            if progress is not None:
                task.progress = max(0, min(100, int(progress)))
            task.updated_at = time.time()
            self._trim_locked()
            self._persist_locked()
            return task

    def get(self, task_id: str) -> Optional[TaskRecord]:
        with self._lock:
            return self._tasks.get(task_id)

    def list(self) -> list[dict]:
        with self._lock:
            tasks = list(self._tasks.values())
            handlers = set(self._handlers)
        tasks.sort(key=lambda task: task.updated_at, reverse=True)
        return [task.to_dict(include_result=False, handler_available=task.kind in handlers) for task in tasks]

    def to_dict(self, task: TaskRecord, *, include_result: bool = True) -> dict:
        return task.to_dict(include_result=include_result, handler_available=self.has_handler(task.kind))

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)

    def _load_persisted(self) -> None:
        if not self._storage_path or not self._storage_path.exists():
            return
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except Exception:
            return

        now = time.time()
        records = payload.get("tasks", []) if isinstance(payload, dict) else []
        for item in records:
            if not isinstance(item, dict) or not item.get("id") or not item.get("kind"):
                continue
            status = item.get("status", "pending")
            message = item.get("message", "")
            error = item.get("error", "")
            updated_at = float(item.get("updated_at") or now)
            progress = int(item.get("progress", 0) or 0)
            if status in INTERRUPTIBLE_STATUSES:
                status = "interrupted"
                message = "Task was interrupted before API restart"
                error = error or "The API process stopped before this task reached a terminal state."
                updated_at = now
                progress = 100
            self._tasks[item["id"]] = TaskRecord(
                id=item["id"],
                kind=item["kind"],
                status=status,
                created_at=float(item.get("created_at") or updated_at),
                updated_at=updated_at,
                message=message,
                error=error,
                result=item.get("result"),
                progress=progress,
                args=list(item.get("args", [])),
                kwargs=dict(item.get("kwargs", {})),
                retry_of=item.get("retry_of"),
            )
        self._trim_locked()
        self._persist_locked()

    def _trim_locked(self) -> None:
        if self._max_history <= 0 or len(self._tasks) <= self._max_history:
            return
        keep = sorted(self._tasks.values(), key=lambda task: task.updated_at, reverse=True)[: self._max_history]
        self._tasks = {task.id: task for task in keep}

    def _persist_locked(self) -> None:
        if not self._storage_path:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        tasks = sorted(self._tasks.values(), key=lambda task: task.updated_at, reverse=True)
        payload = {
            "version": 1,
            "tasks": [task.to_dict(include_result=True) | {"args": task.args, "kwargs": task.kwargs} for task in tasks],
        }
        text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        tmp_path = self._storage_path.with_suffix(f"{self._storage_path.suffix}.tmp")
        tmp_path.write_text(text, encoding="utf-8")
        tmp_path.replace(self._storage_path)


registry = BackgroundTaskRegistry()
