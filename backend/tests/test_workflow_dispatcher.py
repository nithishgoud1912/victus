"""The real shared dispatcher enforces step policy, bounds, cancellation and proof."""

import asyncio
import threading

import pytest

from victus.tools.contracts import ActionProposal
from victus.tools.dispatcher import Dispatcher
from victus.tools.registry import ToolRegistry
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
            await asyncio.sleep(1)
        if mode == "stopped-after-effect":
            cancelled.set()
        return {"value": object() if mode == "live-handle" else "done"}

    dispatcher, context, cancelled = setup(
        tmp_path, execute, lambda *args: mode != "mismatch", timeout=0.02
    )
    result = asyncio.run(
        dispatcher.dispatch_step(
            ActionProposal(tool="fixture.step", arguments={"text": "private"}), context
        )
    )
    assert result.status == "unknown" and calls == [True]
    assert context.ledger.get(result.action_id).status == "unknown"
    assert "PRIVATE_ERROR" not in repr(context.trace)
