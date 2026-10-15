"""Bounded spawn-process supervision. No coroutine cancellation assumptions.

The supervisor owns only the process it starts. Adapters must not launch
untracked child workers. Long lived browser/UIA session ownership comes in M2.
Tool execute/verify functions must be importable top-level callables on Windows.
"""

from __future__ import annotations

import math
import multiprocessing
import pickle
import threading
import time
from pathlib import Path
from typing import Any

from victus.safety.cancellation import CancellationController
from victus.tools.contracts import ActionRequest
from victus.tools.dispatcher import Dispatcher, DispatchOutcome
from victus.tools.registry import ToolRegistry, ToolSpec


def _worker(
    connection: Any, workspace: Path, spec: ToolSpec, action: ActionRequest, cancelled: Any
) -> None:
    try:
        registry = ToolRegistry()
        registry.register(spec)
        outcome = Dispatcher(workspace, registry).dispatch(action, cancelled)
        connection.send(outcome)
    except Exception:
        # Native exceptions can contain private arguments. Export only a code.
        connection.send(DispatchOutcome(status="unknown", error_code="WORKER_ERROR"))
    finally:
        connection.close()


class WorkerSupervisor:
    POLL_SECONDS = 0.02
    CANCEL_GRACE_SECONDS = 0.25
    TERMINATE_GRACE_SECONDS = 0.5

    def __init__(self, cancellation: CancellationController) -> None:
        self.cancellation = cancellation
        self.context = multiprocessing.get_context("spawn")
        self._lock = threading.Lock()
        self._process: Any = None

    @property
    def active_pid(self) -> int | None:
        with self._lock:
            return self._process.pid if self._process is not None else None

    def run(self, dispatcher: Dispatcher, action: ActionRequest) -> DispatchOutcome:
        spec = dispatcher.registry.get(action.tool)
        if not math.isfinite(spec.timeout_seconds) or spec.timeout_seconds <= 0:
            return DispatchOutcome(status="failed", error_code="INVALID_DEADLINE")
        try:
            # Reject closures before Windows creates even a partially started child.
            pickle.dumps((spec, action))
        except Exception:
            return DispatchOutcome(status="failed", error_code="WORKER_START_FAILED")
        receiving, sending = self.context.Pipe(duplex=False)
        signal = self.context.Event()
        process = self.context.Process(
            target=_worker,
            args=(sending, dispatcher.workspace, spec, action, signal),
            name="victus-action-worker",
            daemon=True,
        )
        started = False
        deadline = time.monotonic() + spec.timeout_seconds
        try:
            with self._lock:
                if self._process is not None:
                    return DispatchOutcome(status="failed", error_code="WORKER_BUSY")
                try:
                    started = self.cancellation.start(process.start, signal)
                except Exception:
                    return DispatchOutcome(status="failed", error_code="WORKER_START_FAILED")
                if not started:
                    return DispatchOutcome(status="cancelled", error_code="SERVICE_STOPPED")
                self._process = process
            sending.close()
            while True:
                if self.cancellation.stopped.is_set():
                    return self._interrupt(signal, "STOPPED_DURING_ACTION")
                if time.monotonic() >= deadline:
                    return self._interrupt(signal, "WORKER_DEADLINE_EXCEEDED")
                if receiving.poll(self.POLL_SECONDS):
                    try:
                        outcome = receiving.recv()
                    except (EOFError, OSError):
                        return DispatchOutcome(status="unknown", error_code="WORKER_EXITED")
                    if not isinstance(outcome, DispatchOutcome):
                        return DispatchOutcome(status="unknown", error_code="INVALID_WORKER_RESULT")
                    return outcome
                if not process.is_alive():
                    return DispatchOutcome(status="unknown", error_code="WORKER_EXITED")
        finally:
            if started:
                self._reap(process)
            receiving.close()
            sending.close()
            self.cancellation.finish(signal)
            with self._lock:
                if self._process is process:
                    self._process = None
            process.close()

    def _interrupt(self, signal: Any, code: str) -> DispatchOutcome:
        signal.set()
        # A worker can have changed the target already. Stop is not rollback.
        return DispatchOutcome(status="unknown", error_code=code)

    def _reap(self, process: Any) -> None:
        process.join(self.CANCEL_GRACE_SECONDS)
        if process.is_alive():
            process.terminate()
            process.join(self.TERMINATE_GRACE_SECONDS)
        if process.is_alive():
            process.kill()
            process.join(self.TERMINATE_GRACE_SECONDS)
        if process.is_alive():
            # The caller latches Stop and close() retains directory ownership.
            raise RuntimeError("Owned worker could not be stopped")
