"""Task entry points share one queue, cancellation barrier and mutation slot."""

import time
from pathlib import Path

from victus.runtime.locks import MutationLocks
from victus.safety.cancellation import CancellationController
from victus.storage.database import Database
from victus.tasks.events import EventManager
from victus.tasks.queue import TaskQueue
from victus.tools.contracts import ActionRequest, TaskResult
from victus.tools.registry import ToolRegistry


class TaskService:
    def __init__(
        self,
        workspace: Path,
        database: Database,
        registry: ToolRegistry,
        events: EventManager | None = None,
    ) -> None:
        self.workspace = workspace
        self.database = database
        self.registry = registry
        self.cancellation = CancellationController()
        self.locks = MutationLocks()
        self.stopped = self.cancellation.stopped
        self.mutation_lock = self.locks.mutation
        self.events = events if events is not None else EventManager(database.path)
        self.queue = TaskQueue(
            workspace,
            database,
            registry,
            self.events,
            cancellation=self.cancellation,
            locks=self.locks,
        )
        self.dispatcher = self.queue.dispatcher

    def stop(self) -> None:
        self.queue.stop()

    def close(self) -> None:
        self.queue.close()

    def enqueue(
        self, action: ActionRequest, client_request_id: str | None = None
    ) -> tuple[str, bool]:
        return self.queue.submit(action, client_request_id)

    def run(self, action: ActionRequest) -> TaskResult:
        """Compatibility entry point; never bypass supervised queued execution."""
        task_id, _ = self.enqueue(action)
        while True:
            result = self.database.get(task_id)
            if result is not None and result.status not in {"queued", "prepared", "running"}:
                return result
            if not self.queue._worker_thread.is_alive():
                raise RuntimeError("Task scheduler exited before recording a result")
            time.sleep(0.02)
