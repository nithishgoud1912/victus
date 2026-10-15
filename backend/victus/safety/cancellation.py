"""Emergency latch and atomic dispatch barrier, independent of planning."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


class CancellationController:
    def __init__(self) -> None:
        self.stopped = threading.Event()
        self._barrier = threading.Lock()
        self._active_signal: Any = None

    def start(self, start_worker: Callable[[], None], signal: Any) -> bool:
        """Linearize process launch with Stop; never hold this lock during work."""
        with self._barrier:
            if self.stopped.is_set():
                return False
            start_worker()
            self._active_signal = signal
            return True

    def finish(self, signal: Any) -> None:
        with self._barrier:
            if self._active_signal is signal:
                self._active_signal = None

    def stop(self) -> None:
        with self._barrier:
            self.stopped.set()
            if self._active_signal is not None:
                self._active_signal.set()
