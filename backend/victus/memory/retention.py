"""Product retention defaults. Logical deletion does not promise forensic erasure."""

import hashlib
import json
import sqlite3
import threading
import time
from contextlib import closing
from datetime import datetime, timezone
from uuid import uuid4

from victus.storage.paths import safe_path
from victus.storage.payloads import PayloadStore

DAY = 86400
EVIDENCE_QUOTA = 250 * 1024 * 1024


def purge_task_context(root, task_id):
    path = root / "victus.sqlite3"
    with closing(sqlite3.connect(path, timeout=2)) as db, db:
        db.execute("PRAGMA secure_delete=ON")
        actions = [
            r[0]
            for r in db.execute(
                "SELECT action_id FROM action_attempts WHERE expected_effect_ref=?",
                ("task:" + task_id,),
            )
        ]
        row = db.execute("SELECT result_json FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if row and (action := json.loads(row[0]).get("action_id")):
            actions = list(set([*actions, action]))
        for action in actions:
            db.execute(
                "UPDATE payloads SET data_json='{}',byte_length=0,purged=1 WHERE action_id=?",
                (action,),
            )
            db.execute("DELETE FROM approval_previews WHERE action_id=?", (action,))
            db.execute(
                "UPDATE recovery_reconciliations SET evidence_ref=NULL WHERE action_id=?", (action,)
            )
        db.execute(
            "DELETE FROM approval_permits WHERE approval_id IN (SELECT approval_id FROM approvals WHERE task_id=?)",
            (task_id,),
        )
        db.execute(
            "UPDATE approvals SET state='invalidated' WHERE task_id=? AND state IN ('pending','approved')",
            (task_id,),
        )
        evidence = db.execute(
            "SELECT evidence_id,relative_path FROM evidence_index WHERE task_id=?", (task_id,)
        ).fetchall()
        for evidence_id, relative in evidence:
            safe_path(root, relative, prefix="evidence").unlink(missing_ok=True)
            db.execute("DELETE FROM evidence_index WHERE evidence_id=?", (evidence_id,))


class RetentionService:
    def __init__(self, root, guard, memory, *, clock=time.time, evidence_quota=EVIDENCE_QUOTA):
        self.root, self.path, self.guard, self.memory = root, root / "victus.sqlite3", guard, memory
        self.clock, self.evidence_quota = clock, evidence_quota
        self._closing = threading.Event()
        self._thread = None
        self.last_error = None

    def start(self):
        self._thread = threading.Thread(target=self._loop, name="victus-retention", daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._closing.wait(60):
            try:
                self.cleanup()
                self.last_error = None
            except Exception:
                self.last_error = "RETENTION_DEFERRED_OR_STORAGE_UNAVAILABLE"

    def close(self):
        self._closing.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                raise RuntimeError("Retention worker shutdown incomplete")

    def register_evidence(self, task_id, relative_path, *, pinned=False):
        path = safe_path(self.root, relative_path, prefix="evidence")
        if not path.is_file():
            raise ValueError("Evidence file is missing")
        size = path.stat().st_size
        if size > self.evidence_quota:
            raise ValueError("Evidence quota exceeded")
        now = self.clock()
        with closing(sqlite3.connect(self.path, timeout=2)) as db, db:
            used = db.execute("SELECT COALESCE(SUM(byte_length),0) FROM evidence_index").fetchone()[
                0
            ]
            if used + size > self.evidence_quota:
                raise ValueError("Evidence quota exceeded; run retention cleanup")
            key = uuid4().hex
            db.execute(
                "INSERT INTO evidence_index VALUES (?,?,?,?,?,?,?,?)",
                (
                    key,
                    task_id,
                    relative_path,
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    size,
                    int(pinned),
                    now,
                    now + (7 * DAY if pinned else DAY),
                ),
            )
        return key

    def pin_task(self, task_id, value=True):
        with closing(sqlite3.connect(self.path, timeout=2)) as db, db:
            db.execute("UPDATE task_retention SET pinned=? WHERE task_id=?", (int(value), task_id))
        checkpoint = self.root / "agent/checkpoints.sqlite3"
        if checkpoint.is_file():
            with closing(sqlite3.connect(checkpoint, timeout=2)) as db, db:
                db.execute(
                    "UPDATE agent_retention SET pinned=? WHERE task_id=?", (int(value), task_id)
                )

    def cleanup(self, *, end_session=False):
        with self.guard():
            return self._cleanup(end_session=end_session)

    def _cleanup(self, *, end_session=False):
        now = self.clock()
        cutoff = datetime.fromtimestamp(now - 30 * DAY, timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        counts = {
            "expired_memories": 0,
            "payloads": PayloadStore(self.path).purge_expired(),
            "checkpoints": 0,
            "tasks": 0,
            "evidence": 0,
        }
        with closing(sqlite3.connect(self.path, timeout=2)) as db:
            expired = [
                r[0]
                for r in db.execute(
                    "SELECT memory_id FROM memory_entries WHERE expires_at<=?", (now,)
                )
            ]
        for key in expired:
            self.memory._forget(key)
            counts["expired_memories"] += 1
        checkpoint = self.root / "agent/checkpoints.sqlite3"
        if checkpoint.is_file():
            from victus.storage.checkpoints import CheckpointStore

            store = CheckpointStore(self.root)
            store.purge_expired()
            with store.connect() as db:
                expired_threads = [
                    r[0]
                    for r in db.execute(
                        "SELECT task_id FROM agent_retention WHERE terminal_at<=? AND pinned=0",
                        (now - 7 * DAY,),
                    )
                ]
                if end_session:
                    db.execute(
                        "DELETE FROM agent_payloads WHERE kind IN ('evidence','observation')"
                    )
            for task_id in expired_threads:
                store.forget_task(task_id)
                counts["checkpoints"] += 1
        with closing(sqlite3.connect(self.path, timeout=2)) as db, db:
            db.execute("PRAGMA secure_delete=ON")
            for task_id, raw in db.execute("SELECT task_id,result_json FROM tasks").fetchall():
                if json.loads(raw)["status"] not in {"queued", "prepared", "running"}:
                    db.execute(
                        "INSERT OR IGNORE INTO task_retention(task_id,terminal_at) VALUES (?,?)",
                        (task_id, now),
                    )
            for key, relative, _size, pinned, expiry in db.execute(
                "SELECT evidence_id,relative_path,byte_length,pinned,expires_at FROM evidence_index ORDER BY created_at"
            ).fetchall():
                if expiry <= now or (end_session and not pinned):
                    safe_path(self.root, relative, prefix="evidence").unlink(missing_ok=True)
                    db.execute("DELETE FROM evidence_index WHERE evidence_id=?", (key,))
                    counts["evidence"] += 1
            old_tasks = [
                r[0]
                for r in db.execute(
                    "SELECT task_id FROM task_retention WHERE terminal_at<=? AND pinned=0",
                    (now - 30 * DAY,),
                )
            ]
        for task_id in old_tasks:
            purge_task_context(self.root, task_id)
            if checkpoint.is_file():
                CheckpointStore(self.root).forget_task(task_id)
            with closing(sqlite3.connect(self.path, timeout=2)) as db, db:
                actions = [
                    r[0]
                    for r in db.execute(
                        "SELECT action_id FROM action_attempts WHERE expected_effect_ref=?",
                        ("task:" + task_id,),
                    )
                ]
                for action in actions:
                    for table in (
                        "payloads",
                        "events",
                        "recovery_reconciliations",
                        "recovery_retries",
                        "approvals_legacy",
                    ):
                        db.execute(f"DELETE FROM {table} WHERE action_id=?", (action,))
                    db.execute("DELETE FROM action_attempts WHERE action_id=?", (action,))
                db.execute("DELETE FROM approvals WHERE task_id=?", (task_id,))
                for table in ("task_events", "client_requests", "tasks", "task_retention"):
                    db.execute(f"DELETE FROM {table} WHERE task_id=?", (task_id,))
            counts["tasks"] += 1
        with closing(sqlite3.connect(self.path, timeout=2)) as db, db:
            db.execute("DELETE FROM events WHERE created_at<?", (cutoff,))
            db.execute("DELETE FROM task_events WHERE created_at<?", (cutoff,))
            # Size-based rotation is metadata-only; task snapshots remain authoritative.
            for table in ("events", "task_events"):
                db.execute(
                    f"DELETE FROM {table} WHERE event_id NOT IN (SELECT event_id FROM {table} ORDER BY event_id DESC LIMIT 50000)"
                )
            db.execute("DELETE FROM approval_previews WHERE expires_at<=?", (now,))
        return counts
