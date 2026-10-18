"""The real shared dispatcher enforces step policy, bounds, cancellation and proof."""

import asyncio
import threading
from dataclasses import replace

import pytest
from pydantic import ValidationError

from victus.runtime.resources import resources
from victus.tools.contracts import ActionProposal, ActionRequest, ToolRequest
from victus.tools.dispatcher import Dispatcher
from victus.tools.filesystem import fs_create_note
from victus.tools.registry import RiskLevel, ToolRegistry
from victus.workflows.common import Arguments, context_for, spec


class Input(Arguments):
    text: str


def setup(tmp_path, execute, verify, *, authorize=lambda tool, args: True, timeout=1):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    registry = ToolRegistry()
    registry.register(
        spec("fixture.step", Input, execute, verify, "fixture:execute", timeout=timeout)
    )
    cancelled = threading.Event()
    context = context_for(workspace, "fixture-task", cancelled, {"fixture:execute"}, authorize)
    return Dispatcher(workspace, registry), context, cancelled


def test_step_is_verified_and_payload_kept_out_of_audit(tmp_path):
    def execute(root, args):
        return {"text": args.text}

    dispatcher, context, _ = setup(
        tmp_path, execute, lambda output, args: output["text"] == args.text
    )
    outcome = asyncio.run(
        dispatcher.dispatch_step(
            ActionProposal(tool="fixture.step", arguments={"text": "PRIVATE_PAYLOAD"}), context
        )
    )
    assert outcome.verified
    assert context.ledger.get(outcome.action_id).status == "verified"
    assert context.payloads.get_by_action(outcome.action_id, "output")
    assert "PRIVATE_PAYLOAD" not in repr(context.events.get_events(task_id=context.task_id))
    assert "PRIVATE_PAYLOAD" not in repr(context.trace)


@pytest.mark.parametrize("mode", ["policy", "unknown-tool", "bad-arguments", "stopped", "budget"])
def test_rejections_and_stop_dispatch_nothing(tmp_path, mode):
    calls = []
    dispatcher, context, cancelled = setup(
        tmp_path, lambda *args: calls.append(True), lambda *args: True
    )
    proposal = ActionProposal(tool="fixture.step", arguments={"text": "private"})
    if mode == "policy":
        context.authorize = lambda *args: False
    elif mode == "unknown-tool":
        proposal.tool = "unknown"
    elif mode == "bad-arguments":
        proposal.arguments = {"unexpected": "private"}
    elif mode == "stopped":
        cancelled.set()
    else:
        context.remaining_steps = 0
    result = asyncio.run(dispatcher.dispatch_step(proposal, context))
    assert not result.verified and calls == []


@pytest.mark.parametrize(
    "mode", ["mismatch", "exception", "timeout", "live-handle", "stopped-after-effect"]
)
def test_attempted_but_unproved_effects_are_unknown_and_never_retried(tmp_path, mode):
    calls = []

    async def execute(root, args):
        calls.append(True)
        if mode == "exception":
            raise RuntimeError("PRIVATE_ERROR")
        if mode == "timeout":
            await asyncio.sleep(2)
        if mode == "stopped-after-effect":
            cancelled.set()
        return {"value": object() if mode == "live-handle" else "done"}

    dispatcher, context, cancelled = setup(
        # The deadline includes durable pre-dispatch checks, not only inference.
        tmp_path,
        execute,
        lambda *args: mode != "mismatch",
        timeout=0.5,
    )
    result = asyncio.run(
        dispatcher.dispatch_step(
            ActionProposal(tool="fixture.step", arguments={"text": "private"}), context
        )
    )
    assert result.status == "unknown" and calls == [True]
    assert context.ledger.get(result.action_id).status == "unknown"
    assert "PRIVATE_ERROR" not in repr(context.trace)


@pytest.mark.parametrize(
    "extra", ["task_id", "action_id", "approved", "verifier", "scopes", "permit_token"]
)
def test_transport_and_proposal_never_accept_authority(extra):
    for contract in (ToolRequest, ActionProposal):
        with pytest.raises(ValidationError):
            contract.model_validate(
                {"tool": "fixture.step", "arguments": {"text": "x"}, extra: True}
            )


@pytest.mark.parametrize(
    "malformed",
    [
        {"tool": "fixture.step", "arguments": {"text": 7}},
        {"tool": "fixture.step", "arguments": {"text": "x", "approved": True}},
        {"tool": "fixture.step", "arguments": {"text": "x"}, "task_id": "forged"},
        {"tool": "unknown", "arguments": {"text": "x"}},
    ],
)
def test_dispatcher_revalidates_untrusted_or_constructed_input(tmp_path, malformed):
    calls = []
    dispatcher, context, _ = setup(tmp_path, lambda *_: calls.append(1), lambda *_: True)
    forged = malformed if "task_id" in malformed else ActionProposal.model_construct(**malformed)
    outcome = asyncio.run(dispatcher.dispatch_step(forged, context))
    assert not outcome.verified and calls == []
    assert context.ledger.list_for_task(context.task_id) == []


@pytest.mark.parametrize("verification", [False, 1, "verified", {"verified": True}, None])
def test_only_exact_true_from_trusted_verifier_can_succeed(tmp_path, verification):
    dispatcher, context, _ = setup(
        tmp_path, lambda *_: {"value": "effect"}, lambda *_: verification
    )
    outcome = asyncio.run(
        dispatcher.dispatch_step(
            ActionProposal(tool="fixture.step", arguments={"text": "x"}), context
        )
    )
    assert outcome.status == "unknown" and not outcome.verified
    assert context.ledger.get(outcome.action_id).status == "unknown"


@pytest.mark.parametrize("kind", ["scope", "risk"])
def test_deterministic_scope_and_risk_denial_precedes_intent(tmp_path, kind):
    calls = []
    dispatcher, context, _ = setup(tmp_path, lambda *_: calls.append(1), lambda *_: True)
    if kind == "scope":
        context.scopes = frozenset()
    else:
        registry = ToolRegistry()
        registry.register(
            replace(dispatcher.registry.get("fixture.step"), risk_floor=RiskLevel.HIGH)
        )
        dispatcher.registry = registry
    outcome = asyncio.run(
        dispatcher.dispatch_step(
            ActionProposal(tool="fixture.step", arguments={"text": "x"}), context
        )
    )
    assert not outcome.verified and calls == []
    assert context.ledger.list_for_task(context.task_id) == []


def test_distinct_dispatchers_share_mutation_slot(tmp_path):
    calls = []

    async def execute(*_):
        calls.append("start")
        await asyncio.sleep(0.03)
        calls.append("finish")
        return {"value": "done"}

    dispatcher, context, _ = setup(tmp_path, execute, lambda *_: True)
    other = Dispatcher(dispatcher.workspace, dispatcher.registry)
    second = context_for(
        dispatcher.workspace, "other-task", threading.Event(), {"fixture:execute"}, lambda *_: True
    )
    action = ActionProposal(tool="fixture.step", arguments={"text": "x"})

    async def run():
        return await asyncio.gather(
            dispatcher.dispatch_step(action, context), other.dispatch_step(action, second)
        )

    assert all(r.verified for r in asyncio.run(run()))
    assert calls == ["start", "finish", "start", "finish"]


@pytest.mark.parametrize("change", ["target", "policy", "stop"])
def test_final_policy_target_and_stop_rechecked_after_resource_wait(tmp_path, change):
    calls = []
    dispatcher, context, cancelled = setup(tmp_path, lambda *_: calls.append(1), lambda *_: True)
    ready = threading.Event()
    allowed = [True]

    def authorize(*_):
        ready.set()
        return allowed[0]

    context.authorize = authorize
    original = dispatcher.registry.get("fixture.step")

    def policy(root, _args):
        if (root / "stale").exists():
            raise PermissionError()

    registry = ToolRegistry()
    registry.register(replace(original, policy=policy))
    dispatcher.registry = registry
    resource = resources().mutation
    resource.acquire()

    def change_and_release():
        assert ready.wait(2)
        if change == "target":
            (dispatcher.workspace / "stale").touch()
        elif change == "policy":
            allowed[0] = False
        else:
            cancelled.set()
        resource.release()

    thread = threading.Thread(target=change_and_release)
    thread.start()
    try:
        outcome = asyncio.run(
            dispatcher.dispatch_step(
                ActionProposal(tool="fixture.step", arguments={"text": "x"}), context
            )
        )
    finally:
        thread.join(3)
    assert not outcome.verified and calls == []
    assert context.ledger.list_for_task(context.task_id) == []


def test_dispatch_intent_is_durable_before_adapter_and_identity_is_service_assigned(tmp_path):
    seen = []

    def execute(*_):
        records = context.ledger.list_for_task(context.task_id)
        assert len(records) == 1 and records[0].status == "dispatching"
        seen.append(records[0].action_id)
        return {"value": "done"}

    dispatcher, context, _ = setup(tmp_path, execute, lambda *_: True)
    outcome = asyncio.run(
        dispatcher.dispatch_step(
            ActionProposal(tool="fixture.step", arguments={"text": "x"}), context
        )
    )
    assert outcome.verified and seen == [outcome.action_id]
    assert len(outcome.action_id) == 32


def test_note_tool_uses_the_same_step_path_and_keeps_exclusive_creation(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    registry = ToolRegistry()
    registry.register(fs_create_note())
    dispatcher = Dispatcher(root, registry)
    context = context_for(root, "note-task", None, {"fs:write"}, lambda *_: True)
    action = ActionRequest(
        tool="fs.create_note", arguments={"filename": "safe.txt", "text": "original"}
    )
    first = asyncio.run(dispatcher.dispatch_step(action, context))
    second = asyncio.run(dispatcher.dispatch_step(action, context))
    assert first.verified and not second.verified
    assert second.error_code == "TARGET_EXISTS"
    assert (root / "safe.txt").read_text() == "original"
