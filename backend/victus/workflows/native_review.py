"""Bounded review inside the existing owner worker. No native handle leaves it."""

import asyncio
import hashlib
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from victus.adapters.uia.applications import ApplicationReference, UIAWorker, load_profiles
from victus.adapters.uia.selectors import ControlReference
from victus.recovery.resume import ResumeManager
from victus.safety.approvals import ApprovalBinding, ApprovalStore, argument_hash
from victus.safety.permits import PermitStore
from victus.storage.database import Database
from victus.tools.dispatcher import Dispatcher
from victus.tools.registry import RetryClass, RiskLevel, ToolRegistry, ToolSpec
from victus.workflows.common import bytes_match, context_for, new_destination
from victus.workflows.contracts import NOTEPAD_CHECKLIST_TOOL, NotepadChecklistSubmission
from victus.workflows.create_notepad_checklist import ChecklistRequest, NotepadTools
from victus.workflows.qualification_records import runtime_identity


class NativeSaveReview:
    def __init__(self, tools, context, registry, *, ttl=60):
        if not 0 < ttl <= 60:
            raise ValueError("Native review must be bounded to 60 seconds")
        self.tools, self.context, self.registry, self.ttl = tools, context, registry, ttl
        self.approvals = ApprovalStore(context.ledger.db_path)
        self.store = Database.attach(tools._workspace.parent)

    def binding(self, args, action_id):
        tools = self.tools
        owned = tools.worker._resolve_app(ApplicationReference(args.app_ref))
        identities = []
        for reference, read_only in (
            (tools.editor_ref, True),
            (args.filename_ref, False),
            (args.save_ref, False),
        ):
            _, root, control = tools.resolver._reacquire(
                ControlReference(reference), read_only=read_only
            )
            identities.append(
                [list(root.element_info.runtime_id), list(control.element_info.runtime_id)]
            )
        if tools._read(tools.editor_ref) != tools.text:
            raise PermissionError("Editor content changed")
        destination = new_destination(tools._workspace, tools.request.filename)
        parent = destination.parent.stat()
        tool = self.registry.get("uia.save_checklist")
        identity = argument_hash(
            {
                "profile": owned.profile.name,
                "process": asdict(owned.identity),
                "controls": identities,
                "editor_tab": list(owned.editor_tab_identity)
                if owned.editor_tab_identity
                else None,
                "editor_window": list(owned.editor_window_identity)
                if owned.editor_window_identity
                else None,
                "destination": str(destination.resolve()),
                "parent": [parent.st_dev, parent.st_ino],
                "payload": hashlib.sha256(tools.expected).hexdigest(),
                "request": tools.request.model_dump(),
            }
        )
        return ApprovalBinding(
            task_id=self.context.task_id,
            action_id=action_id,
            tool_name=tool.name,
            tool_version=tool.version,
            canonical_args_hash=argument_hash(args.model_dump()),
            policy_version="native-save-v2",
            target_identity="native:" + identity,
            observation_identity=identity,
        )

    async def __call__(self, args):
        context, tools = self.context, self.tools
        action = context.ledger.prepare_action(
            "uia.save_checklist",
            self.registry.get("uia.save_checklist").version,
            args.model_dump(),
            expected_effect_ref=f"task:{context.task_id}",
        )
        binding = self.binding(args, action)
        record = self.approvals.request(
            binding,
            {
                "action": "Save new Notepad checklist",
                "profile": tools.request.profile,
                "destination": str((tools._workspace / tools.request.filename).resolve()),
                "text": tools.text,
                "encoding": tools.request.encoding,
                "payload_sha256": hashlib.sha256(tools.expected).hexdigest(),
            },
            ttl_seconds=self.ttl,
        )
        task = self.store.get(context.task_id)
        if task is None:
            self.approvals.invalidate(record.approval_id)
            raise PermissionError("Owned task is unavailable")
        task.status, task.approval_id = "waiting_for_review", record.approval_id
        self.store.save(
            task,
            event_type="approval.required",
            event_payload={
                "approval_id": record.approval_id,
                "action_id": action,
                "expires_at": record.expires_at,
            },
        )
        try:
            while True:
                if context.stopped() or time.monotonic() >= context.deadline:
                    raise PermissionError("Review cancelled or timed out")
                current = self.approvals.get(record.approval_id)
                if current is None or current.state not in {"pending", "approved"}:
                    raise PermissionError("Review denied, expired or invalidated")
                if current.state == "approved":
                    break
                await asyncio.sleep(0.05)
            if self.binding(args, action) != binding:
                raise PermissionError("Native target changed; new review required")
            permits = PermitStore(self.approvals)
            token = permits.issue(record.approval_id, binding)

            def consumed_guard():
                current = self.approvals.get(record.approval_id)
                if (
                    context.stopped()
                    or current is None
                    or current.state != "consumed"
                    or self.approvals.now() >= current.expires_at
                    or self.binding(args, action) != binding
                    or tools._read(args.filename_ref)
                    != str(tools._workspace / tools.request.filename)
                ):
                    raise PermissionError("Native Save authority changed")

            tools.review_guard = consumed_guard
            task.status = "running"
            self.store.save(
                task,
                event_type="approval.resolved",
                event_payload={"approval_id": record.approval_id, "state": "approved"},
            )
            return replace(
                context,
                prepared_action_id=action,
                owned_action_id=None,
                permits=permits,
                permit_token=token,
                approval_binding=binding,
                revalidate_binding=lambda: self.binding(args, action),
                review_save=None,
            )
        except BaseException:
            self.approvals.invalidate(record.approval_id)
            entry = context.ledger.get(action)
            if entry.status == "prepared":
                context.ledger.mark_cancelled(action)
            raise


async def reviewed_checklist(workspace, submission, cancelled, authority, worker, *, ttl=60):
    """Shared native/fake integration; worker and task identity are server-owned."""
    request = ChecklistRequest(**submission.model_dump())
    tools = NotepadTools(worker, request, workspace)
    registry = ToolRegistry()
    tools.register(registry)
    context = context_for(
        workspace,
        authority.task_id,
        cancelled,
        {
            "desktop:launch",
            "desktop:read",
            "desktop:interact",
            "filesystem:save",
            "filesystem:read",
        },
        tools.authorize,
    )
    context.resource_owned = True  # Outer supervised owner holds the slot while reviewing.
    context.review_save = NativeSaveReview(tools, context, registry, ttl=ttl)
    from victus.workflows.create_notepad_checklist import create_notepad_checklist

    try:
        result = await create_notepad_checklist(Dispatcher(workspace, registry), context, request)
        if result.status != "succeeded":
            raise RuntimeError("Native workflow result is unverified")
        return workspace / submission.filename
    finally:
        ResumeManager(context.ledger, ApprovalStore(context.ledger.db_path)).invalidate(
            context.task_id
        )


@dataclass(frozen=True)
class NativeChecklistExecutor:
    profiles_file: str
    profiles_sha256: str
    profiles: frozenset[str]
    runtime_sha256: str

    async def __call__(self, workspace, submission, cancelled, authority):
        path = Path(self.profiles_file)
        if (
            runtime_identity() != self.runtime_sha256
            or submission.profile not in self.profiles
            or path.is_symlink()
            or hashlib.sha256(path.read_bytes()).hexdigest() != self.profiles_sha256
        ):
            raise PermissionError("Qualified native profile changed")
        with UIAWorker(load_profiles(path)) as worker:
            return await reviewed_checklist(workspace, submission, cancelled, authority, worker)


def verify_native_checklist(path, submission):
    return bytes_match(
        path, ChecklistRequest(**submission.model_dump()).editor_text().encode("utf-8")
    )


def reject_unowned(*_):
    raise PermissionError("Owned native execution required")


def native_checklist_spec(profiles_file, profiles, *, native_qualified, review_qualified):
    """Trusted registration only. Neither qualification assertion is a public input."""
    if native_qualified is not True or review_qualified is not True or not profiles:
        raise PermissionError("Native and review qualification both required")
    path = Path(profiles_file).resolve(strict=True)
    executor = NativeChecklistExecutor(
        str(path),
        hashlib.sha256(path.read_bytes()).hexdigest(),
        frozenset(profiles),
        runtime_identity(),
    )
    return ToolSpec(
        name=NOTEPAD_CHECKLIST_TOOL,
        version="0.1.0",
        description="Owned reviewed checklist",
        argument_model=NotepadChecklistSubmission,
        risk_floor=RiskLevel.LOW,
        required_scope="fs:write",
        timeout_seconds=180,
        resource_name="workflow_owner",
        retry_class=RetryClass.NONE,
        execute=reject_unowned,
        execute_owned=executor,
        verify=verify_native_checklist,
    )
