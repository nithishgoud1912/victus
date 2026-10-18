"""Task entry points share one queue, cancellation barrier and mutation slot."""

import time
from pathlib import Path

from victus.runtime.locks import MutationLocks
from victus.safety.cancellation import CancellationController
from victus.storage.database import Database
from victus.tasks.events import EventManager
from victus.tasks.queue import TaskQueue
from victus.tools.contracts import ActionRequest, TaskResult, ToolRequest
from victus.tools.registry import RiskLevel, ToolRegistry
from victus.workflows.common import new_destination
from victus.workflows.contracts import (
    NOTEPAD_CHECKLIST_TOOL,
    NotepadChecklistSubmission,
    WorkflowUnavailable,
)


class TaskService:
    def __init__(
        self,
        workspace: Path,
        database: Database,
        registry: ToolRegistry,
        events: EventManager | None = None,
        *,
        scopes=frozenset({"fs:write"}),
        max_unreviewed_risk=RiskLevel.LOW,
        qualified_notepad_profiles: frozenset[str] = frozenset(),
        reviewed_notepad_profiles: frozenset[str] = frozenset(),
    ) -> None:
        self.workspace = workspace
        self.database = database
        self.registry = registry
        # Trusted server wiring only. Bootstrap deliberately supplies none until
        # native qualification AND exact-action review integration pass.
        self.qualified_notepad_profiles = frozenset(qualified_notepad_profiles)
        self.reviewed_notepad_profiles = frozenset(reviewed_notepad_profiles)
        self.research = None
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
            scopes=scopes,
            max_unreviewed_risk=max_unreviewed_risk,
        )
        self.dispatcher = self.queue.dispatcher

    def stop(self) -> None:
        self.queue.stop()
        from victus.recovery.resume import ResumeManager
        from victus.safety.approvals import ApprovalStore
        from victus.storage.action_ledger import ActionLedger

        ResumeManager(ActionLedger(self.database.path), ApprovalStore(self.database.path)).invalidate()

    def close(self) -> None:
        self.queue.close()

    def enqueue(
        self, action: ToolRequest | ActionRequest, client_request_id: str | None = None
    ) -> tuple[str, bool]:
        if action.tool in self.registry.names() and not self.registry.get(action.tool).public:
            raise ValueError("Internal workflow transport is not a public tool")
        if action.tool == NOTEPAD_CHECKLIST_TOOL:
            return self.enqueue_notepad(
                NotepadChecklistSubmission.model_validate(action.arguments, strict=True),
                client_request_id,
            )
        from victus.workflows.contracts import BROWSER_RESEARCH_TOOL, BrowserResearchSubmission
        if action.tool == BROWSER_RESEARCH_TOOL:
            return self.enqueue_research(BrowserResearchSubmission.model_validate(action.arguments, strict=True), client_request_id)
        return self.queue.submit(action, client_request_id)

    def enqueue_research(self, submission, client_request_id=None):
        from victus.workflows.contracts import BROWSER_RESEARCH_TOOL, BrowserResearchSubmission

        submission = BrowserResearchSubmission.model_validate(submission.model_dump(), strict=True)
        with self.queue._admission_lock:
            if client_request_id:
                original = self.queue.get_by_client_request_id(client_request_id)
                if original:
                    return original, False
            if self.research is None or BROWSER_RESEARCH_TOOL not in self.registry.names():
                raise WorkflowUnavailable('Qualified fixture browser prerequisite unavailable')
            if not Path(self.research.browser_executable).is_file():
                raise WorkflowUnavailable('Qualified browser is not installed')
            return self.queue.submit(ToolRequest(tool=BROWSER_RESEARCH_TOOL, arguments=submission.model_dump()),
                client_request_id, pre_admission=lambda: new_destination(self.workspace, submission.filename))

    def run(self, action: ToolRequest | ActionRequest) -> TaskResult:
        """Compatibility entry point; never bypass supervised queued execution."""
        task_id, _ = self.enqueue(action)
        while True:
            result = self.database.get(task_id)
            if result is not None and result.status not in {"queued", "prepared", "running", "waiting_for_review"}:
                return result
            if not self.queue._worker_thread.is_alive():
                raise RuntimeError("Task scheduler exited before recording a result")
            time.sleep(0.02)

    def enqueue_notepad(
        self, submission: NotepadChecklistSubmission, client_request_id: str | None = None
    ) -> tuple[str, bool]:
        submission = NotepadChecklistSubmission.model_validate(submission.model_dump(), strict=True)
        with self.queue._admission_lock:
            if client_request_id:
                original = self.queue.get_by_client_request_id(client_request_id)
                if original:
                    return original, False
            return self._enqueue_notepad_new(submission, client_request_id)

    def _enqueue_notepad_new(self, submission, client_request_id):
        if (not self.qualified_notepad_profiles or not self.reviewed_notepad_profiles
            or NOTEPAD_CHECKLIST_TOOL not in self.registry.names()):
            raise WorkflowUnavailable("Notepad workflow requires native qualification and review")
        if submission.profile not in self.qualified_notepad_profiles.intersection(self.reviewed_notepad_profiles):
            raise ValueError("Unsupported Notepad profile")
        action = ToolRequest(tool=NOTEPAD_CHECKLIST_TOOL, arguments=submission.model_dump())
        # The queue checks deduplication first under the admission lock: replaying
        # a successful request must still return its original task after file creation.
        return self.queue.submit(
            action, client_request_id,
            pre_admission=lambda: new_destination(self.workspace, submission.filename),
        )
