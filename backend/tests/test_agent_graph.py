import asyncio
import json
import sqlite3

import pytest
from graph_support import Fixture

from victus.agent.graph import agent
from victus.agent.state import Budgets
from victus.storage.checkpoints import CheckpointStore, JSONSerializer


def run(fixture, goal=None, budgets=None):
    async def execute():
        async with agent(fixture.services) as runner:
            return await runner.start(fixture.task, goal or fixture.goal(), budgets=budgets)

    return asyncio.run(execute())


def test_real_dispatcher_verification_and_reference_only_checkpoints(tmp_path):
    fixture = Fixture(tmp_path)
    result = run(fixture)
    assert result["status"] == "succeeded" and result["completion_verified"]
    assert fixture.calls == 1 and fixture.plan_calls == 1
    record = fixture.context(result).ledger.get(result["action_ledger_refs"][0])
    assert record.status == "verified" and result["evidence_refs"]
    with sqlite3.connect(fixture.store.path) as db:
        rows = db.execute("SELECT checkpoint FROM checkpoints").fetchall()
    assert len(rows) > 5
    assert all(
        b"PRIVATE_OBSERVATION" not in row[0] and b'"text":"ready"' not in row[0] for row in rows
    )


def test_model_done_is_not_task_proof(tmp_path):
    fixture = Fixture(
        tmp_path,
        decisions=[{"decision": "finish", "status": "completed", "reason": "Done, trust me"}],
    )
    result = run(fixture)
    assert result["status"] == "failed" and not result["completion_verified"]
    assert fixture.calls == 0 and result["error_history"][0]["code"] == "GOAL_NOT_VERIFIED"


def test_finish_with_independent_existing_goal_proof(tmp_path):
    fixture = Fixture(
        tmp_path,
        decisions=[{"decision": "finish", "status": "completed", "reason": "No actions needed"}],
    )
    (fixture.workspace / "note.txt").write_text("ready")
    result = run(fixture)
    assert result["status"] == "succeeded" and fixture.calls == 0


def test_multiple_verified_actions_continue_via_observe(tmp_path):
    fixture = Fixture(
        tmp_path, decisions=[Fixture.action("a.txt", "one"), Fixture.action("b.txt", "two")]
    )
    result = run(fixture, fixture.goal({"a.txt": "one", "b.txt": "two"}))
    assert result["status"] == "succeeded" and fixture.calls == 2 and fixture.observations == 2
    assert len(result["action_ledger_refs"]) == 2 and result["remaining"]["actions"] == 10


@pytest.mark.parametrize("mode", ["approval", "validation", "route", "finish"])
def test_blocked_paths_never_execute(tmp_path, mode):
    fixture = Fixture(tmp_path)
    if mode == "approval":
        fixture.approved = False
    elif mode == "validation":
        fixture.valid = False
    elif mode == "route":
        fixture.services.router = lambda goal: None
    else:
        fixture.decisions = [{"decision": "finish", "status": "blocked", "reason": "Unavailable"}]
    result = run(fixture)
    assert result["status"] in {"blocked", "failed"} and fixture.calls == 0


def test_pending_approval_survives_reopen_and_revalidates(tmp_path):
    fixture = Fixture(tmp_path)
    fixture.approved = None
    first = run(fixture)
    assert first["status"] == "awaiting_approval" and fixture.calls == 0
    reopened = Fixture(tmp_path, decisions=[])
    reopened.resolve_review()

    async def resume():
        async with agent(reopened.services) as runner:
            return await runner.resume(reopened.task)

    result = asyncio.run(resume())
    assert result["status"] == "succeeded" and reopened.calls == 1 and reopened.plan_calls == 0


def test_approval_resume_cannot_bypass_new_validation_failure(tmp_path):
    fixture = Fixture(tmp_path)
    fixture.approved = None
    run(fixture)
    reopened = Fixture(tmp_path, decisions=[])
    reopened.valid = False
    reopened.resolve_review()

    async def resume():
        async with agent(reopened.services) as runner:
            return await runner.resume(reopened.task)

    result = asyncio.run(resume())
    assert result["status"] == "blocked" and reopened.calls == 0
    assert result["error_code"] == "APPROVAL_OR_TARGET_STALE"


@pytest.mark.parametrize(
    "budget", ["nodes", "actions", "observations", "model_requests", "output_tokens"]
)
def test_finite_budgets_stop_without_unapproved_effects(tmp_path, budget):
    fixture = Fixture(tmp_path)
    result = run(fixture, budgets=Budgets(**{budget: 0}))
    assert result["status"] == "blocked" and fixture.calls == 0
    assert result["error_code"] == "AGENT_BUDGET_EXHAUSTED"


def test_deterministic_recovery_reobserves_before_new_proposal(tmp_path):
    fixture = Fixture(
        tmp_path,
        decisions=[Fixture.action("note.txt", "ready"), Fixture.action("note.txt", "ready")],
    )
    checks = []

    def validate(state, action):
        checks.append(True)
        return len(checks) > 1

    fixture.services.validator = validate
    original_observe = fixture.services.observer
    fixture.services.observer = lambda route, goal: {
        **original_observe(route, goal),
        "validation_state": len(checks),
    }
    fixture.recovery = "observe"
    result = run(fixture)
    assert result["status"] == "succeeded" and fixture.calls == 1 and fixture.observations == 2
    assert result["remaining"]["recoveries"] == 1 and len(result["error_history"]) == 1


def test_failed_effect_is_unknown_and_never_retried(tmp_path):
    fixture = Fixture(tmp_path)
    tool = fixture.dispatcher.registry.get("fixture.write")
    object.__setattr__(tool, "verify", lambda *args: False)
    fixture.recovery = "propose"
    result = run(fixture)
    assert result["status"] == "unknown" and fixture.calls == 1 and fixture.plan_calls == 1


def test_json_serializer_never_loads_pickle_or_live_objects():
    serde = JSONSerializer()
    assert serde.loads_typed(serde.dumps_typed({"refs": ["a"], "value": None})) == {
        "refs": ["a"],
        "value": None,
    }
    with pytest.raises(ValueError):
        serde.loads_typed(("pickle", b"unsafe"))
    with pytest.raises(TypeError):
        serde.dumps_typed({"live": object()})


def test_payload_ownership_retention_and_purge(tmp_path):
    store = CheckpointStore(tmp_path)
    reference = store.put_payload("one", "goal", {"text": "private"})
    with pytest.raises(ValueError):
        store.payload("two", "goal", reference)
    with pytest.raises(ValueError):
        store.payload("one", "proposal", reference)
    with store.connect() as db:
        db.execute("UPDATE agent_payloads SET expires=0")
    with pytest.raises(ValueError):
        store.payload("one", "goal", reference)
    assert store.purge_expired() == 1


@pytest.mark.parametrize(
    "window,code,expected", [("effect", 71, "unknown"), ("journal", 72, "succeeded")]
)
def test_hard_process_restart_never_repeats_file_write(tmp_path, window, code, expected):
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).parent / "live" / "m3_graph_crash_probe.py"
    crashed = subprocess.run(
        [sys.executable, str(script), window, "--data-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert crashed.returncode == code, crashed.stderr
    assert (tmp_path / "workspace" / "note.txt").read_bytes() == b"ready"
    resumed = subprocess.run(
        [sys.executable, str(script), "resume", "--data-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert resumed.returncode == 0, resumed.stderr
    report = json.loads(resumed.stdout)
    assert report["status"] == expected and report["calls_this_process"] == 0
    assert len(report["action_refs"]) == 1
    fixture = Fixture(tmp_path)
    records = fixture.context({"task_id": fixture.task}).ledger.list_for_task(fixture.task)
    assert len(records) == 1
    assert records[0].status == ("unknown" if window == "effect" else "verified")


def test_recovery_budget_stops_repeated_invalid_proposals(tmp_path):
    fixture = Fixture(tmp_path, decisions=[Fixture.action("note.txt", "ready")] * 4)
    fixture.valid = False
    fixture.recovery = "propose"
    result = run(fixture, budgets=Budgets(recoveries=1))
    assert result["status"] == "partial" and fixture.plan_calls == 2 and fixture.calls == 0
    assert result["remaining"]["recoveries"] == 0


def test_task_deadline_survives_restart(tmp_path):
    import time

    fixture = Fixture(tmp_path)
    fixture.approved = None
    run(fixture, budgets=Budgets(deadline_epoch=time.time() + 30))

    async def resume():
        async with agent(fixture.services) as runner:
            snapshot = await runner.graph.aget_state(runner.config(fixture.task))
            left = {**snapshot.values["remaining"], "deadline_epoch": time.time() - 1}
            await runner.graph.aupdate_state(runner.config(fixture.task), {"remaining": left})
            return await runner.resume(fixture.task)

    result = asyncio.run(resume())
    assert result["status"] == "blocked" and fixture.calls == 0
    assert result["error_code"] == "AGENT_BUDGET_EXHAUSTED"


def test_cancellation_latch_survives_restart_before_execution(tmp_path):
    fixture = Fixture(tmp_path)
    fixture.approved = None
    run(fixture)
    fixture.store.cancel(fixture.task)
    reopened = Fixture(tmp_path, decisions=[])

    async def resume():
        async with agent(reopened.services) as runner:
            return await runner.resume(reopened.task)

    result = asyncio.run(resume())
    assert result["status"] == "cancelled" and result["cancellation_requested"]
    assert reopened.calls == 0


def test_cancel_inflight_effect_marks_unknown_and_does_not_replay(tmp_path):
    fixture = Fixture(tmp_path)
    entered = asyncio.Event()
    original = fixture.execute

    async def effect(workspace, args):
        output = original(workspace, args)
        entered.set()
        await asyncio.sleep(10)
        return output

    object.__setattr__(fixture.dispatcher.registry.get("fixture.write"), "execute", effect)

    async def execute():
        async with agent(fixture.services) as runner:
            pending = asyncio.create_task(runner.start(fixture.task, fixture.goal()))
            await asyncio.wait_for(entered.wait(), 3)
            runner.cancel(fixture.task)
            return await asyncio.wait_for(pending, 3)

    result = asyncio.run(execute())
    assert result["status"] == "unknown" and fixture.calls == 1
    assert fixture.context(result).ledger.get(result["action_ledger_refs"][0]).status == "unknown"


def test_restart_rechecks_target_and_current_approval(tmp_path):
    fixture = Fixture(tmp_path)

    async def stop():
        async with agent(fixture.services, interrupt_after=["authorize"]) as runner:
            return await runner.start(fixture.task, fixture.goal())

    first = asyncio.run(stop())
    assert first["next_node"] == "execute" and fixture.calls == 0
    reopened = Fixture(tmp_path, decisions=[])
    reopened.valid = False

    async def resume():
        async with agent(reopened.services) as runner:
            return await runner.resume(reopened.task)

    result = asyncio.run(resume())
    assert result["status"] != "succeeded" and reopened.calls == 0


def test_graph_refuses_memory_checkpointer(tmp_path):
    from langgraph.checkpoint.memory import InMemorySaver

    from victus.agent.graph import build_graph

    with pytest.raises(TypeError):
        build_graph(Fixture(tmp_path).services, InMemorySaver())


def test_only_one_checkpoint_owner_and_no_duplicate_start(tmp_path):
    fixture = Fixture(tmp_path)

    async def execute():
        async with agent(fixture.services) as runner:
            with pytest.raises(RuntimeError):
                async with agent(fixture.services):
                    pass
            await runner.start(fixture.task, fixture.goal())
            with pytest.raises(sqlite3.IntegrityError):
                await runner.start(fixture.task, fixture.goal())

    asyncio.run(execute())
    assert fixture.calls == 1


def test_service_exception_is_sanitized_and_charges_planning_budget(tmp_path):
    fixture = Fixture(tmp_path)

    def broken(*args):
        raise RuntimeError("PRIVATE PROVIDER FAILURE")

    fixture.services.planner = broken
    result = run(fixture)
    assert result["status"] == "failed" and "PRIVATE" not in repr(result)
    assert result["remaining"]["model_requests"] == 6
    assert result["remaining"]["output_tokens"] == 3072
    assert result["remaining"]["schema_repairs"] == 1
    assert result["remaining"]["repairs_used"] == 1


def test_gateway_planner_repair_usage_is_checkpointed(tmp_path):
    from victus.agent.services import GatewayPlanner
    from victus.models.contracts import ModelPin, ProviderResponse, ProviderUsage

    fixture = Fixture(tmp_path)
    pin = ModelPin(name="fixture:1", digest="sha256:" + "a" * 64)

    class Provider:
        def __init__(self):
            self.calls = 0

        async def complete(self, request):
            self.calls += 1
            return ProviderResponse(
                pin=pin,
                content="malformed"
                if self.calls == 1
                else json.dumps(Fixture.action("note.txt", "ready")),
                usage=ProviderUsage(input_tokens=10, output_tokens=10),
            )

    provider = Provider()
    fixture.services.planner = GatewayPlanner(provider, pin, fixture.parser)
    result = run(fixture)
    assert result["status"] == "succeeded" and provider.calls == 2
    assert result["remaining"]["model_requests"] == 6 and result["remaining"]["schema_repairs"] == 1
    assert result["remaining"]["repairs_used"] == 1
    assert result["remaining"]["output_tokens"] == 3072


def test_each_decision_can_repair_without_resetting_shared_model_budget(tmp_path):
    from victus.agent.services import GatewayPlanner
    from victus.models.contracts import ModelPin, ProviderResponse, ProviderUsage

    fixture = Fixture(tmp_path)
    pin = ModelPin(name="fixture:1", digest="sha256:" + "a" * 64)

    class Provider:
        def __init__(self):
            self.outputs = [
                "bad",
                json.dumps(Fixture.action("a.txt", "one")),
                "bad again",
                json.dumps(Fixture.action("b.txt", "two")),
            ]
            self.calls = 0

        async def complete(self, request):
            self.calls += 1
            return ProviderResponse(
                pin=pin,
                content=self.outputs.pop(0),
                usage=ProviderUsage(input_tokens=10, output_tokens=10),
            )

    provider = Provider()
    fixture.services.planner = GatewayPlanner(provider, pin, fixture.parser)
    result = run(fixture, fixture.goal({"a.txt": "one", "b.txt": "two"}))
    assert result["status"] == "succeeded" and provider.calls == 4 and fixture.calls == 2
    assert (fixture.workspace / "b.txt").read_text() == "two"
    assert result["remaining"]["schema_repairs"] == 1
    assert result["remaining"]["repairs_used"] == 2
    assert result["remaining"]["model_requests"] == 4


def test_model_budget_does_not_reset_when_reopening_checkpoint(tmp_path):
    fixture = Fixture(tmp_path)

    async def stop():
        async with agent(fixture.services, interrupt_after=["propose"]) as runner:
            return await runner.start(
                fixture.task, fixture.goal(), budgets=Budgets(model_requests=1)
            )

    first = asyncio.run(stop())
    assert first["remaining"]["model_requests"] == 0
    reopened = Fixture(tmp_path, decisions=[])

    async def resume():
        async with agent(reopened.services) as runner:
            return await runner.resume(reopened.task)

    result = asyncio.run(resume())
    assert result["status"] == "succeeded" and reopened.plan_calls == 0
    assert result["remaining"]["model_requests"] == 0


def test_existing_f1_note_tool_uses_same_dispatcher_and_native_verifier(tmp_path):
    from victus.agent.output_parser import OutputParser
    from victus.tools.contracts import NoteArguments
    from victus.tools.filesystem import fs_create_note
    from victus.workflows.common import context_for

    fixture = Fixture(
        tmp_path,
        decisions=[
            {
                "decision": "action",
                "action": {
                    "tool": "fs.create_note",
                    "arguments": {"filename": "note.txt", "text": "ready"},
                },
            }
        ],
    )
    fixture.dispatcher.registry.register(fs_create_note())
    fixture.parser = OutputParser({"fs.create_note": NoteArguments})
    fixture.services.parser = fixture.parser
    fixture.services.context_factory = lambda state: context_for(
        fixture.workspace, state["task_id"], None, {"fs:write"}, lambda tool, args: True
    )
    result = run(fixture)
    assert (
        result["status"] == "succeeded"
        and (fixture.workspace / "note.txt").read_bytes() == b"ready"
    )
    record = fixture.context(result).ledger.get(result["action_ledger_refs"][0])
    assert record.status == "verified" and record.tool_name == "fs.create_note"


def test_interrupted_finalization_recovers_to_terminal_unknown(tmp_path):
    fixture = Fixture(tmp_path)

    async def stop():
        async with agent(fixture.services, interrupt_after=["verify"]) as runner:
            return await runner.start(fixture.task, fixture.goal())

    first = asyncio.run(stop())
    assert first["next_node"] == "finalize"
    fixture.store.claim(fixture.task, first["sequence"], "finalize")

    async def resume():
        async with agent(fixture.services) as runner:
            return await runner.resume(fixture.task)

    result = asyncio.run(resume())
    assert result["status"] == "unknown" and result["next_node"] == "end" and fixture.calls == 1
