"""Command-specific model boundary checks; provider replies are deterministic fixtures."""

import asyncio
import json
import threading
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest

from victus.agent.command_execution import CommandExecutor
from victus.agent.commands import CommandReference, CommandSubmission
from victus.models.contracts import ErrorCode, ModelError, ModelPin, ProviderResponse, ProviderUsage
from victus.storage.database import Database
from victus.storage.secure_json import encode
from victus.tools.contracts import ToolRequest
from victus.tools.filesystem import fs_create_note


@pytest.mark.parametrize(
    "mode",
    [
        "arbitrary_tool",
        "changed_path",
        "changed_text",
        "finish_only",
        "invalid_json",
        "timeout",
        "stop",
    ],
)
def test_model_cannot_expand_confirmed_effect_or_claim_unverified_completion(
    tmp_path, monkeypatch, mode
):
    import victus.agent.command_execution as module

    workspace = tmp_path / "runtime/workspace"
    workspace.mkdir(parents=True)
    database = Database(workspace.parent)
    command_id = uuid4().hex
    task_id = uuid4().hex
    pin = ModelPin(name="fixture:1", digest="sha256:" + "a" * 64)
    expected = ToolRequest(
        tool="fs.create_note", arguments={"filename": "confirmed.txt", "text": "confirmed"}
    )
    submission = CommandSubmission(text="Create a note", reasoning=True)
    payload = {
        "submission": submission.model_dump(),
        "action": expected.model_dump(),
        "model_pin": pin.model_dump(),
    }
    with database.connect() as db:
        db.execute(
            "INSERT INTO command_intakes VALUES(?,?,?,?,?,?)",
            (command_id, "fixture", encode(payload), "submitted", task_id, time.time() + 300),
        )
    cancelled = threading.Event()

    class Provider:
        async def complete(self, request):
            if mode == "timeout":
                raise ModelError(ErrorCode.TIMEOUT)
            if mode == "stop":
                cancelled.set()
                await asyncio.sleep(0.1)
            action = expected.model_dump()
            if mode == "arbitrary_tool":
                action = {"tool": "shell.run", "arguments": {"command": "evil"}}
            if mode == "changed_path":
                action = {
                    **action,
                    "arguments": {**action["arguments"], "filename": "unreviewed.txt"},
                }
            if mode == "changed_text":
                action = {**action, "arguments": {**action["arguments"], "text": "unreviewed"}}
            decision = (
                {"decision": "finish", "status": "completed", "reason": "Trust my summary"}
                if mode == "finish_only"
                else {"decision": "action", "action": action}
            )
            return ProviderResponse(
                pin=pin,
                content="not JSON" if mode == "invalid_json" else json.dumps(decision),
                usage=ProviderUsage(input_tokens=20, output_tokens=30),
            )

        async def close(self):
            pass

    monkeypatch.setattr(module, "OllamaClient", Provider)
    executor = CommandExecutor(fs_create_note(), expected, pin)
    with pytest.raises(RuntimeError, match="not independently verified"):
        asyncio.run(
            executor(
                workspace,
                CommandReference(command_id=command_id),
                cancelled,
                SimpleNamespace(task_id=task_id),
            )
        )
    assert list(workspace.iterdir()) == []
