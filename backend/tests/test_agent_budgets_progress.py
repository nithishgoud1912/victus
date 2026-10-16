"""7C limits with real persistent graph and deterministic local domain services."""

import asyncio
import json
import time

import pytest
from graph_support import Fixture

from victus.agent.budgets import (
    Budgets,
    charge_planning,
    charge_time,
    pause_for_approval,
    resume_approval,
)
from victus.agent.graph import agent
from victus.agent.progress import ProgressState, assess, fingerprint
from victus.agent.services import GatewayPlanner
from victus.models.contracts import ErrorCode, ModelError, ModelPin
from victus.models.gateway import RequestBudget


def run(fixture, budgets=None, goal=None):
    async def invoke():
        async with agent(fixture.services) as runner:
            return await runner.start(fixture.task, goal or fixture.goal(), budgets=budgets)

    return asyncio.run(invoke())


def test_defaults_are_independent_and_finite():
    budget = Budgets()
    assert (budget.actions, budget.model_requests, budget.schema_repairs) == (12, 8, 1)
    assert budget.active_seconds == 180 and budget.recursion_limit == 80
    assert budget.approval_timeout_seconds == 60


def test_active_clock_and_approval_expiry_are_separate():
    left = charge_time(Budgets(deadline_epoch=200.0).model_dump(), 12.5)
    waiting = pause_for_approval(left, now=100.0)
    assert waiting["active_seconds"] == 167.5
    assert pause_for_approval(waiting, now=110.0) == waiting
    resumed, valid = resume_approval(waiting, now=140.0)
    assert valid and resumed["active_seconds"] == left["active_seconds"]
    assert resumed["deadline_epoch"] == 240.0
    assert resumed["approval_expires_epoch"] == 160.0
    waiting_again = pause_for_approval(resumed, now=145.0)
    _, valid = resume_approval(waiting_again, now=160.0)
    assert not valid  # Repeated polling cannot renew the approval wait.


def test_repair_consumes_shared_requests_without_destroying_next_decision_allowance():
    left = charge_planning(Budgets().model_dump(), 2, 1024, 1)
    assert left["model_requests"] == 6 and left["schema_repairs"] == 1
    assert left["repairs_used"] == 1
    assert charge_planning(left, 2, 1024, 1)["model_requests"] == 4


def test_one_repair_per_decision_even_when_other_shared_allowances_remain():
    budget = RequestBudget()
    budget.reserve(10, decision_id="one")
    budget.reserve(10, repair=True, decision_id="one")
    with pytest.raises(ModelError):
        budget.reserve(10, repair=True, decision_id="one")
    budget.reserve(10, repair=True, decision_id="two")
    assert budget.snapshot()["requests"] == 3


def test_equivalence_ignores_ids_order_and_fresh_target_handles():
    one = {
        "observation_id": "one",
        "timestamp": "earlier",
        "text": "same",
        "targets": [{"ref": "old", "role": "button", "label": "Save"}],
    }
    two = {
        "targets": [{"ref": "new", "label": "Save", "role": "button"}],
        "observation_id": "two",
        "text": "same",
        "timestamp": "later",
    }
    a = {"tool": "browser.click", "arguments": {"target_ref": "old", "observation_id": "one"}}
    b = {"arguments": {"observation_id": "two", "target_ref": "new"}, "tool": "browser.click"}
    assert fingerprint(a, one) == fingerprint(b, two)
    assert fingerprint(a, one) != fingerprint(a, {**one, "text": "saved"})
    assert fingerprint({**a, "tool": "browser.read"}, one) != fingerprint(a, one)


def test_same_label_targets_and_changed_arguments_are_not_equivalent():
    observation = {"targets": [{"ref": "a", "label": "Save"}, {"ref": "b", "label": "Save"}]}
    assert fingerprint({"target_ref": "a"}, observation) != fingerprint(
        {"target_ref": "b"}, observation
    )
    assert fingerprint({"arguments": {"text": "one"}}, {}) != fingerprint(
        {"arguments": {"text": "two"}}, {}
    )


def test_loop_history_survives_alternating_proposals_and_serialization():
    state = ProgressState().model_dump()
    state, verdict = assess(state, {"tool": "one"}, {})
    assert verdict == "continue"
    state, _ = assess(state, {"tool": "two"}, {})
    state, verdict = assess(state, {"tool": "one"}, {})
    assert verdict == "recover"
    state = json.loads(json.dumps(state))
    state, verdict = assess(state, {"tool": "one"}, {})
    assert verdict == "stop"
    assert "one" not in repr(state)  # Only digests enter checkpoint history.


def test_unchanged_observation_loop_stops_partial_after_one_recovery(tmp_path):
    fixture = Fixture(tmp_path, decisions=[Fixture.action("a.txt", "one")] * 6)
    result = run(fixture, goal=fixture.goal({"a.txt": "one", "missing.txt": "two"}))
    assert result["status"] == "partial" and result["error_code"] == "NO_PROGRESS"
    assert fixture.plan_calls == 3 and fixture.calls == 1
    assert result["remaining"]["model_requests"] == 5
    assert result["remaining"]["actions"] == 11
    assert result["evidence_refs"] and len(result["action_ledger_refs"]) == 1


def test_loop_guard_survives_checkpoint_reopen(tmp_path):
    fixture = Fixture(tmp_path, decisions=[Fixture.action("a.txt", "one")] * 6)
    fixture.goal_expected = {"a.txt": "one", "missing.txt": "two"}

    async def invoke():
        async with agent(fixture.services, interrupt_after=["recover"]) as runner:
            first = await runner.start(fixture.task, fixture.goal(fixture.goal_expected))
        assert first["next_node"] == "observe"
        plans = fixture.plan_calls
        async with agent(fixture.services) as runner:
            result = await runner.resume(fixture.task)
        assert fixture.plan_calls == plans + 1
        return result

    result = asyncio.run(invoke())
    assert result["status"] == "partial" and fixture.calls == 1


def test_global_model_limit_stops_eighth_attempt_without_ninth_call(tmp_path):
    fixture = Fixture(tmp_path, decisions=[Fixture.action(f"n{i}.txt", str(i)) for i in range(12)])
    result = run(fixture, goal=fixture.goal({"missing.txt": "not complete"}))
    assert fixture.plan_calls == fixture.calls == 8
    assert result["remaining"]["model_requests"] == 0
    assert result["remaining"]["actions"] == 4 and result["status"] == "partial"


def test_twelve_action_attempts_are_shared_across_plans(tmp_path):
    fixture = Fixture(tmp_path, decisions=[Fixture.action(f"n{i}.txt", str(i)) for i in range(16)])
    result = run(
        fixture,
        Budgets(model_requests=20, observations=20, nodes=200, recursion_limit=200),
        fixture.goal({"missing.txt": "not complete"}),
    )
    assert fixture.calls == 12 and result["remaining"]["actions"] == 0
    assert result["status"] == "partial" and result["error_code"] == "AGENT_BUDGET_EXHAUSTED"


def test_failed_model_request_charges_actual_attempt_not_an_unused_repair(tmp_path):
    fixture = Fixture(tmp_path)

    class Provider:
        async def complete(self, request):
            raise ModelError(ErrorCode.UNAVAILABLE)

    fixture.services.planner = GatewayPlanner(
        Provider(), ModelPin(name="fixture:1", digest="sha256:" + "a" * 64), fixture.parser
    )
    result = run(fixture)
    assert result["remaining"]["model_requests"] == 7
    assert result["remaining"]["repairs_used"] == 0 and fixture.calls == 0


def test_active_time_interrupts_slow_planning(tmp_path):
    fixture = Fixture(tmp_path)

    async def slow(*args):
        await asyncio.sleep(10)

    fixture.services.planner = slow
    result = run(fixture, Budgets(active_seconds=0.5))
    assert result["status"] == "blocked" and fixture.calls == 0
    assert result["remaining"]["active_seconds"] == 0
    assert result["error_code"] in {"AGENT_ACTIVE_TIME_EXHAUSTED", "AGENT_BUDGET_EXHAUSTED"}


def test_approval_pause_preserves_clock_and_expiry_survives_polling(tmp_path):
    fixture = Fixture(tmp_path)
    fixture.approved = None

    async def invoke():
        async with agent(fixture.services) as runner:
            first = await runner.start(fixture.task, fixture.goal())
            assert first["status"] == "awaiting_approval"
            expires = first["remaining"]["approval_expires_epoch"]
            # Simulate forty seconds spent waiting without sleeping in the test.
            snapshot = await runner.graph.aget_state(runner.config(fixture.task))
            left = {
                **snapshot.values["remaining"],
                "approval_started_epoch": time.time() - 40,
                "deadline_epoch": time.time() - 20,
            }
            await runner.graph.aupdate_state(runner.config(fixture.task), {"remaining": left})
            second = await runner.resume(fixture.task)
            assert second["status"] == "awaiting_approval"
            assert second["remaining"]["approval_expires_epoch"] == expires
            assert first["remaining"]["active_seconds"] - second["remaining"]["active_seconds"] < 5
            fixture.approved = True
            fixture.resolve_review()
            return await runner.resume(fixture.task)

    result = asyncio.run(invoke())
    assert result["status"] == "succeeded" and fixture.calls == 1


def test_expired_approval_cannot_dispatch_on_restart(tmp_path):
    fixture = Fixture(tmp_path)
    fixture.approved = None

    async def invoke():
        async with agent(fixture.services) as runner:
            await runner.start(fixture.task, fixture.goal())
            snapshot = await runner.graph.aget_state(runner.config(fixture.task))
            left = {**snapshot.values["remaining"], "approval_expires_epoch": time.time() - 1}
            await runner.graph.aupdate_state(runner.config(fixture.task), {"remaining": left})
        fixture.approved = True
        async with agent(fixture.services) as runner:
            return await runner.resume(fixture.task)

    result = asyncio.run(invoke())
    assert result["status"] == "blocked" and result["error_code"] == "APPROVAL_WAIT_EXPIRED"
    assert fixture.calls == 0


def test_approval_expiring_during_revalidation_cannot_execute(tmp_path):
    fixture = Fixture(tmp_path)
    fixture.approved = None

    async def invoke():
        async with agent(fixture.services) as runner:
            await runner.start(fixture.task, fixture.goal())
            snapshot = await runner.graph.aget_state(runner.config(fixture.task))
            left = {**snapshot.values["remaining"], "approval_expires_epoch": time.time() + 0.1}
            await runner.graph.aupdate_state(runner.config(fixture.task), {"remaining": left})

            async def slow_validation(state, action):
                await asyncio.sleep(0.25)
                return True

            fixture.services.validator = slow_validation
            fixture.approved = True
            fixture.resolve_review()
            store = fixture.services.approvals(snapshot.values)
            with store.connect() as db:
                db.execute("UPDATE approvals SET expires_at=?", (time.time() + 0.1,))
            return await runner.resume(fixture.task)

    result = asyncio.run(invoke())
    assert result["status"] == "blocked" and result["error_code"] in {
        "APPROVAL_WAIT_EXPIRED",
        "APPROVAL_OR_TARGET_STALE",
    }
    assert fixture.calls == 0


def test_finish_wording_is_not_semantic_progress():
    one = {"decision": "finish", "status": "completed", "reason": "Done"}
    two = {**one, "reason": "Everything is finished"}
    assert fingerprint(one, {}) == fingerprint(two, {})


def test_recursion_limit_stops_truthfully_without_raising_or_growing(tmp_path):
    fixture = Fixture(tmp_path)
    result = run(fixture, Budgets(recursion_limit=2))
    assert result["status"] == "blocked" and fixture.calls == 0
    assert result["error_code"] == "GRAPH_RECURSION_EXHAUSTED"
    assert result["remaining"]["recursion_limit"] == 2

    async def reopen():
        async with agent(fixture.services) as runner:
            return await runner.resume(fixture.task)

    assert asyncio.run(reopen())["error_code"] == "GRAPH_RECURSION_EXHAUSTED"
