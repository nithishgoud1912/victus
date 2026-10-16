"""M4 real checkpoint/dispatcher integration with an authenticated review route."""

import asyncio
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from graph_support import Fixture

from victus.agent.graph import agent
from victus.api.app import create_app
from victus.safety.permits import PermitStore, consume_permit, issue_permit, validate_binding
from victus.settings import Settings
from victus.tools.registry import RiskLevel

TOKEN = "review-test-" + "x" * 40
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
DECISION = {"decision": "approved", "confirmation": "explicit_user_review"}


def consequential(root):
    fixture = Fixture(root)
    tool = fixture.dispatcher.registry.get("fixture.write")
    fixture.dispatcher.registry._tools[tool.name] = replace(tool, risk_floor=RiskLevel.HIGH)
    return fixture


def approve(fixture, state):
    store = fixture.services.approvals(state)
    record = store.get(state["approval_ref"])
    return store.decide(record.approval_id, record.binding(), approved=True)


def test_real_interrupt_survives_replay_and_ignores_forged_resume_body(tmp_path):
    fixture = consequential(tmp_path)

    async def run():
        async with agent(fixture.services) as runner:
            state = await runner.start(fixture.task, fixture.goal())
            assert state["status"] == "awaiting_approval" and fixture.calls == 0
            saved = await runner.graph.aget_state(runner.config(fixture.task))
            assert saved.next == ("review",) and saved.tasks[0].interrupts
            with fixture.store.connect() as db:
                before = db.execute("SELECT count(*) FROM node_journal").fetchone()[0]
            for _ in range(3):
                assert (await runner.resume(fixture.task))["approval_ref"] == state["approval_ref"]
            with fixture.store.connect() as db:
                assert db.execute("SELECT count(*) FROM node_journal").fetchone()[0] == before
                assert not db.execute("SELECT 1 FROM node_journal WHERE node='review'").fetchall()
            assert len(fixture.context(state).ledger.list_for_task(fixture.task)) == 1
            # Even bypassing the runner with a forged resume cannot approve.
            from langgraph.types import Command

            await runner.graph.ainvoke(
                Command(resume={"approved": True}), runner.config(fixture.task)
            )
            result = await runner.graph.aget_state(runner.config(fixture.task))
            assert result.values["status"] == "blocked" and fixture.calls == 0

    asyncio.run(run())


def test_authenticated_resolution_and_reopened_graph_dispatch_exactly_once(tmp_path):
    settings = Settings(tmp_path, TOKEN)
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        fixture = consequential(tmp_path)

        async def pause():
            async with agent(fixture.services) as runner:
                return await runner.start(fixture.task, fixture.goal())

        state = asyncio.run(pause())
        url = f"/api/approvals/{state['approval_ref']}"
        assert client.get(url).status_code == 401
        assert client.post(url + "/resolve", json=DECISION).status_code == 401
        assert client.get(url + "/preview", headers=HEADERS).json()["arguments"]["text"] == "ready"
        for extra in (
            {"action_id": "other"},
            {"arguments": {"text": "changed"}},
            {"source": "voice"},
        ):
            assert (
                client.post(
                    url + "/resolve", headers=HEADERS, json={**DECISION, **extra}
                ).status_code
                == 422
            )
        assert (
            client.post(
                url + "/resolve", headers=HEADERS, json={"decision": "approved"}
            ).status_code
            == 422
        )
        assert client.post(url + "/resolve", headers=HEADERS, json=DECISION).status_code == 200
        assert client.post(url + "/resolve", headers=HEADERS, json=DECISION).status_code == 409
        reopened = consequential(tmp_path)

        async def resume():
            async with agent(reopened.services) as runner:
                result = await runner.resume(reopened.task)
                again = await runner.resume(reopened.task)
                assert again["status"] == result["status"]
                return result

        result = asyncio.run(resume())
        assert result["status"] == "succeeded" and reopened.calls == 1
        assert client.get(url, headers=HEADERS).json()["state"] == "consumed"
        response = client.post(url + "/resolve", headers=HEADERS, json=DECISION)
        assert response.status_code == 409 and "consumed" in response.json()["detail"]


@pytest.mark.parametrize("change", ["target", "observation", "policy", "cancel", "expire", "deny"])
def test_review_resume_cannot_use_stale_approval(tmp_path, change):
    fixture = consequential(tmp_path)

    async def run():
        async with agent(fixture.services) as runner:
            state = await runner.start(fixture.task, fixture.goal())
            store = fixture.services.approvals(state)
            record = store.get(state["approval_ref"])
            if change == "deny":
                store.decide(record.approval_id, record.binding(), approved=False)
            else:
                approve(fixture, state)
            if change == "target":
                (fixture.workspace / "note.txt").write_text("another user's file")
            elif change == "observation":
                # The trusted resolver now reports a different live target binding.
                fixture.services.target_identity = lambda *_: "replacement-window"
            elif change == "policy":
                fixture.services.policy_version = "new-policy"
            elif change == "cancel":
                runner.cancel(fixture.task)
            elif change == "expire":
                with store.connect() as db:
                    db.execute("UPDATE approvals SET expires_at=0")
            result = await runner.resume(fixture.task)
            assert result["status"] != "succeeded" and fixture.calls == 0
            assert store.get(record.approval_id).state in {"denied", "expired", "invalidated"}
            if change == "target":
                assert (fixture.workspace / "note.txt").read_text() == "another user's file"

    asyncio.run(run())


@pytest.mark.parametrize("change", ["target", "cancel", "expire"])
def test_dispatcher_rechecks_after_execution_context_created(tmp_path, change):
    fixture = Fixture(tmp_path)
    original = fixture.services.execution

    async def execution(state):
        action, context = await original(state)
        if change == "target":
            (fixture.workspace / "note.txt").write_text("preserve")
        elif change == "cancel":
            fixture.store.cancel(fixture.task)
        else:
            with context.permits.approvals.connect() as db:
                db.execute("UPDATE approvals SET expires_at=0")
        return action, context

    fixture.services.execution = execution

    async def run():
        async with agent(fixture.services) as runner:
            return await runner.start(fixture.task, fixture.goal())

    result = asyncio.run(run())
    assert result["status"] != "succeeded" and fixture.calls == 0


def test_named_permit_functions_and_transactional_cancellation(tmp_path):
    from victus.safety.approvals import ApprovalBinding, ApprovalStore, argument_hash
    from victus.storage.migrations import migrate

    path = tmp_path / "victus.sqlite3"
    migrate(path)
    store = ApprovalStore(path)
    binding = ApprovalBinding(
        task_id="task",
        action_id="action",
        tool_name="tool",
        tool_version="1",
        canonical_args_hash=argument_hash({}),
        policy_version="1",
        target_identity="file",
        observation_identity="obs",
    )
    record = store.request(binding, {})
    store.decide(record.approval_id, binding, approved=True)
    permits = PermitStore(store)
    assert validate_binding(permits, record.approval_id, binding).state == "approved"
    token = issue_permit(permits, record.approval_id, binding)
    checks = []

    def cancelled():
        checks.append(True)
        return len(checks) > 1

    with pytest.raises(PermissionError):
        consume_permit(permits, token, binding, cancelled=cancelled)
    assert store.get(record.approval_id).state == "invalidated"


def test_expired_resolution_has_clear_conflict_and_stop_invalidates(tmp_path):
    settings = Settings(tmp_path, TOKEN)
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        fixture = consequential(tmp_path)

        async def run():
            async with agent(fixture.services) as runner:
                return await runner.start(fixture.task, fixture.goal())

        state = asyncio.run(run())
        store = fixture.services.approvals(state)
        with store.connect() as db:
            db.execute("UPDATE approvals SET expires_at=0")
        url = f"/api/approvals/{state['approval_ref']}/resolve"
        response = client.post(url, headers=HEADERS, json=DECISION)
        assert response.status_code == 409 and "expired" in response.json()["detail"]
        assert (
            client.post(
                "/api/approvals/missing/resolve", headers=HEADERS, json=DECISION
            ).status_code
            == 404
        )

        old = store.get(state["approval_ref"])
        fresh = store.request(old.binding(), {"text": "review again"})
        assert client.post("/api/stop", headers=HEADERS).status_code == 200
        response = client.post(
            f"/api/approvals/{fresh.approval_id}/resolve", headers=HEADERS, json=DECISION
        )
        assert response.status_code == 409 and "stopped" in response.json()["detail"]
        assert store.get(fresh.approval_id).state == "invalidated"


def test_bootstrap_invalidates_old_review_on_service_restart(tmp_path):
    from victus.bootstrap import build_services

    fixture = consequential(tmp_path)

    async def run():
        async with agent(fixture.services) as runner:
            return await runner.start(fixture.task, fixture.goal())

    state = asyncio.run(run())
    record = fixture.services.approvals(state).get(state["approval_ref"])
    services = build_services(Settings(tmp_path, TOKEN))
    try:
        assert services.ledger.get(record.action_id).status == "cancelled"
        assert services.approvals.get(record.approval_id).state == "invalidated"
    finally:
        services.close()


@pytest.mark.parametrize(
    "window,exit_code,attempt", [("consume", 73, "cancelled"), ("effect", 71, "unknown")]
)
def test_killed_process_never_replays_consumed_permit(tmp_path, window, exit_code, attempt):
    import json
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).parent / "live" / "m4_approval_crash_probe.py"
    crashed = subprocess.run(
        [sys.executable, str(script), window, "--data-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert crashed.returncode == exit_code, crashed.stderr
    for _ in range(2):
        resumed = subprocess.run(
            [sys.executable, str(script), "resume", "--data-dir", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert resumed.returncode == 0, resumed.stderr
        result = json.loads(resumed.stdout)
        assert result == {
            "status": "unknown",
            "calls": 0,
            "approvals": ["consumed"],
            "attempts": [attempt],
        }
    assert (tmp_path / "workspace" / "note.txt").exists() is (window == "effect")


def test_interrupt_serializer_is_explicit_and_validation_never_swallows_interrupt(tmp_path):
    from langgraph.errors import GraphInterrupt
    from langgraph.types import Interrupt

    from victus.storage.checkpoints import JSONSerializer
    from victus.tools.contracts import ActionProposal

    serializer = JSONSerializer()
    interrupt = Interrupt(value={"approval_id": "record"}, id="interrupt-id")
    restored = serializer.loads_typed(serializer.dumps_typed([interrupt]))
    assert type(restored[0]) is Interrupt and restored[0].value == interrupt.value
    assert restored[0].id == interrupt.id
    with pytest.raises(TypeError):
        serializer.dumps_typed([object()])
    fixture = Fixture(tmp_path)
    context = fixture.context({"task_id": fixture.task})

    def interrupted(*_):
        raise GraphInterrupt((interrupt,))

    context.authorize = interrupted
    with pytest.raises(GraphInterrupt):
        asyncio.run(
            fixture.dispatcher.dispatch_step(
                ActionProposal(
                    tool="fixture.write", arguments={"filename": "note.txt", "text": "ready"}
                ),
                context,
            )
        )
    assert fixture.calls == 0 and context.ledger.list_for_task(fixture.task) == []


def test_policy_rejection_before_live_resolver_permanently_retires_review(tmp_path):
    fixture = Fixture(tmp_path)
    original = fixture.services.execution
    contexts = []

    async def execution(state):
        action, context = await original(state)
        contexts.append((action, context))
        context.authorize = lambda *_: False
        return action, context

    fixture.services.execution = execution

    async def run():
        async with agent(fixture.services) as runner:
            state = await runner.start(fixture.task, fixture.goal())
            action, context = contexts[0]
            context.authorize = lambda *_: True
            outcome = await fixture.dispatcher.dispatch_step(action, context)
            assert outcome.status == "blocked"
            with context.permits.approvals.connect() as db:
                assert db.execute("SELECT state FROM approvals").fetchone()[0] == "invalidated"
            return state

    result = asyncio.run(run())
    assert result["status"] == "blocked" and fixture.calls == 0


def test_non_filesystem_tool_requires_explicit_live_identity_resolver(tmp_path):
    fixture = Fixture(tmp_path)
    fixture.services.target_identity = None

    async def run():
        async with agent(fixture.services) as runner:
            return await runner.start(fixture.task, fixture.goal())

    result = asyncio.run(run())
    assert result["status"] != "succeeded" and fixture.calls == 0
    with fixture.services.approvals(result).connect() as db:
        assert not db.execute("SELECT 1 FROM approvals").fetchall()
