from pathlib import Path
from threading import Event, Lock
from uuid import uuid4

from victus.storage.database import Database
from victus.tools.contracts import ActionRequest, TaskResult
from victus.tools.dispatcher import Dispatcher
from victus.tools.registry import ToolRegistry


class TaskService:
    def __init__(self, workspace: Path, database: Database, registry: ToolRegistry) -> None:
        self.workspace = workspace
        self.database = database
        self.registry = registry
        self.dispatcher = Dispatcher(workspace, registry)
        self.stopped = Event()
        self.mutation_lock = Lock()

    def stop(self) -> None:
        # This latches until process restart; it is not an automatic undo.
        self.stopped.set()

    def run(self, action: ActionRequest) -> TaskResult:
        result = TaskResult(task_id=uuid4().hex, tool=action.tool, status="prepared")
        self.database.save(result)
        with self.mutation_lock:
            if self.stopped.is_set():
                result.status = "cancelled"
                self.database.save(result)
                return result
            # Recheck stop at the dispatch boundary.
            if self.stopped.is_set():
                result.status = "cancelled"
                self.database.save(result)
                return result
            result.status = "running"
            self.database.save(result)
            outcome = self.dispatcher.dispatch(action)
            result.status = outcome.status
            result.verified = outcome.verified
            result.error_code = outcome.error_code
            result.output_name = outcome.output_name
            result.sha256 = outcome.sha256
            self.database.save(result)
            return result