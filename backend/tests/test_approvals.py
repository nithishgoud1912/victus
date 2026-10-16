"""8A record, retention, migration and concurrent permit invariants."""

import hashlib
import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from victus.safety.approvals import ApprovalBinding, ApprovalStore, argument_hash
from victus.safety.permits import PermitStore
from victus.storage.migrations import migrate


@pytest.fixture
def setup(tmp_path):
    path = tmp_path / "victus.sqlite3"
    migrate(path)
    clock = [1000.0]
    store = ApprovalStore(path, clock=lambda: clock[0])
    binding = ApprovalBinding(
        task_id="task-1",
        action_id="action-1",
        tool_name="fs.create_note",
        tool_version="1",
        canonical_args_hash=argument_hash({"text": "private text"}),
        policy_version="policy-1",
        target_identity="workspace:note.txt",
        observation_identity="observation-1",
    )
    return store, binding, clock


def request(setup):
    store, binding, _ = setup
    return store.request(binding, {"text": "private text"})


def approve(setup):
    store, binding, _ = setup
    record = request(setup)
    return store.decide(record.approval_id, binding, approved=True)


def test_hash_matches_supplied_algorithm():
    args = {"z": [True, None, 1], "a": "తెలుగు"}
    encoded = json.dumps(
        args, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    assert argument_hash(args) == hashlib.sha256(encoded).hexdigest()
    assert argument_hash(args) == argument_hash(dict(reversed(list(args.items()))))
    assert argument_hash({"text": "a"}) != argument_hash({"text": "b"})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), object()])
def test_hash_rejects_non_json(value):
    with pytest.raises((ValueError, TypeError)):
        argument_hash({"nested": [value]})


def test_pending_record_survives_reopen_without_preview_leak(setup):
    store, binding, clock = setup
    record = request(setup)
    reopened = ApprovalStore(store.db_path, clock=lambda: clock[0])
    assert reopened.get(record.approval_id) == record
    assert record.binding() == binding and record.state == "pending"
    assert "private text" not in record.model_dump_json()
    assert reopened.preview(record.approval_id, task_id=binding.task_id) == {"text": "private text"}
    with sqlite3.connect(store.db_path) as db:
        payload = db.execute("SELECT protected_payload FROM approval_previews").fetchone()[0]
    if os.name == "nt":
        assert payload.startswith(b"dpapi:") and b"private text" not in payload
    else:
        assert store.db_path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(PermissionError):
        store.preview(record.approval_id, task_id="different-task")


def test_denial_is_terminal(setup):
    store, binding, _ = setup
    record = request(setup)
    assert store.decide(record.approval_id, binding, approved=False).state == "denied"
    with pytest.raises(PermissionError):
        store.decide(record.approval_id, binding, approved=True)
    with pytest.raises(PermissionError):
        PermitStore(store).issue(record.approval_id, binding)


@pytest.mark.parametrize("field", list(ApprovalBinding.model_fields))
@pytest.mark.parametrize("phase", ["decide", "issue", "consume"])
def test_every_binding_is_checked_and_mismatch_invalidates(setup, field, phase):
    store, binding, _ = setup
    record = request(setup)
    changed = binding.model_copy(
        update={field: "0" * 64 if field == "canonical_args_hash" else "other"}
    )
    permits = PermitStore(store)
    token = None
    if phase != "decide":
        store.decide(record.approval_id, binding, approved=True)
    if phase == "consume":
        token = permits.issue(record.approval_id, binding)
    with pytest.raises(PermissionError):
        if phase == "decide":
            store.decide(record.approval_id, changed, approved=True)
        elif phase == "issue":
            permits.issue(record.approval_id, changed)
        else:
            permits.consume(token, changed)
    assert store.get(record.approval_id).state == "invalidated"
    with pytest.raises(PermissionError):
        permits.issue(record.approval_id, binding)


@pytest.mark.parametrize("phase", ["pending", "approved", "permit"])
def test_expiry_at_exact_boundary(setup, phase):
    store, binding, clock = setup
    record = request(setup)
    permits = PermitStore(store)
    token = None
    if phase != "pending":
        store.decide(record.approval_id, binding, approved=True)
    if phase == "permit":
        token = permits.issue(record.approval_id, binding)
    clock[0] = record.expires_at
    with pytest.raises(PermissionError):
        if phase == "pending":
            store.decide(record.approval_id, binding, approved=True)
        elif phase == "approved":
            permits.issue(record.approval_id, binding)
        else:
            permits.consume(token, binding)
    assert store.get(record.approval_id).state == "expired"
    with pytest.raises(PermissionError):
        store.preview(record.approval_id, task_id=binding.task_id)


def test_purge_removes_body_preserves_metadata(setup):
    store, _, clock = setup
    record = request(setup)
    clock[0] = record.expires_at + 1
    assert store.purge_expired() == 1
    assert store.purge_expired() == 0
    with sqlite3.connect(store.db_path) as db:
        assert db.execute("SELECT protected_payload FROM approval_previews").fetchone()[0] is None
    assert store.get(record.approval_id).state == "expired"


def test_invalidation_revokes_outstanding_permit(setup):
    store, binding, _ = setup
    record = approve(setup)
    permits = PermitStore(store)
    token = permits.issue(record.approval_id, binding)
    assert store.invalidate(record.approval_id)
    assert not store.invalidate(record.approval_id)
    with pytest.raises(PermissionError):
        permits.consume(token, binding)


def test_pending_cannot_issue_and_unreviewed_preview_cannot_change(setup):
    store, binding, _ = setup
    record = request(setup)
    with pytest.raises(PermissionError):
        PermitStore(store).issue(record.approval_id, binding)
    with pytest.raises(TypeError):
        store.decide(record.approval_id, binding, approved=1)


def test_concurrent_single_issue_and_consume_across_reopen(setup):
    store, binding, clock = setup
    record = approve(setup)

    def issue(_):
        try:
            return PermitStore(ApprovalStore(store.db_path, clock=lambda: clock[0])).issue(
                record.approval_id, binding
            )
        except PermissionError:
            return None

    with ThreadPoolExecutor(max_workers=6) as pool:
        tokens = [token for token in pool.map(issue, range(12)) if token]
    assert len(tokens) == 1
    with sqlite3.connect(store.db_path) as db:
        assert db.execute("SELECT token_hash FROM approval_permits").fetchone()[0] != tokens[0]

    def consume(_):
        try:
            return (
                PermitStore(ApprovalStore(store.db_path, clock=lambda: clock[0]))
                .consume(tokens[0], binding)
                .state
            )
        except PermissionError:
            return None

    with ThreadPoolExecutor(max_workers=6) as pool:
        outcomes = list(pool.map(consume, range(12)))
    assert outcomes.count("consumed") == 1
    assert store.get(record.approval_id).state == "consumed"
    assert not store.invalidate(record.approval_id)
    with pytest.raises(PermissionError):
        PermitStore(store).issue(record.approval_id, binding)


@pytest.mark.parametrize("ttl", [0, -1, 301, float("nan"), float("inf")])
def test_invalid_retention_rejected(setup, ttl):
    store, binding, _ = setup
    with pytest.raises(ValueError):
        store.request(binding, {}, ttl_seconds=ttl)


def test_migration_invalidates_legacy_and_preserves_action_audit(tmp_path, monkeypatch):
    from victus.storage import migrations

    path = tmp_path / "legacy.sqlite3"
    discover = migrations._discover_migrations
    monkeypatch.setattr(migrations, "_discover_migrations", lambda: discover()[:4])
    migrate(path)
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO approvals(approval_id,action_id,decision,reason) VALUES(?,?,?,?)",
            ("old", "action", "approved", "old audit reason"),
        )
    monkeypatch.setattr(migrations, "_discover_migrations", discover)
    assert migrate(path) == [version for version, _ in discover() if version > 4]
    assert migrate(path) == []
    store = ApprovalStore(path)
    assert store.get("old").state == "invalidated"
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT reason FROM approvals_legacy").fetchone()[0] == "old audit reason"


def test_failed_migration_rolls_back_schema_and_version(tmp_path, monkeypatch):
    from victus.storage import migrations

    path = tmp_path / "legacy.sqlite3"
    discover = migrations._discover_migrations
    monkeypatch.setattr(migrations, "_discover_migrations", lambda: discover()[:4])
    migrate(path)
    broken = tmp_path / "0005_broken.sql"
    real_sql = discover()[4][1].read_text(encoding="utf-8")
    broken.write_text(real_sql + "\nTHIS IS INVALID SQL;", encoding="utf-8")
    monkeypatch.setattr(migrations, "_discover_migrations", lambda: discover()[:4] + [(5, broken)])
    with pytest.raises(sqlite3.OperationalError):
        migrate(path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT max(version) FROM schema_versions").fetchone()[0] == 4
        assert "decision" in {r[1] for r in db.execute("PRAGMA table_info(approvals)")}
        assert not db.execute(
            "SELECT name FROM sqlite_master WHERE name='approvals_legacy'"
        ).fetchall()
    monkeypatch.setattr(migrations, "_discover_migrations", discover)
    assert migrate(path) == [version for version, _ in discover() if version > 4]


def test_protection_failure_never_stores_plaintext(setup, monkeypatch):
    from victus.safety import approvals

    store, binding, _ = setup

    def unavailable(_):
        raise OSError("DPAPI unavailable")

    monkeypatch.setattr(approvals, "protect", unavailable)
    with pytest.raises(OSError):
        store.request(binding, {"secret": "not retained"})
    with sqlite3.connect(store.db_path) as db:
        assert db.execute("SELECT count(*) FROM approvals").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM approval_previews").fetchone()[0] == 0


def test_unknown_and_forged_records_or_permits_fail_closed(setup):
    store, binding, _ = setup
    assert store.get("missing") is None
    assert not store.invalidate("missing")
    with pytest.raises(PermissionError):
        store.decide("missing", binding, approved=True)
    with pytest.raises(PermissionError):
        PermitStore(store).issue("missing", binding)
    for token in ("fake", "a" * 43):
        with pytest.raises(PermissionError):
            PermitStore(store).consume(token, binding)


@pytest.mark.parametrize(
    "preview", [{"large": "x" * 128001}, {"bad": float("nan")}], ids=["oversized", "nonfinite"]
)
def test_preview_boundaries(setup, preview):
    store, binding, _ = setup
    with pytest.raises(ValueError):
        store.request(binding, preview)
