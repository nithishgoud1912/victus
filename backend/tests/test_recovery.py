"""Recovery preserves uncertainty, limits retries and requires approved reversals."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

import pytest

from victus.agent.budgets import Budgets
from victus.recovery.compensation import CompensationManager, CompensationSpec
from victus.recovery.reconcile import EffectProof, Reconciler
from victus.recovery.resume import ResumeManager
from victus.recovery.retry import RetryManager
from victus.safety.approvals import ApprovalBinding, ApprovalStore, argument_hash
from victus.safety.permits import PermitStore
from victus.storage.action_ledger import ActionLedger
from victus.storage.migrations import migrate
from victus.storage.payloads import PayloadStore
from victus.tasks.events import EventManager
from victus.tools.dispatcher import Dispatcher
from victus.tools.registry import RetryClass, ToolRegistry
from victus.tools.steps import StepContext
from victus.workflows.common import Arguments, spec


class Args(Arguments):
    value: str


@pytest.fixture
def recovery(tmp_path):
    path = tmp_path / "victus.sqlite3"
    migrate(path)
    ledger, payloads = ActionLedger(path), PayloadStore(path)
    args = {"value": "approved"}
    action_id = ledger.prepare_action(
        "fixture.forward", "0.1.0", args, expected_effect_ref="task:old"
    )
    payloads.store(action_id, "arguments", args)
    ledger.mark_dispatching(action_id)
    ledger.mark_unknown(action_id, error_code="TIMEOUT")
    return ledger, payloads, action_id, Reconciler(ledger, payloads, timeout_seconds=0.05)


async def present(record, args):
    return EffectProof("present", {"receipt_id": "receipt-1"})


async def absent(record, args):
    return EffectProof("absent", {"lookup": "authoritative_not_found"})


@pytest.mark.parametrize("verdict", ["present", "absent", "unknown"])
def test_reconciliation_preserves_unknown_history_and_retains_evidence(recovery, verdict):
    ledger, payloads, action_id, reconciler = recovery

    async def probe(record, args):
        assert record.action_id == action_id and args == {"value": "approved"}
        return EffectProof(verdict, {"receipt_id": "receipt-1"} if verdict != "unknown" else {})

    reconciler.register("fixture.forward", "0.1.0", probe)
    result = asyncio.run(reconciler.reconcile(action_id, quiesced=True))
    assert ledger.get(action_id).status == "unknown"
    assert result.verdict == verdict and reconciler.latest(action_id) == result
    if verdict != "unknown":
        assert payloads.get(result.evidence_ref).action_id == action_id


@pytest.mark.parametrize(
    "problem",
    ["unsupported", "version", "missing", "expired", "changed", "failure", "deadline", "empty"],
)
def test_unsupported_or_unprovable_effect_stays_unknown(recovery, problem):
    ledger, _, action_id, reconciler = recovery

    async def probe(*_):
        if problem == "failure":
            raise RuntimeError("PRIVATE exception data")
        if problem == "deadline":
            await asyncio.sleep(1)
        return EffectProof("present", {} if problem == "empty" else {"receipt_id": "receipt-1"})

    if problem != "unsupported":
        reconciler.register("fixture.forward", "wrong" if problem == "version" else "0.1.0", probe)
    with ledger._connect() as db:
        if problem == "missing":
            db.execute("DELETE FROM payloads")
        elif problem == "expired":
            db.execute("UPDATE payloads SET expires_at='2000-01-01T00:00:00.000000Z'")
        elif problem == "changed":
            db.execute("UPDATE payloads SET data_json='{}'")
    result = asyncio.run(reconciler.reconcile(action_id, quiesced=True))
    assert result.verdict == "unknown" and result.evidence_ref is None
    assert ledger.get(action_id).status == "unknown"


def test_reconciliation_requires_stopped_owner_and_no_sync_native_probe(recovery):
    _, _, action_id, reconciler = recovery
    with pytest.raises(PermissionError):
        asyncio.run(reconciler.reconcile(action_id, quiesced=False))
    with pytest.raises(TypeError):
        reconciler.register("tool", "1", lambda *_: True)


def test_unfinished_probe_marks_uncertain_dispatch_unknown(recovery):
    ledger, payloads, _, reconciler = recovery
    action_id = ledger.prepare_action("fixture.forward", "0.1.0", {"value": "pending"})
    payloads.store(action_id, "arguments", {"value": "pending"})
    ledger.mark_dispatching(action_id)
    reconciler.register("fixture.forward", "0.1.0", present)
    results = asyncio.run(reconciler.unfinished(quiesced=True))
    assert len(results) == 2 and all(result.verdict == "present" for result in results)
    assert ledger.get(action_id).status == "unknown"


def tool(*, retry=RetryClass.SAFE, write=False):
    return replace(
        spec("fixture.forward", Args, lambda *_: {}, lambda *_: True, "fixture:read"),
        retry_class=retry,
        external_write=write,
    )


def test_retry_count_and_shared_budget_persist_across_reopen(recovery):
    ledger, _, action_id, _ = recovery
    left = Budgets(actions=3, recoveries=2, model_requests=4).model_dump()
    first = RetryManager(ledger, max_retries=2).reserve(
        action_id, tool(), left, cancelled=lambda: False
    )
    second = RetryManager(ActionLedger(ledger.db_path), max_retries=2).reserve(
        action_id, tool(), left, cancelled=lambda: False
    )
    assert first.remaining["actions"] == 2 and second.remaining["actions"] == 1
    assert second.remaining["recoveries"] == 0 and second.remaining["model_requests"] == 4
    with pytest.raises(PermissionError):
        RetryManager(ledger, max_retries=2).reserve(
            action_id, tool(), left, cancelled=lambda: False
        )


def test_concurrent_retry_reservations_never_exceed_bound(recovery):
    ledger, _, action_id, _ = recovery

    def reserve(_):
        try:
            return (
                RetryManager(ledger, max_retries=2)
                .reserve(action_id, tool(), Budgets().model_dump(), cancelled=lambda: False)
                .retry_number
            )
        except PermissionError:
            return None

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(reserve, range(12)))
    assert sorted(value for value in results if value) == [1, 2]


@pytest.mark.parametrize("reason", ["unsafe", "external", "cancel", "actions", "time", "version"])
def test_retry_deny_cases_do_not_reserve(recovery, reason):
    ledger, _, action_id, _ = recovery
    selected = tool(
        retry=RetryClass.NONE if reason == "unsafe" else RetryClass.IDEMPOTENT,
        write=reason == "external",
    )
    if reason == "version":
        selected = replace(selected, version="changed")
    left = Budgets(
        actions=0 if reason == "actions" else 12, active_seconds=0 if reason == "time" else 180
    ).model_dump()
    with pytest.raises(PermissionError):
        RetryManager(ledger).reserve(
            action_id, selected, left, cancelled=lambda: reason == "cancel"
        )
    with ledger._connect() as db:
        assert db.execute("SELECT count(*) FROM recovery_retries").fetchone()[0] == 0


@pytest.mark.parametrize("verdict", ["present", "unknown", "absent", "stale"])
def test_external_retry_requires_explicit_review_and_fresh_absence(recovery, verdict):
    ledger, _, action_id, reconciler = recovery
    if verdict != "unknown":
        reconciler.register("fixture.forward", "0.1.0", present if verdict == "present" else absent)
        asyncio.run(reconciler.reconcile(action_id, quiesced=True))
    if verdict == "stale":
        with ledger._connect() as db:
            db.execute("UPDATE recovery_reconciliations SET created_at='2000-01-01T00:00:00.000Z'")
    manager = RetryManager(ledger)
    with pytest.raises(PermissionError):
        manager.reserve(
            action_id, tool(write=True), Budgets().model_dump(), cancelled=lambda: False
        )
    if verdict == "absent":
        assert (
            manager.reserve(
                action_id,
                tool(write=True),
                Budgets().model_dump(),
                automatic=False,
                cancelled=lambda: False,
            ).retry_number
            == 1
        )
    else:
        with pytest.raises(PermissionError):
            manager.reserve(
                action_id,
                tool(write=True),
                Budgets().model_dump(),
                automatic=False,
                cancelled=lambda: False,
            )


def test_resume_invalidates_old_authority_never_calls_executor(recovery):
    ledger, _, action_id, reconciler = recovery
    approvals = ApprovalStore(ledger.db_path)
    binding = ApprovalBinding(
        task_id="old",
        action_id=action_id,
        tool_name="fixture.forward",
        tool_version="0.1.0",
        canonical_args_hash=argument_hash({"value": "approved"}),
        policy_version="1",
        target_identity="recipient",
        observation_identity="old-observation",
    )
    record = approvals.request(binding, {"text": "preview"})
    approvals.decide(record.approval_id, binding, approved=True)
    token = PermitStore(approvals).issue_permit(record.approval_id, binding)
    reconciler.register("fixture.forward", "0.1.0", present)
    reports = asyncio.run(
        ResumeManager(ledger, approvals).resume(reconciler, quiesced=True, task_id="old")
    )
    assert (
        reports[0].verdict == "present" and approvals.get(record.approval_id).state == "invalidated"
    )
    with pytest.raises(PermissionError):
        PermitStore(approvals).consume_permit(token, binding, cancelled=lambda: False)
    assert ledger.get(action_id).status == "unknown"


@pytest.mark.parametrize("allowed", [False, True])
def test_only_supported_compensation_executes_through_new_policy_and_permit(
    recovery, tmp_path, allowed
):
    ledger, payloads, action_id, reconciler = recovery
    registry = ToolRegistry()
    effects = []
    reverse = spec(
        "fixture.reverse",
        Args,
        lambda _, args: effects.append(args.value) or {"reversed": args.value},
        lambda output, args: output["reversed"] == args.value,
        "fixture:reverse",
    )
    registry.register(reverse)
    manager = CompensationManager(reconciler, registry)
    with pytest.raises(PermissionError):
        manager.offer(action_id)
    reconciler.register("fixture.forward", "0.1.0", present)
    asyncio.run(reconciler.reconcile(action_id, quiesced=True))
    manager.register(
        CompensationSpec(
            "fixture.forward",
            "0.1.0",
            reverse.name,
            reverse.version,
            lambda args, evidence: {"value": evidence["receipt_id"]},
        )
    )
    proposal = manager.offer(action_id)
    new_id = ledger.prepare_action(
        reverse.name, reverse.version, proposal.arguments, expected_effect_ref="task:reverse"
    )
    binding = ApprovalBinding(
        task_id="reverse",
        action_id=new_id,
        tool_name=reverse.name,
        tool_version=reverse.version,
        canonical_args_hash=argument_hash(proposal.arguments),
        policy_version="1",
        target_identity="receipt-1",
        observation_identity="new-observation",
    )
    approvals = ApprovalStore(ledger.db_path)
    approval = approvals.request(binding, {"receipt_id": "receipt-1"})
    approvals.decide(approval.approval_id, binding, approved=True)
    permits = PermitStore(approvals)
    context = StepContext(
        "reverse",
        frozenset({"fixture:reverse"}),
        lambda *_: allowed,
        ledger,
        payloads,
        EventManager(ledger.db_path),
        Event(),
        prepared_action_id=new_id,
        permits=permits,
        permit_token=permits.issue_permit(approval.approval_id, binding),
        approval_binding=binding,
        revalidate_binding=lambda: binding,
    )
    dispatcher = Dispatcher(tmp_path, registry)
    outcome = asyncio.run(manager.dispatch(action_id, proposal, dispatcher, context))
    assert outcome.status == ("succeeded" if allowed else "blocked")
    assert effects == (["receipt-1"] if allowed else [])
    again = asyncio.run(manager.dispatch(action_id, proposal, dispatcher, context))
    assert again.status == "blocked" and len(effects) == int(allowed)
