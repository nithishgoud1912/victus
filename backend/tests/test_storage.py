"""Tests for the migration runner, action ledger, and payload store."""

import json
import sqlite3

import pytest

from victus.storage.action_ledger import ActionLedger
from victus.storage.migrations import current_version, migrate
from victus.storage.payloads import PayloadStore


def test_migration_failure_rolls_back_schema_data_and_version(tmp_path, monkeypatch):
    import victus.storage.migrations as migrations

    path = tmp_path / "migration.sqlite3"
    migrate(path)
    before = current_version(path)
    script = tmp_path / "failed.sql"
    script.write_text(
        "CREATE TABLE partial_schema(value TEXT);"
        "INSERT INTO partial_schema VALUES ('partial');"
        "INSERT INTO missing_table VALUES (1);",
        encoding="utf-8",
    )
    original = migrations._discover_migrations()
    monkeypatch.setattr(
        migrations, "_discover_migrations", lambda: original + [(before + 1, script)]
    )
    with pytest.raises(sqlite3.OperationalError):
        migrate(path)
    with sqlite3.connect(path) as db:
        assert (
            db.execute("SELECT name FROM sqlite_master WHERE name='partial_schema'").fetchone()
            is None
        )
    assert current_version(path) == before
    script.write_text("CREATE TABLE partial_schema(value TEXT);", encoding="utf-8")
    assert migrate(path) == [before + 1]
    assert migrate(path) == []


def test_task_state_and_event_roll_back_together(tmp_path):
    from victus.storage.database import Database
    from victus.tools.contracts import TaskResult

    database = Database(tmp_path)
    task = TaskResult(task_id="atomic-state", tool="fs.create_note", status="queued")
    database.save(task)
    with database.connect() as db:
        db.execute("""CREATE TRIGGER reject_terminal_event BEFORE INSERT ON task_events
                    WHEN NEW.event_type='task.cancelled'
                    BEGIN SELECT RAISE(ABORT, 'injected storage failure'); END""")
    task.status = "cancelled"
    with pytest.raises(sqlite3.IntegrityError, match="injected storage failure"):
        database.save(task, event_type="task.cancelled", event_payload={"reason": "test"})
    assert database.get(task.task_id).status == "queued"
    with database.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM task_retention").fetchone()[0] == 0
        db.execute("DROP TRIGGER reject_terminal_event")
    database.save(
        task, event_type="task.cancelled", event_payload={"text": "private", "reason": "test"}
    )
    with database.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM task_retention").fetchone()[0] == 1
        payload = db.execute("SELECT safe_payload FROM task_events").fetchone()[0]
        assert json.loads(payload) == {"reason": "test"}


def test_migration_version_marker_failure_rolls_back_ddl(tmp_path, monkeypatch):
    import victus.storage.migrations as migrations

    path = tmp_path / "marker.sqlite3"
    migrate(path)
    before = current_version(path)
    script = tmp_path / "next.sql"
    script.write_text("CREATE TABLE partial_schema(value TEXT);", encoding="utf-8")
    original = migrations._discover_migrations()
    monkeypatch.setattr(
        migrations, "_discover_migrations", lambda: original + [(before + 1, script)]
    )
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TRIGGER reject_version BEFORE INSERT ON schema_versions
                    BEGIN SELECT RAISE(ABORT, 'version marker failure'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="version marker failure"):
        migrate(path)
    assert current_version(path) == before
    with sqlite3.connect(path) as db:
        assert (
            db.execute("SELECT name FROM sqlite_master WHERE name='partial_schema'").fetchone()
            is None
        )


def test_raw_arguments_stay_in_protected_payload_not_audit(ledger, payloads, db_path):
    private = "private checklist sentinel V22"
    action_id = ledger.prepare_action("fs.create_note", "1.0.0", {"text": private})
    payload_id = payloads.store(action_id, "arguments", {"text": private})
    assert json.loads(payloads.get(payload_id).data_json) == {"text": private}
    with sqlite3.connect(db_path) as db:
        for table in ("action_attempts", "events", "tasks", "task_events", "client_requests"):
            assert private not in repr(db.execute(f"SELECT * FROM {table}").fetchall())
        raw = db.execute(
            "SELECT data_json FROM payloads WHERE payload_id=?", (payload_id,)
        ).fetchone()[0]
        assert raw.startswith("protected:v1:") and private not in raw


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.sqlite3"
    migrate(path)
    return path


@pytest.fixture
def ledger(db_path):
    return ActionLedger(db_path)


@pytest.fixture
def payloads(db_path):
    return PayloadStore(db_path)


# ── migration tests ──────────────────────────────────────────────────────


class TestMigrations:
    def test_applies_all_migrations(self, db_path):
        version = current_version(db_path)
        assert version is not None and version >= 3

    def test_idempotent_reapplication(self, tmp_path):
        path = tmp_path / "idem.sqlite3"
        first = migrate(path)
        second = migrate(path)
        assert len(first) >= 3
        assert second == []
        assert current_version(path) == first[-1]

    def test_creates_expected_tables(self, db_path):
        import sqlite3

        conn = sqlite3.connect(db_path)
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        conn.close()
        assert {"tasks", "action_attempts", "events", "approvals", "payloads"}.issubset(tables)


# ── action ledger tests ──────────────────────────────────────────────────


class TestActionLedger:
    def test_prepare_and_get(self, ledger):
        action_id = ledger.prepare_action("fs.create_note", "1.0.0", {"filename": "a.txt"})
        record = ledger.get(action_id)
        assert record is not None
        assert record.status == "prepared"
        assert record.tool_name == "fs.create_note"
        assert record.tool_version == "1.0.0"
        assert record.canonical_args_hash  # non-empty

    def test_full_lifecycle(self, ledger):
        aid = ledger.prepare_action("fs.create_note", "1.0.0", {"filename": "b.txt"})
        ledger.mark_dispatching(aid)
        assert ledger.get(aid).status == "dispatching"
        assert ledger.get(aid).dispatched_at is not None

        ledger.mark_applied(aid, output_name="b.txt")
        assert ledger.get(aid).status == "applied"
        assert ledger.get(aid).output_name == "b.txt"

        ledger.mark_verified(aid, sha256="abc123")
        record = ledger.get(aid)
        assert record.status == "verified"
        assert record.sha256 == "abc123"
        assert record.finished_at is not None

    def test_invalid_transition_raises(self, ledger):
        aid = ledger.prepare_action("fs.create_note", "1.0.0", {"filename": "c.txt"})
        with pytest.raises(ValueError, match="Invalid transition"):
            ledger.mark_verified(aid)  # prepared → verified is not valid

    def test_mark_unknown_after_dispatch(self, ledger):
        aid = ledger.prepare_action("fs.create_note", "1.0.0", {"filename": "d.txt"})
        ledger.mark_dispatching(aid)
        ledger.mark_unknown(aid, error_code="POSTCONDITION_FAILED")
        record = ledger.get(aid)
        assert record.status == "unknown"
        assert record.error_code == "POSTCONDITION_FAILED"

    def test_mark_failed_before_dispatch(self, ledger):
        aid = ledger.prepare_action("fs.create_note", "1.0.0", {"filename": "e.txt"})
        ledger.mark_failed(aid, error_code="POLICY_DENIED")
        record = ledger.get(aid)
        assert record.status == "failed"
        assert record.error_code == "POLICY_DENIED"
        assert record.finished_at is not None

    def test_mark_cancelled(self, ledger):
        aid = ledger.prepare_action("fs.create_note", "1.0.0", {"filename": "f.txt"})
        ledger.mark_cancelled(aid)
        assert ledger.get(aid).status == "cancelled"

    def test_list_unfinished(self, ledger):
        a1 = ledger.prepare_action("fs.create_note", "1.0.0", {"filename": "g.txt"})
        a2 = ledger.prepare_action("fs.create_note", "1.0.0", {"filename": "h.txt"})
        ledger.mark_dispatching(a2)
        a3 = ledger.prepare_action("fs.create_note", "1.0.0", {"filename": "i.txt"})
        ledger.mark_cancelled(a3)

        unfinished = ledger.list_unfinished()
        ids = {r.action_id for r in unfinished}
        assert a1 in ids
        assert a2 in ids
        assert a3 not in ids  # cancelled is terminal

    def test_get_nonexistent_returns_none(self, ledger):
        assert ledger.get("nonexistent") is None

    def test_canonical_hash_deterministic(self, ledger):
        a1 = ledger.prepare_action("t", "1", {"b": 2, "a": 1})
        a2 = ledger.prepare_action("t", "1", {"a": 1, "b": 2})
        assert ledger.get(a1).canonical_args_hash == ledger.get(a2).canonical_args_hash


# ── payload store tests ──────────────────────────────────────────────────


class TestPayloadStore:
    def test_store_and_retrieve(self, ledger, payloads):
        aid = ledger.prepare_action("fs.create_note", "1.0.0", {"filename": "p.txt"})
        pid = payloads.store(aid, "arguments", {"filename": "p.txt", "text": "hello"})
        record = payloads.get(pid)
        assert record is not None
        assert record.action_id == aid
        assert record.kind == "arguments"
        data = json.loads(record.data_json)
        assert data["text"] == "hello"

    def test_typed_text_shorter_retention(self, ledger, payloads):
        aid = ledger.prepare_action("fs.create_note", "1.0.0", {"filename": "q.txt"})
        pid_args = payloads.store(aid, "arguments", {"x": 1})
        pid_text = payloads.store(aid, "typed_text", "raw user input")
        args_rec = payloads.get(pid_args)
        text_rec = payloads.get(pid_text)
        # typed_text should expire before arguments
        assert args_rec.expires_at > text_rec.expires_at

    def test_purge_by_action(self, ledger, payloads):
        aid = ledger.prepare_action("fs.create_note", "1.0.0", {"filename": "r.txt"})
        pid = payloads.store(aid, "arguments", {"x": 1})
        count = payloads.purge_by_action(aid)
        assert count == 1
        # Purged payloads are not returned by get()
        assert payloads.get(pid) is None

    def test_get_by_action_filters_kind(self, ledger, payloads):
        aid = ledger.prepare_action("fs.create_note", "1.0.0", {"filename": "s.txt"})
        payloads.store(aid, "arguments", {"x": 1})
        payloads.store(aid, "typed_text", "hello")
        args_only = payloads.get_by_action(aid, "arguments")
        assert len(args_only) == 1
        assert args_only[0].kind == "arguments"
        all_payloads = payloads.get_by_action(aid)
        assert len(all_payloads) == 2
