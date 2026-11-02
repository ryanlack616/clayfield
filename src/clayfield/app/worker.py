"""Reusable Qt worker infrastructure for CPU-bound operations."""

from __future__ import annotations

from collections.abc import Callable
from threading import Event
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot
from clayfield.app.cancellation import WorkerCancelled


class WorkerSignals(QObject):
    """Signals emitted by a background operation."""

    started = Signal()
    progress = Signal(int, str)
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()


class FunctionWorker(QRunnable):
    """Run a callable on Qt's global thread pool."""

    def __init__(self, function: Callable[..., Any], *args: Any, inject_control: bool = False, **kwargs: Any) -> None:
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.inject_control = inject_control
        self._cancel_event = Event()
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    def cancel(self) -> None:
        """Request cancellation at the next cooperative checkpoint."""
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        """Return whether cancellation has been requested."""
        return self._cancel_event.is_set()

    @Slot()
    def run(self) -> None:
        self.signals.started.emit()
        try:
            if self.inject_control:
                result = self.function(
                    *self.args,
                    cancel_check=self.is_cancelled,
                    progress_callback=self.signals.progress.emit,
                    **self.kwargs,
                )
            else:
                result = self.function(*self.args, **self.kwargs)
        except WorkerCancelled:
            self.signals.cancelled.emit()
            return
        except Exception as error:  # noqa: BLE001 - forwarded through the signal boundary
            self.signals.failed.emit(str(error))
            return
        self.signals.finished.emit(result)
