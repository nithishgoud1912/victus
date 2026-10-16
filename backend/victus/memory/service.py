"""SQLite-reviewed memory with restart-safe cascaded forgetting."""

import json
import sqlite3
import time
from contextlib import closing
from uuid import uuid4

from victus.memory.models import MemoryEntry, MemoryInput
from victus.storage import secure_json


class MemoryService:
    def __init__(self, root, guard, *, clock=time.time):
        self.root, self.path, self.guard, self.clock = root, root / "victus.sqlite3", guard, clock

    def remember(self, entry: MemoryInput):
        now = self.clock()
        if entry.expires_at is not None and entry.expires_at <= now:
            raise ValueError("Memory expiry must be in the future")
        memory_id = uuid4().hex
        with closing(sqlite3.connect(self.path, timeout=2)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT COUNT(*) FROM memory_entries").fetchone()[0] >= 1000:
                raise ValueError("Memory capacity reached; forget an entry first")
            db.execute(
                "INSERT INTO memory_entries VALUES (?,?,?,?,?,?,?,?)",
                (
                    memory_id,
                    entry.type,
                    secure_json.encode_text(entry.value),
                    entry.provenance,
                    now,
                    now,
                    now,
                    entry.expires_at,
                ),
            )
            db.executemany(
                "INSERT INTO memory_refs VALUES (?,?)",
                [(memory_id, t) for t in set(entry.task_ids)],
            )
        return self.get(memory_id)

    def get(self, memory_id):
        return next(iter(self.recall(memory_id=memory_id)), None)

    def recall(self, *, memory_id=None, type=None, limit=100):
        if not 1 <= limit <= 100:
            raise ValueError("Invalid recall limit")
        sql = "SELECT * FROM memory_entries WHERE (expires_at IS NULL OR expires_at>?)"
        params = [self.clock()]
        for key, value in (("memory_id", memory_id), ("type", type)):
            if value is not None:
                sql += f" AND {key}=?"
                params.append(value)
        sql += " ORDER BY last_confirmed_at DESC, memory_id LIMIT ?"
        params.append(limit)
        with closing(sqlite3.connect(self.path, timeout=2)) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(sql, params).fetchall()
        return [
            MemoryEntry(
                **{
                    k: row[k]
                    for k in (
                        "memory_id",
                        "type",
                        "provenance",
                        "created_at",
                        "updated_at",
                        "last_confirmed_at",
                        "expires_at",
                    )
                },
                value=secure_json.decode_text(row["protected_value"]),
            )
            for row in rows
        ]

    def edit(self, memory_id, entry: MemoryInput):
        # Replacing an entry first removes copies linked to the old value.
        if self.get(memory_id) is None:
            raise KeyError("Memory entry not found")
        if entry.expires_at is not None and entry.expires_at <= self.clock():
            raise ValueError("Memory expiry must be in the future")
        with self.guard():
            self._forget(memory_id)
            return self.remember(entry)

    def export(self):
        # Explicit export returns the reviewed values; callers display before saving.
        with closing(sqlite3.connect(self.path, timeout=2)) as db:
            ids = [
                r[0] for r in db.execute("SELECT memory_id FROM memory_entries ORDER BY memory_id")
            ]
        return {
            "context_only": True,
            "authority": "current_instructions_and_policy_override_memory",
            "entries": [entry.model_dump() for key in ids if (entry := self.get(key)) is not None],
        }

    def link_task(self, memory_id, task_id):
        with closing(sqlite3.connect(self.path, timeout=2)) as db, db:
            if not db.execute(
                "SELECT 1 FROM memory_entries WHERE memory_id=? AND (expires_at IS NULL OR expires_at>?)",
                (memory_id, self.clock()),
            ).fetchone():
                raise KeyError("Memory unavailable")
            db.execute("INSERT OR IGNORE INTO memory_refs VALUES (?,?)", (memory_id, task_id))

    def forget(self, memory_id):
        with self.guard():
            return self._forget(memory_id)

    def _forget(self, memory_id):
        with closing(sqlite3.connect(self.path, timeout=2)) as db, db:
            tasks = [
                r[0]
                for r in db.execute(
                    "SELECT task_id FROM memory_refs WHERE memory_id=?", (memory_id,)
                )
            ]
            # A durable job hides the value immediately, then retries cross-DB cleanup after crashes.
            db.execute(
                "INSERT OR IGNORE INTO memory_forget_jobs VALUES (?,?,?)",
                (memory_id, json.dumps(tasks), self.clock()),
            )
            count = db.execute(
                "DELETE FROM memory_entries WHERE memory_id=?", (memory_id,)
            ).rowcount
        self._finish_job(memory_id)
        return bool(count)

    def _finish_job(self, memory_id):
        with closing(sqlite3.connect(self.path, timeout=2)) as db:
            row = db.execute(
                "SELECT task_ids_json FROM memory_forget_jobs WHERE memory_id=?", (memory_id,)
            ).fetchone()
        if not row:
            return
        from victus.memory.retention import purge_task_context

        for task_id in json.loads(row[0]):
            purge_task_context(self.root, task_id)
            if (self.root / "agent" / "checkpoints.sqlite3").is_file():
                from victus.storage.checkpoints import CheckpointStore

                CheckpointStore(self.root).forget_task(task_id)
        with closing(sqlite3.connect(self.path, timeout=2)) as db, db:
            db.execute("DELETE FROM memory_refs WHERE memory_id=?", (memory_id,))
            db.execute("DELETE FROM memory_forget_jobs WHERE memory_id=?", (memory_id,))

    def finish_pending(self):
        with self.guard():
            with closing(sqlite3.connect(self.path, timeout=2)) as db:
                ids = [r[0] for r in db.execute("SELECT memory_id FROM memory_forget_jobs")]
            for memory_id in ids:
                self._finish_job(memory_id)

    def planning_preferences(self, task_id):
        # Only the existing reviewed, bounded ContextBuilder keys are eligible.
        result = []
        for entry in self.recall(type="preference", limit=8):
            key, separator, value = entry.value.partition("=")
            if separator and key in {"language", "tone", "date_format", "preferred_editor"}:
                self.link_task(entry.memory_id, task_id)
                result.append(
                    {
                        "key": key,
                        "value": value[:160],
                        "approved": True,
                        "provenance": "user_review",
                        "expires_epoch": entry.expires_at,
                    }
                )
        return result
