from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Callable, Optional

ProgressReporter = Callable[[Optional[int], Optional[str]], None]
CancelChecker = Callable[[], bool]

_current_reporter: ContextVar[Optional[ProgressReporter]] = ContextVar("current_progress_reporter", default=None)
_current_cancel_checker: ContextVar[Optional[CancelChecker]] = ContextVar("current_cancel_checker", default=None)


class TaskCancellationRequested(RuntimeError):
    """Raised by long-running jobs when the web task has been canceled."""


def set_progress_reporter(reporter: ProgressReporter) -> Token:
    return _current_reporter.set(reporter)


def reset_progress_reporter(token: Token) -> None:
    _current_reporter.reset(token)


def set_cancel_checker(checker: Optional[CancelChecker]) -> Token:
    return _current_cancel_checker.set(checker)


def reset_cancel_checker(token: Token) -> None:
    _current_cancel_checker.reset(token)


def report_progress(progress: Optional[int] = None, message: Optional[str] = None) -> None:
    reporter = _current_reporter.get()
    if reporter:
        reporter(progress, message)


def is_cancel_requested() -> bool:
    checker = _current_cancel_checker.get()
    return bool(checker and checker())


def raise_if_cancel_requested() -> None:
    if is_cancel_requested():
        raise TaskCancellationRequested("Task cancellation requested")
