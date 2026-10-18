import hashlib
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any

from victus.safety.policy import validate_action
from victus.tools.contracts import ActionRequest
from victus.tools.registry import ToolRegistry


class PostconditionFailed(ValueError):
    pass


def _is_graph_interrupt(error):
    # Graph execution already imports this class. A plain note must not load the
    # full planning stack merely to recognize its control-flow exception.
    import sys

    kind = getattr(sys.modules.get("langgraph.errors"), "GraphInterrupt", None)
    return kind is not None and isinstance(error, kind)


@dataclass(frozen=True)
class DispatchOutcome:
    """The observable result of a single action attempt."""

    status: str
    verified: bool = False
    error_code: str | None = None
    output_name: str | None = None
    sha256: str | None = None


class Dispatcher:
    """Owns validation, policy, adapter call, and verification for one action attempt.

    The caller (TaskService) is responsible for task identity, persistence, and
    the stop/cancellation latch. Workflow steps receive a trusted context for
    their ledger, payloads and audit trail; one owner serializes those steps.
    """

    def __init__(self, workspace: Path, registry: ToolRegistry) -> None:
        self.workspace = workspace
        self.registry = registry
        self._step_lock = None
        self._dispatch_barrier = RLock()

    def cancel_task(self, cancel):
        """Linearize the owner's cancellation latch with a dispatch commitment."""
        with self._dispatch_barrier:
            cancel()

    def _reject_review(self, context, *, cancelled=False):
        """A failed pre-dispatch check permanently retires this review attempt."""
        action_id = context.prepared_action_id
        if action_id is None or context.permits is None:
            return
        approvals = context.permits.approvals
        with approvals.connect() as db:
            now = approvals.now()
            approvals._expire(db, now)
            db.execute(
                "UPDATE approvals SET state='invalidated',updated_at=? "
                "WHERE task_id=? AND action_id=? AND state IN ('pending','approved')",
                (now, context.task_id, action_id),
            )
        record = context.ledger.get(action_id)
        if record is not None and record.status == "prepared":
            if cancelled:
                context.ledger.mark_cancelled(action_id)
            else:
                context.ledger.mark_failed(action_id, error_code="APPROVAL_OR_TARGET_STALE")

    def dispatch(self, action, cancelled: Any = None, *, authority=None) -> DispatchOutcome:
        """Owned-worker compatibility entry; all execution uses dispatch_step."""
        import asyncio
        from uuid import uuid4

        from victus.storage.action_ledger import ActionLedger
        from victus.storage.migrations import migrate
        from victus.storage.payloads import PayloadStore
        from victus.tasks.events import EventManager
        from victus.tools.steps import StepContext, WorkerAuthority

        resource_owned = authority is not None
        authority = authority or WorkerAuthority(uuid4().hex, None, frozenset({"fs:write"}))
        db_path = self.workspace.parent / "victus.sqlite3"
        if not db_path.exists():
            migrate(db_path)
        context = StepContext(
            task_id=authority.task_id,
            scopes=authority.scopes,
            authorize=lambda *_: True,
            ledger=ActionLedger(db_path),
            payloads=PayloadStore(db_path),
            events=EventManager(db_path),
            cancelled=cancelled,
            max_unreviewed_risk=authority.max_unreviewed_risk,
        )
        context.owned_action_id = authority.action_id
        # Supervisor/TaskQueue holds the process-wide slot for this entire worker.
        context.resource_owned = resource_owned
        context.emit_step_events = False  # TaskQueue owns public task lifecycle events.
        outcome = asyncio.run(self.dispatch_step(action, context))
        data = outcome.data
        code = (
            "WORKER_ERROR"
            if outcome.error_code == "STEP_POSTCONDITION_OR_EXECUTION_UNCERTAIN"
            else outcome.error_code
        )
        return DispatchOutcome(
            status="failed" if outcome.status == "blocked" else outcome.status,
            verified=outcome.verified,
            error_code=code,
            output_name=data.get("output_name"),
            sha256=data.get("sha256"),
        )

    async def dispatch_step(self, action, context):
        """One slot for task workers, deterministic workflows and planner actions."""
        import asyncio
        import math
        import time

        from victus.runtime.resources import ResourcePressure, resources
        from victus.tools.steps import StepOutcome

        if context.stopped():
            self._reject_review(context, cancelled=True)
            return StepOutcome("cancelled", error_code="SERVICE_STOPPED")
        try:
            # Reject forged envelopes/schema before any lock, ledger or adapter call.
            action, tool, arguments = self.registry.validate(action)
            self._policy(tool, arguments, context)
            if not math.isfinite(tool.timeout_seconds) or tool.timeout_seconds <= 0:
                return StepOutcome("blocked", error_code="INVALID_DEADLINE")
        except BaseException as error:
            if _is_graph_interrupt(error) or not isinstance(error, Exception):
                raise
            self._reject_review(context)
            code = (
                "TARGET_EXISTS"
                if isinstance(error, FileExistsError)
                else "POLICY_DENIED"
                if isinstance(error, PermissionError)
                else "STEP_VALIDATION_OR_POLICY_DENIED"
            )
            return StepOutcome("blocked", error_code=code)
        acquired = False
        deadline = min(context.deadline, time.monotonic() + tool.timeout_seconds)
        try:
            if not context.resource_owned:
                while True:
                    if context.stopped():
                        self._reject_review(context, cancelled=True)
                        return StepOutcome("cancelled", error_code="SERVICE_STOPPED")
                    if time.monotonic() >= deadline:
                        self._reject_review(context)
                        return StepOutcome("failed", error_code="STEP_DEADLINE_OR_STOP")
                    resources().check()
                    if resources().mutation.acquire(blocking=False):
                        acquired = True
                        break
                    await asyncio.sleep(0.01)
            return await self._dispatch_step(action, context, deadline)
        except ResourcePressure:
            self._reject_review(context)
            return StepOutcome("blocked", error_code="LOCAL_RESOURCE_PRESSURE")
        finally:
            if acquired:
                resources().mutation.release()

    def _policy(self, tool, arguments, context):
        from victus.safety.policy import validate_step

        validate_step(tool, arguments, context)
        if tool.policy is not None:
            tool.policy(self.workspace, arguments)
        elif tool.name == "fs.create_note":
            validate_action(ActionRequest(tool=tool.name, arguments=arguments), self.workspace)

    async def _dispatch_step(self, action, context, deadline):
        """Execute a typed workflow step through this registry/policy/ledger boundary.

        Construct in the supervised owner process. Async handlers stay on its loop;
        synchronous UIA handlers stay on its COM thread. Native hangs are terminated
        by the outer WorkerSupervisor, never assumed stopped by coroutine cancellation.
        """
        import asyncio
        import inspect
        import json
        import math
        import time

        from victus.safety.approvals import argument_hash
        from victus.storage.action_ledger import _canonical_hash
        from victus.tools.steps import StepOutcome

        if self._step_lock is None:
            self._step_lock = asyncio.Lock()
        async with self._step_lock:
            if context.stopped():
                self._reject_review(context, cancelled=True)
                return StepOutcome("cancelled", error_code="SERVICE_STOPPED")
            if (
                context.remaining_steps <= 0
                or not math.isfinite(context.deadline)
                or time.monotonic() >= context.deadline
            ):
                return StepOutcome("failed", error_code="WORKFLOW_BUDGET_EXHAUSTED")
            context.remaining_steps -= 1
            try:
                action, tool, arguments = self.registry.validate(action)
                self._policy(tool, arguments, context)
                if not math.isfinite(tool.timeout_seconds) or tool.timeout_seconds <= 0:
                    raise ValueError("Invalid deadline")
            except BaseException as error:
                if _is_graph_interrupt(error) or not isinstance(error, Exception):
                    raise
                self._reject_review(context)
                return StepOutcome("blocked", error_code="STEP_VALIDATION_OR_POLICY_DENIED")
            action_id = context.prepared_action_id or context.owned_action_id
            if action_id is not None:
                record = context.ledger.get(action_id)
                if (
                    record is None
                    or record.status != "prepared"
                    or record.tool_name != tool.name
                    or record.tool_version != tool.version
                    or record.expected_effect_ref != f"task:{context.task_id}"
                    or record.canonical_args_hash != _canonical_hash(arguments.model_dump())
                    or (
                        context.prepared_action_id is not None
                        and (context.permits is None or context.permit_token is None)
                    )
                    or (context.owned_action_id is not None and context.permits is not None)
                ):
                    return StepOutcome("blocked", error_code="APPROVAL_BINDING_INVALID")
            else:
                if context.permits is not None or context.permit_token is not None:
                    return StepOutcome("blocked", error_code="APPROVAL_BINDING_INVALID")
                action_id = context.ledger.prepare_action(
                    tool.name,
                    tool.version,
                    arguments.model_dump(),
                    expected_effect_ref=f"task:{context.task_id}",
                )
            context.payloads.store(
                action_id, "arguments", arguments.model_dump(), retention_hours=24
            )
            dispatched = False
            outcome = None
            try:
                if context.permits is not None:
                    try:
                        live = context.revalidate_binding()
                        if inspect.isawaitable(live):
                            live = await live
                        if (
                            live != context.approval_binding
                            or live.task_id != context.task_id
                            or live.action_id != action_id
                            or live.tool_name != tool.name
                            or live.tool_version != tool.version
                            or live.canonical_args_hash != argument_hash(arguments.model_dump())
                        ):
                            raise PermissionError("Target changed")
                    except (PermissionError, ValueError):
                        approval = context.permits.approvals
                        with approval.connect() as db:
                            db.execute(
                                "UPDATE approvals SET state='invalidated',updated_at=? "
                                "WHERE action_id=? AND state IN ('pending','approved')",
                                (approval.now(), action_id),
                            )
                        context.ledger.mark_failed(
                            action_id, error_code="TARGET_STALE_NEW_REVIEW_REQUIRED"
                        )
                        return StepOutcome(
                            "blocked", action_id, error_code="TARGET_STALE_NEW_REVIEW_REQUIRED"
                        )
                if context.stopped():
                    context.ledger.mark_cancelled(action_id)
                    outcome = StepOutcome("cancelled", action_id, error_code="SERVICE_STOPPED")
                else:
                    with self._dispatch_barrier:
                        if context.stopped():
                            context.ledger.mark_cancelled(action_id)
                            return StepOutcome("cancelled", action_id, error_code="SERVICE_STOPPED")
                        # Reacquire target/policy after waiting; no earlier check grants a lease.
                        self._policy(tool, arguments, context)
                        if context.permits is not None:
                            context.permits.consume_permit(
                                context.permit_token, live, cancelled=context.stopped
                            )
                        if context.stopped():
                            context.ledger.mark_cancelled(action_id)
                            return StepOutcome("cancelled", action_id, error_code="SERVICE_STOPPED")
                        if time.monotonic() >= deadline:
                            raise TimeoutError
                        context.ledger.mark_dispatching(action_id)
                        dispatched = True
                    async with asyncio.timeout(max(0, deadline - time.monotonic())):
                        # Durable intent can block on storage. Stop/deadline may
                        # have arrived during that I/O; do not enter the adapter.
                        if context.stopped() or time.monotonic() >= deadline:
                            raise TimeoutError
                        from victus.tools.steps import WorkerAuthority

                        output = (
                            tool.execute_owned(
                                self.workspace, arguments, context.cancelled,
                                WorkerAuthority(context.task_id, action_id, context.scopes,
                                                context.max_unreviewed_risk),
                            ) if tool.execute_owned is not None else
                            tool.execute_cancellable(self.workspace, arguments, context.cancelled)
                            if tool.execute_cancellable is not None
                            else tool.execute(self.workspace, arguments)
                        )
                        if inspect.isawaitable(output):
                            output = await output
                        if context.stopped() or time.monotonic() >= deadline:
                            raise TimeoutError
                        verification_output = output
                        if isinstance(output, Path):
                            if (
                                output.is_symlink()
                                or output.resolve().parent != self.workspace.resolve()
                                or (
                                    tool.name == "fs.create_note"
                                    and output.name != arguments.filename
                                )
                            ):
                                raise ValueError("Artifact outside workspace")
                            with output.open("rb") as stream:
                                contents = stream.read(128001)
                            if len(contents) > 128000:
                                raise ValueError("Artifact output limit")
                            output = {
                                "output_name": output.name,
                                "sha256": hashlib.sha256(contents).hexdigest(),
                            }
                        if not isinstance(output, dict):
                            raise TypeError("Workflow tool must return data, not live handles")
                        # Bound and validate the transport before returning it to workflow code.
                        encoded = json.dumps(output, ensure_ascii=True, allow_nan=False)
                        if len(encoded.encode("utf-8")) > 128_000:
                            raise ValueError("Step output limit")
                        context.ledger.mark_applied(
                            action_id, output_name=output.get("output_name")
                        )
                        verified = tool.verify(verification_output, arguments)
                        if inspect.isawaitable(verified):
                            verified = await verified
                        if context.stopped() or time.monotonic() >= deadline:
                            raise TimeoutError
                        if verified is not True:
                            raise PostconditionFailed("Postcondition not proved")
                        if isinstance(verification_output, Path):
                            if (
                                verification_output.is_symlink()
                                or verification_output.resolve().parent != self.workspace.resolve()
                            ):
                                raise PostconditionFailed(
                                    "Artifact target changed during verification"
                                )
                            with verification_output.open("rb") as stream:
                                reread = stream.read(128001)
                            if hashlib.sha256(reread).hexdigest() != output["sha256"]:
                                raise PostconditionFailed("Artifact changed during verification")
                        context.payloads.store(action_id, "output", output, retention_hours=24)
                        context.ledger.mark_verified(action_id, sha256=output.get("sha256"))
                        outcome = StepOutcome("succeeded", action_id, output)
            except BaseException as error:
                if _is_graph_interrupt(error):
                    raise
                if (
                    isinstance(error, PermissionError)
                    and not dispatched
                    and context.permits is not None
                ):
                    stopped = context.stopped()
                    code = "SERVICE_STOPPED" if stopped else "APPROVAL_OR_TARGET_STALE"
                    if stopped:
                        context.ledger.mark_cancelled(action_id)
                    else:
                        context.ledger.mark_failed(action_id, error_code=code)
                    outcome = StepOutcome(
                        "cancelled" if stopped else "blocked", action_id, error_code=code
                    )
                    return outcome
                code = (
                    "POSTCONDITION_FAILED"
                    if isinstance(error, PostconditionFailed)
                    else "TARGET_EXISTS"
                    if isinstance(error, FileExistsError) and not dispatched
                    else "STEP_DEADLINE_OR_STOP"
                    if isinstance(error, (TimeoutError, asyncio.CancelledError))
                    else "STEP_POSTCONDITION_OR_EXECUTION_UNCERTAIN"
                )
                if dispatched:
                    context.ledger.mark_unknown(action_id, error_code=code)
                else:
                    context.ledger.mark_failed(action_id, error_code=code)
                outcome = StepOutcome(
                    "unknown" if dispatched else "failed", action_id, error_code=code
                )
                if isinstance(error, (KeyboardInterrupt, SystemExit, asyncio.CancelledError)):
                    raise
            finally:
                if outcome is not None:
                    safe = {
                        "tool": tool.name,
                        "action_id": action_id,
                        "status": outcome.status,
                        "error_code": outcome.error_code,
                    }
                    context.trace.append(safe)
                    if context.emit_step_events:
                        context.events.record_event(context.task_id, "workflow.step", safe)
            return outcome
