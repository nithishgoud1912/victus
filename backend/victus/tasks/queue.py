"""Task queue with capacity limits, single active worker, and client request deduplication.

Enforces:
- At most 3 queued tasks; rejects additional submissions with QueueFullError.
- Exactly 1 active task running in a supervised background worker.
- Deduplication via client_request_id persisted to SQLite.
- Immediate cancellation and draining of queued work when stopped.
"""

from __future__ import annotations

import json
import queue
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from victus.runtime.locks import MutationLocks
from victus.runtime.resources import resources
from victus.runtime.supervisor import WorkerSupervisor
from victus.safety.cancellation import CancellationController
from victus.storage.action_ledger import ActionLedger
from victus.storage.database import Database
from victus.tasks.events import EventManager
from victus.tools.contracts import ActionRequest, TaskResult
from victus.tools.dispatcher import Dispatcher
from victus.tools.registry import ToolRegistry


class QueueFullError(Exception):
    """Raised when the task queue exceeds its maximum capacity."""


class TaskQueue:
    """Manages task scheduling with capacity limits and a supervised worker."""

    MAX_QUEUED = 3

    def __init__(
        self,
        workspace: Path,
        database: Database,
        registry: ToolRegistry,
        events: EventManager,
        *,
        cancellation: CancellationController | None = None,
        locks: MutationLocks | None = None,
    ) -> None:
        self.workspace = workspace
        self.database = database
        self.registry = registry
        self.events = events
        self.dispatcher = Dispatcher(workspace, registry)
        self.cancellation = cancellation or CancellationController()
        self.stopped = self.cancellation.stopped
        self.mutation_lock = (locks or MutationLocks()).mutation
        self.supervisor = WorkerSupervisor(self.cancellation)
        self.ledger = ActionLedger(database.path)

        # Queue allows at most MAX_QUEUED pending items.
        self._queue: queue.Queue[tuple[str, ActionRequest]] = queue.Queue(maxsize=self.MAX_QUEUED)
        self._active_task_id: str | None = None
        self._active_lock = threading.Lock()
        self._admission_lock = threading.RLock()

        # Start the single supervised background worker thread.
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="victus-task-worker",
            daemon=True,
        )
        self._worker_thread.start()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.database.path, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def get_by_client_request_id(self, client_request_id: str) -> str | None:
        """Return the task_id mapped to *client_request_id*, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT task_id FROM client_requests WHERE client_request_id = ?",
                (client_request_id,),
            ).fetchone()
            return row["task_id"] if row else None

    @property
    def active_task_id(self) -> str | None:
        """The task_id currently being executed by the worker, if any."""
        with self._active_lock:
            return self._active_task_id

    @property
    def queued_count(self) -> int:
        """Number of tasks currently waiting in the queue."""
        return self._queue.qsize()

    def submit(
        self,
        action: ActionRequest,
        client_request_id: str | None = None,
    ) -> tuple[str, bool]:
        """Submit a task to the queue.

        Returns (task_id, newly_enqueued).
        If client_request_id matches an existing request, returns (existing_task_id, False).
        Raises QueueFullError if the queue is at capacity.
        """
        with self._admission_lock:
            return self._submit_locked(action, client_request_id)

    def _submit_locked(
        self, action: ActionRequest, client_request_id: str | None
    ) -> tuple[str, bool]:
        if client_request_id:
            existing = self.get_by_client_request_id(client_request_id)
            if existing:
                return (existing, False)

        stopped = self.stopped.is_set()
        if not stopped:
            resources().check()
            resources().check_disk(self.workspace)
        if not stopped and self._queue.full():
            raise QueueFullError(f"Task queue is full (maximum {self.MAX_QUEUED} queued tasks)")
        task_id = uuid4().hex
        result = TaskResult(
            task_id=task_id,
            tool=action.tool,
            status="cancelled" if stopped else "queued",
            error_code="SERVICE_STOPPED" if stopped else None,
        )
        # Commit all admission metadata before exposing work to the scheduler.
        with self.database.connect() as conn:
            conn.execute(
                "INSERT INTO tasks (task_id, result_json) VALUES (?, ?)",
                (task_id, result.model_dump_json()),
            )
            if client_request_id:
                conn.execute(
                    "INSERT INTO client_requests (client_request_id, task_id) VALUES (?, ?)",
                    (client_request_id, task_id),
                )
            conn.execute(
                "INSERT INTO task_events (task_id, event_type, safe_payload) VALUES (?, ?, ?)",
                (task_id, f"task.{result.status}", json.dumps({"tool": action.tool})),
            )
        if not stopped:
            self._queue.put_nowait((task_id, action))
        return (task_id, True)

    def _worker_loop(self) -> None:
        """Supervised worker that pulls one task at a time from the queue."""
        while True:
            try:
                item = self._queue.get(timeout=0.05)
            except queue.Empty:
                if self.stopped.is_set():
                    break
                continue

            task_id, action = item
            with self._active_lock:
                self._active_task_id = task_id

            try:
                self._execute_task(task_id, action)
            except Exception:
                # Fallback in case of unexpected worker error
                task = self.database.get(task_id) or TaskResult(
                    task_id=task_id, tool=action.tool, status="unknown"
                )
                task.status = "unknown"
                task.error_code = "WORKER_ERROR"
                if self.supervisor.active_pid is not None:
                    self.cancellation.stop()
                if task.action_id is not None:
                    record = self.ledger.get(task.action_id)
                    if record and record.status in {"dispatching", "applied"}:
                        self.ledger.mark_unknown(task.action_id, error_code="WORKER_ERROR")
                self.database.save(task)
                self.events.record_event(
                    task_id,
                    "task.unknown",
                    {"error_code": task.error_code},
                )
            finally:
                with self._active_lock:
                    self._active_task_id = None
                self._queue.task_done()

    def _execute_task(self, task_id: str, action: ActionRequest) -> None:
        """Run a single task attempt with stop checks and event tracking."""
        task = self.database.get(task_id) or TaskResult(
            task_id=task_id, tool=action.tool, status="queued"
        )

        if self.stopped.is_set():
            task.status = "cancelled"
            self.database.save(task)
            self.events.record_event(task_id, "task.cancelled", {"reason": "service_stopped"})
            return

        acquired = False
        while not self.stopped.is_set():
            if self.mutation_lock.acquire(timeout=0.05):
                acquired = True
                break
        try:
            if self.stopped.is_set():
                task.status = "cancelled"
                self.database.save(task)
                self.events.record_event(task_id, "task.cancelled", {"reason": "service_stopped"})
                return

            task.status = "running"
            self.database.save(task)
            self.events.record_event(task_id, "task.started", {"tool": action.tool})

            # Recheck stop right at the dispatch boundary
            if self.stopped.is_set():
                task.status = "cancelled"
                self.database.save(task)
                self.events.record_event(task_id, "task.cancelled", {"reason": "service_stopped"})
                return

            spec = self.dispatcher.registry.get(action.tool)
            task.action_id = self.ledger.prepare_action(
                spec.name,
                spec.version,
                action.arguments.model_dump(),
                expected_effect_ref=f"task:{task_id}",
            )
            self.database.save(task)
            self.ledger.mark_dispatching(task.action_id)
            outcome = self.supervisor.run(self.dispatcher, action)
            if outcome.status == "succeeded":
                self.ledger.mark_applied(task.action_id, output_name=outcome.output_name)
                self.ledger.mark_verified(task.action_id, sha256=outcome.sha256)
            elif outcome.status == "cancelled":
                self.ledger.mark_cancelled(task.action_id)
            elif outcome.status == "failed":
                self.ledger.mark_failed(task.action_id, error_code=outcome.error_code)
            else:
                self.ledger.mark_unknown(task.action_id, error_code=outcome.error_code)
            task.status = outcome.status
            task.verified = outcome.verified
            task.error_code = outcome.error_code
            task.output_name = outcome.output_name
            task.sha256 = outcome.sha256
            self.database.save(task)

            self.events.record_event(
                task_id,
                f"task.{outcome.status}",
                {
                    "tool": action.tool,
                    "verified": outcome.verified,
                    "error_code": outcome.error_code,
                    "output_name": outcome.output_name,
                    "sha256": outcome.sha256,
                },
            )
        finally:
            if acquired:
                self.mutation_lock.release()

    def stop(self) -> None:
        # Close the dispatch barrier before waiting for admission/storage locks.
        self.cancellation.stop()
        with self._admission_lock:
            self._stop_locked()

    def close(self) -> None:
        self.stop()
        self._worker_thread.join(timeout=10)
        if self._worker_thread.is_alive() or self.supervisor.active_pid is not None:
            raise RuntimeError("Worker shutdown incomplete; retain data-directory ownership")

    def _stop_locked(self) -> None:
        """Stop worker, cancel queued work, and drain the queue."""
        self.cancellation.stop()

        # Drain and cancel all pending items waiting in the queue
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break

            if item is not None:
                task_id, action = item
                task = self.database.get(task_id) or TaskResult(
                    task_id=task_id, tool=action.tool, status="cancelled"
                )
                task.status = "cancelled"
                self.database.save(task)
                self.events.record_event(task_id, "task.cancelled", {"reason": "service_stopped"})
            self._queue.task_done()
