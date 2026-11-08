"""Shared application context: settings, history, status bus and background task runner."""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from src.core.history_manager import HistoryManager
from src.core.settings import Settings
from src.utils.progress import OperationCancelled

log = logging.getLogger("cipherlab.gui")


class StatusBus(QObject):
    """Signals consumed by the main window's status bar."""

    message = Signal(str)
    counts = Signal(int, int)      # bytes, characters
    progress = Signal(int, str)    # percent (-1 = indeterminate, -2 = finished), message


class _WorkerSignals(QObject):
    finished = Signal(int, object)
    failed = Signal(int, str)
    progress = Signal(int, int, str)


class Worker(QRunnable):
    """Runs ``fn(progress, cancel)`` on the global thread pool."""

    def __init__(self, task_id: int, fn: Callable[[Callable[[int, str], None], Callable[[], bool]], Any]):
        super().__init__()
        self.setAutoDelete(False)
        self.task_id, self.fn = task_id, fn
        self.signals = _WorkerSignals()
        self.cancel_event = threading.Event()

    def run(self) -> None:  # executes in a worker thread
        try:
            result = self.fn(lambda p, m: self.signals.progress.emit(self.task_id, p, m), self.cancel_event.is_set)
        except OperationCancelled:
            self.signals.failed.emit(self.task_id, "Cancelled.")
        except Exception as exc:  # noqa: BLE001 - shown to the user; content is never logged
            log.debug("task failed: %s", type(exc).__name__)
            self.signals.failed.emit(self.task_id, str(exc) or type(exc).__name__)
        else:
            self.signals.finished.emit(self.task_id, result)


class TaskRunner(QObject):
    """Submits Workers and delivers results back on the GUI thread (via queued slots)."""

    def __init__(self, bus: StatusBus):
        super().__init__()
        self._bus = bus
        self._tasks: dict[int, tuple[Worker, Callable, Optional[Callable]]] = {}
        self._next = 1

    def submit(self, fn, on_done: Callable[[Any], None], on_error: Optional[Callable[[str], None]] = None) -> None:
        tid, self._next = self._next, self._next + 1
        worker = Worker(tid, fn)
        self._tasks[tid] = (worker, on_done, on_error)
        worker.signals.finished.connect(self._finished)
        worker.signals.failed.connect(self._failed)
        worker.signals.progress.connect(self._progress)
        self._bus.progress.emit(-1, "Working…")
        QThreadPool.globalInstance().start(worker)

    def cancel_all(self) -> None:
        for worker, _, _ in self._tasks.values():
            worker.cancel_event.set()

    @property
    def busy(self) -> bool:
        return bool(self._tasks)

    def _pop(self, tid: int):
        entry = self._tasks.pop(tid, None)
        if not self._tasks:
            self._bus.progress.emit(-2, "")
        return entry

    @Slot(int, object)
    def _finished(self, tid: int, result: object) -> None:
        entry = self._pop(tid)
        if entry:
            entry[1](result)

    @Slot(int, str)
    def _failed(self, tid: int, message: str) -> None:
        entry = self._pop(tid)
        if entry and entry[2]:
            entry[2](message)

    @Slot(int, int, str)
    def _progress(self, tid: int, percent: int, message: str) -> None:
        if tid in self._tasks:
            self._bus.progress.emit(percent, message)


@dataclass
class AppContext:
    settings: Settings
    history: HistoryManager
    bus: StatusBus = field(default_factory=StatusBus)
    runner: Optional[TaskRunner] = None
    send_to_compare: Callable[[list], None] = lambda candidates: None
    set_language: Callable[[str], None] = lambda lang: None
    set_theme: Callable[[str], None] = lambda name: None

    def __post_init__(self) -> None:
        if self.runner is None:
            self.runner = TaskRunner(self.bus)

    def apply_settings(self) -> None:
        """Push settings into live objects (history manager)."""
        s = self.settings
        self.history.enabled = s.history_enabled
        self.history.store_previews = s.history_store_previews
        self.history.max_records = s.max_history_records
