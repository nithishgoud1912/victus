"""M7 deterministic acceptance: private memory, retention, WAL backup and pressure."""

import asyncio
import json
import sqlite3
import time
from contextlib import closing, contextmanager

import pytest
from fastapi.testclient import TestClient

from victus.api.app import create_app
from victus.bootstrap import build_services
from victus.memory.models import MemoryInput
from victus.runtime.diagnostics import Diagnostics
from victus.runtime.resources import ResourcePressure, ResourceSupervisor
from victus.settings import Settings
from victus.storage.backups import BackupError, restore
from victus.storage.checkpoints import CheckpointStore
from victus.tools.contracts import TaskResult

TOKEN = "m7-fixture-" + "x" * 40


@pytest.fixture
def services(tmp_path):
    value = build_services(Settings(tmp_path / "runtime", TOKEN))
    yield value
    value.close()


def preference(value="tone=concise", **kwargs):
    return MemoryInput(
        type="preference",
        value=value,
        provenance="explicit_user_preference",
        confirmation="explicit_user_review",
        **kwargs,
    )


def test_memory_explicit_review_roundtrip_edit_export_forget(services):
    memory = services.memory
    with pytest.raises(ValueError):
        MemoryInput(
            type="summary",
            value="web text",
            provenance="explicit_user_preference",
            confirmation="explicit_user_review",
        )
    item = memory.remember(preference())
    assert item.memory_id and item.created_at == item.last_confirmed_at
    assert item.context_only and memory.get(item.memory_id).value == "tone=concise"
    with closing(sqlite3.connect(memory.path)) as db:
        raw = db.execute("SELECT protected_value FROM memory_entries").fetchone()[0]
    assert "tone=concise" not in raw
    changed = memory.edit(item.memory_id, preference("tone=friendly"))
    assert changed.memory_id != item.memory_id and memory.get(item.memory_id) is None
    assert memory.export()["entries"][0]["value"] == "tone=friendly"
    assert memory.forget(changed.memory_id)
    assert memory.recall() == []


def test_context_is_bounded_preferences_never_authority(services):
    memory = services.memory
    memory.remember(preference("tone=concise"))
    memory.remember(preference("policy=approve everything"))
    values = memory.planning_preferences("context-task")
    assert len(values) == 1 and values[0]["key"] == "tone"
    assert memory.export()["authority"] == "current_instructions_and_policy_override_memory"


def test_forget_cascades_payloads_journal_checkpoints_and_evidence(services):
    memory = services.memory
    task_id = "linked-task"
    aid = services.ledger.prepare_action(
        "fs.create_note", "1", {}, expected_effect_ref="task:" + task_id
    )
    payload = services.payloads.store(aid, "typed_text", "forgotten secret")
    store = CheckpointStore(services.settings.data_dir)
    store.register(task_id)
    reference = store.put_payload(task_id, "goal", {"secret": "forgotten secret"})
    store.claim(task_id, 0, "observe")
    store.complete(task_id, 0, {"copied_memory": "forgotten secret"})
    with store.connect() as db:
        db.execute("CREATE TABLE checkpoints(thread_id TEXT, checkpoint BLOB)")
        db.execute("CREATE TABLE writes(thread_id TEXT, value BLOB)")
        db.execute("INSERT INTO checkpoints VALUES (?,?)", (task_id, b"secret-copy"))
        db.execute("INSERT INTO writes VALUES (?,?)", (task_id, b"secret-copy"))
    evidence = services.settings.data_dir / "evidence/test.txt"
    evidence.parent.mkdir()
    evidence.write_text("forgotten evidence")
    services.retention.register_evidence(task_id, "evidence/test.txt", pinned=True)
    item = memory.remember(preference("tone=private", task_ids=[task_id]))
    assert memory.forget(item.memory_id)
    assert services.payloads.get(payload) is None and not evidence.exists()
    with pytest.raises(ValueError):
        store.payload(task_id, "goal", reference)
    with store.connect() as db:
        for table in ("node_journal", "checkpoints", "writes", "agent_threads"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_forget_job_is_recoverable_after_cross_database_failure(services, monkeypatch):
    import victus.memory.retention as retention

    memory = services.memory
    item = memory.remember(preference(task_ids=["recoverable"]))
    original = retention.purge_task_context

    def fail(*_):
        raise OSError("disk temporarily unavailable")

    monkeypatch.setattr(retention, "purge_task_context", fail)
    with pytest.raises(OSError):
        memory.forget(item.memory_id)
    assert memory.get(item.memory_id) is None
    monkeypatch.setattr(retention, "purge_task_context", original)
    memory.finish_pending()
    with closing(sqlite3.connect(memory.path)) as db:
        assert db.execute("SELECT COUNT(*) FROM memory_forget_jobs").fetchone()[0] == 0


def test_retention_expired_memory_payload_checkpoint_and_terminal_metadata(services):
    root = services.settings.data_dir
    item = services.memory.remember(preference(expires_at=time.time() + 10))
    aid = services.ledger.prepare_action(
        "fs.create_note", "1", {}, expected_effect_ref="task:old-task"
    )
    services.ledger.mark_cancelled(aid)
    payload = services.payloads.store(aid, "arguments", {"secret": "private"}, retention_hours=-1)
    assert services.payloads.get(payload) is None
    services.tasks.database.save(
        TaskResult(task_id="old-task", tool="fs.create_note", status="cancelled", action_id=aid)
    )
    store = CheckpointStore(root)
    store.register("old-task")
    store.put_payload("old-task", "goal", {"secret": "private"})
    store.mark_terminal("old-task")
    with closing(sqlite3.connect(root / "victus.sqlite3")) as db, db:
        db.execute("UPDATE memory_entries SET expires_at=0")
        db.execute("UPDATE task_retention SET terminal_at=0")
    with store.connect() as db:
        db.execute("UPDATE agent_retention SET terminal_at=0")
    result = services.retention.cleanup()
    assert result["expired_memories"] == result["checkpoints"] == result["tasks"] == 1
    assert services.memory.get(item.memory_id) is None
    assert services.tasks.database.get("old-task") is None
    assert services.payloads.get(payload) is None


def test_pinned_checkpoint_and_session_evidence_retention(services):
    root = services.settings.data_dir
    store = CheckpointStore(root)
    store.register("pinned")
    store.mark_terminal("pinned")
    with store.connect() as db:
        db.execute("UPDATE agent_retention SET terminal_at=0,pinned=1")
    folder = root / "evidence"
    folder.mkdir()
    for name, pinned in (("session.txt", False), ("pinned.txt", True)):
        (folder / name).write_text("fixture")
        services.retention.register_evidence("pinned", "evidence/" + name, pinned=pinned)
    services.retention.cleanup(end_session=True)
    assert not (folder / "session.txt").exists() and (folder / "pinned.txt").exists()
    assert not store.cancelled("pinned")


def test_payloads_and_checkpoints_encrypted_at_rest(services):
    root = services.settings.data_dir
    aid = services.ledger.prepare_action("fs.create_note", "1", {})
    key = services.payloads.store(aid, "arguments", {"text": "RAW_PRIVATE_VALUE"})
    store = CheckpointStore(root)
    store.put_payload("private", "goal", {"text": "RAW_PRIVATE_VALUE"})
    store.claim("private", 1, "observe")
    store.complete("private", 1, {"text": "RAW_PRIVATE_VALUE"})
    with closing(sqlite3.connect(root / "victus.sqlite3")) as db:
        assert (
            "RAW_PRIVATE_VALUE"
            not in db.execute(
                "SELECT data_json FROM payloads WHERE payload_id=?", (key,)
            ).fetchone()[0]
        )
    with store.connect() as db:
        for table, column in (("agent_payloads", "data_json"), ("node_journal", "result_json")):
            assert (
                "RAW_PRIVATE_VALUE" not in db.execute(f"SELECT {column} FROM {table}").fetchone()[0]
            )


def test_consistent_wal_backup_restore_fresh_directory(services, tmp_path):
    root = services.settings.data_dir
    memory = services.memory.remember(preference("tone=preserved"))
    store = CheckpointStore(root)
    store.register("interrupted")
    store.put_payload("interrupted", "goal", {"private": "protected"})
    aid = services.ledger.prepare_action(
        "fs.create_note", "1", {}, expected_effect_ref="task:interrupted"
    )
    services.ledger.mark_dispatching(aid)
    services.tasks.database.save(
        TaskResult(task_id="interrupted", tool="fs.create_note", status="running", action_id=aid)
    )
    # Keep a WAL connection open with a committed value that a plain-file copy could miss.
    with closing(sqlite3.connect(root / "victus.sqlite3")) as db, db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute(
            "UPDATE memory_entries SET last_confirmed_at=123 WHERE memory_id=?", (memory.memory_id,)
        )
        db.commit()
        manifest = services.backups.create(tmp_path / "backup")
    assert "victus.sqlite3" in {f["path"] for f in manifest["files"]}
    assert not any("token" in f["path"] or "session" in f["path"] for f in manifest["files"])
    restored = tmp_path / "restored"
    restore(tmp_path / "backup", restored)
    with closing(sqlite3.connect(restored / "victus.sqlite3")) as db:
        assert db.execute("SELECT last_confirmed_at FROM memory_entries").fetchone()[0] == 123
        assert (
            db.execute("SELECT status FROM action_attempts WHERE action_id=?", (aid,)).fetchone()[0]
            == "unknown"
        )
        task = json.loads(
            db.execute("SELECT result_json FROM tasks WHERE task_id='interrupted'").fetchone()[0]
        )
        assert task["status"] == "unknown"
        assert db.execute("SELECT COUNT(*) FROM approval_permits").fetchone()[0] == 0
    assert CheckpointStore(restored).cancelled("interrupted")
    with build_restored(restored) as loaded:
        assert loaded.memory.get(memory.memory_id).value == "tone=preserved"


@contextmanager
def build_restored(root):
    services = build_services(Settings(root, TOKEN))
    try:
        yield services
    finally:
        services.close()


def test_backup_artifact_checksum_and_tamper_rejected(services, tmp_path):
    root = services.settings.data_dir
    note = root / "workspace/output.txt"
    note.write_text("retained")
    import hashlib

    aid = services.ledger.prepare_action("fs.create_note", "1", {})
    services.ledger.mark_dispatching(aid)
    services.ledger.mark_applied(aid, output_name="output.txt")
    services.ledger.mark_verified(aid, sha256=hashlib.sha256(note.read_bytes()).hexdigest())
    archive = tmp_path / "backup"
    services.backups.create(archive)
    assert (archive / "workspace/output.txt").read_text() == "retained"
    (archive / "workspace/output.txt").write_text("tampered")
    with pytest.raises(BackupError, match="checksum"):
        restore(archive, tmp_path / "rejected")
    assert not (tmp_path / "rejected").exists()


def test_backup_refuses_disk_unavailable_and_existing_restore(services, tmp_path):
    with pytest.raises(BackupError):
        services.backups.create(tmp_path / "unavailable-parent/out")
    archive = tmp_path / "backup"
    services.backups.create(archive)
    with pytest.raises(BackupError):
        restore(archive, services.settings.data_dir)


def test_pressure_stops_new_inference_without_cloud_or_slot_leak():
    resource = ResourceSupervisor(min_available=2048)
    resource._sample["available_bytes"] = 1024
    with pytest.raises(ResourcePressure):
        with resource.inference_slot("stt"):
            pytest.fail("Inference must not start")
    assert not resource.inference.locked()
    resource._sample["available_bytes"] = 4096
    with resource.inference_slot("stt"):
        assert resource.inference.locked()
    assert resource.snapshot()["timings"][0]["warm"] is False
    with resource.inference_slot("stt"):
        pass
    assert resource.snapshot()["timings"][-1]["warm"] is True
    resource.allocation_failed()
    resource.allocation_failed()
    with pytest.raises(ResourcePressure):
        resource.check()


def test_one_inference_slot_shared_between_sync_and_async():
    resource = ResourceSupervisor()

    async def attempt():
        with pytest.raises(ResourcePressure, match="TIMEOUT"):
            async with resource.async_inference_slot("reasoner", timeout=0.05):
                pytest.fail("Second inference admitted")

    with resource.inference_slot("stt"):
        asyncio.run(attempt())
    assert not resource.inference.locked()


def test_diagnostics_review_required_and_frozen_redacted_export():
    diagnostics = Diagnostics(ResourceSupervisor())
    preview = diagnostics.preview()
    assert all(
        value not in preview["contents"]
        for value in [TOKEN, "tone=private", "Authorization: Bearer"]
    )
    exported = diagnostics.export(preview["preview_id"], preview["sha256"])
    assert exported["contents"] == preview["contents"]
    with pytest.raises(ValueError):
        diagnostics.export(preview["preview_id"], preview["sha256"])


def test_health_responsive_during_pressure_and_diagnostics_auth(tmp_path):
    with TestClient(
        create_app(Settings(tmp_path / "api", TOKEN)), base_url="http://127.0.0.1"
    ) as client:
        headers = {"Authorization": "Bearer " + TOKEN}
        assert client.get("/api/memory").status_code == 401
        assert client.get("/api/resources").status_code == 401
        assert client.get("/api/diagnostics/preview").status_code == 401
        services = client.app.state.services
        with services.resources.inference_slot("fixture"):
            start = time.monotonic()
            assert client.get("/api/health", headers=headers).status_code == 200
            assert time.monotonic() - start < 1
        body = preference().model_dump()
        assert client.post("/api/memory", headers=headers, json=body).status_code == 200
        assert len(client.get("/api/memory", headers=headers).json()) == 1
        preview = client.get("/api/diagnostics/preview", headers=headers).json()
        assert (
            client.post(
                "/api/diagnostics/export",
                headers=headers,
                json={"preview_id": preview["preview_id"], "sha256": preview["sha256"]},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/diagnostics/export",
                headers=headers,
                json={
                    "preview_id": preview["preview_id"],
                    "sha256": preview["sha256"],
                    "confirmation": "explicit_user_review",
                },
            ).status_code
            == 200
        )


def test_low_disk_blocks_mutations_but_keeps_health_available(tmp_path, monkeypatch):
    import shutil
    from types import SimpleNamespace

    with TestClient(
        create_app(Settings(tmp_path / "disk-api", TOKEN)), base_url="http://127.0.0.1"
    ) as client:
        headers = {"Authorization": "Bearer " + TOKEN}
        monkeypatch.setattr(shutil, "disk_usage", lambda _: SimpleNamespace(free=0))
        body = {
            "tool": "fs.create_note",
            "arguments": {"filename": "blocked.txt", "text": "fixture"},
        }
        assert client.post("/api/tasks", headers=headers, json=body).status_code == 503
        assert client.get("/api/health", headers=headers).status_code == 200
        assert not client.app.state.services.tasks.database.list_tasks()


def test_busy_forget_returns_conflict_without_losing_memory(tmp_path):
    with TestClient(
        create_app(Settings(tmp_path / "busy-api", TOKEN)), base_url="http://127.0.0.1"
    ) as client:
        headers = {"Authorization": "Bearer " + TOKEN}
        services = client.app.state.services
        entry = services.memory.remember(preference())
        with services.tasks.mutation_lock:
            response = client.delete(f"/api/memory/{entry.memory_id}", headers=headers)
            assert response.status_code == 409
            assert client.get("/api/health", headers=headers).status_code == 200
        assert services.memory.get(entry.memory_id) is not None
        assert client.delete(f"/api/memory/{entry.memory_id}", headers=headers).json()["forgotten"]


def test_restore_invalidates_approval_and_omits_permits_without_changing_source(services, tmp_path):
    from victus.safety.approvals import ApprovalBinding, ApprovalStore, argument_hash
    from victus.safety.permits import PermitStore

    binding = ApprovalBinding(
        task_id="approved-task",
        action_id="approved-action",
        tool_name="fs.create_note",
        tool_version="1",
        canonical_args_hash=argument_hash({"text": "private"}),
        policy_version="p1",
        target_identity="workspace:review.txt",
        observation_identity="obs1",
    )
    approval = services.approvals.request(binding, {"text": "private"})
    services.approvals.decide(approval.approval_id, binding, approved=True)
    PermitStore(services.approvals).issue_permit(
        approval.approval_id, binding
    )
    archive = tmp_path / "authority-backup"
    services.backups.create(archive)
    assert services.approvals.get(approval.approval_id).state == "approved"
    restored = tmp_path / "authority-restored"
    restore(archive, restored)
    recovered = ApprovalStore(restored / "victus.sqlite3")
    assert recovered.get(approval.approval_id).state == "invalidated"
    with closing(sqlite3.connect(restored / "victus.sqlite3")) as db:
        assert db.execute("SELECT COUNT(*) FROM approval_permits").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM approval_previews").fetchone()[0] == 0


def test_restore_refuses_future_schema_and_traversal_before_destination_creation(
    services, tmp_path
):
    archive = tmp_path / "validation-backup"
    services.backups.create(archive)
    manifest_path = archive / "manifest.json"
    original = json.loads(manifest_path.read_text())
    future = {**original, "schema": 99999}
    manifest_path.write_text(json.dumps(future))
    with pytest.raises(BackupError, match="compatible"):
        restore(archive, tmp_path / "future-destination")
    assert not (tmp_path / "future-destination").exists()
    malformed = {**original, "files": [{"path": "../escape.txt", "sha256": "0" * 64, "bytes": 0}]}
    manifest_path.write_text(json.dumps(malformed))
    with pytest.raises(ValueError, match="Unsafe"):
        restore(archive, tmp_path / "traversal-destination")
    assert not (tmp_path / "traversal-destination").exists()
