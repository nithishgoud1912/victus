"""SQLite LangGraph checkpoints plus a durable node journal and restricted payloads."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import asynccontextmanager, closing, contextmanager
from pathlib import Path
from uuid import uuid4

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Interrupt

from victus.models._json import strict_json
from victus.runtime.instance_lock import InstanceLock
from victus.safety.previews import protect, unprotect
from victus.storage import secure_json
from victus.storage.paths import safe_path


class JSONSerializer:
    """No pickle, msgpack object construction or arbitrary class imports on resume."""

    def dumps_typed(self, value):
        def encode(item):
            if type(item) is Interrupt:
                return {
                    "__victus_interrupt_v1__": {
                        "value": item.value,
                        "id": item.id,
                        "response_schema": item.response_schema,
                    }
                }
            raise TypeError("Unsupported checkpoint object")

        data = json.dumps(value, default=encode, allow_nan=False, separators=(",", ":")).encode(
            "utf-8"
        )
        if len(data) > 512000:
            raise ValueError("Checkpoint size limit")
        return "json", b"protected:" + protect(data)

    def loads_typed(self, value):
        kind, data = value
        if data.startswith(b"protected:"):
            data = unprotect(data[10:])
        if kind != "json" or len(data) > 512000:
            raise ValueError("Unsupported checkpoint encoding")

        def restore(item):
            if isinstance(item, list):
                return [restore(value) for value in item]
            if isinstance(item, dict):
                if set(item) == {"__victus_interrupt_v1__"}:
                    value = item["__victus_interrupt_v1__"]
                    if (
                        not isinstance(value, dict)
                        or set(value) != {"value", "id", "response_schema"}
                        or not isinstance(value["id"], str)
                        or value["response_schema"] is not None
                    ):
                        raise ValueError("Invalid interrupt checkpoint")
                    return Interrupt(value=value["value"], id=value["id"])
                return {key: restore(value) for key, value in item.items()}
            return item

        return restore(strict_json(data.decode("utf-8")))


class CheckpointStore:
    def __init__(self, data_dir: Path):
        safe_path(data_dir, "agent/checkpoints.sqlite3")
        self.root = data_dir / "agent"
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.root / "checkpoints.sqlite3"
        if self.path.is_symlink():
            raise ValueError("Checkpoint path cannot be a symlink")
        if self.path.exists():
            with closing(sqlite3.connect(self.path)) as existing:
                if existing.execute("PRAGMA user_version").fetchone()[0] > 1:
                    raise ValueError("Unsupported checkpoint schema")
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS agent_retention(task_id TEXT PRIMARY KEY, terminal_at REAL NOT NULL, pinned INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS agent_threads(task_id TEXT PRIMARY KEY, cancelled INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS node_journal(task_id TEXT NOT NULL, sequence INTEGER NOT NULL,
              node TEXT NOT NULL, result_json TEXT, PRIMARY KEY(task_id, sequence));
            CREATE TABLE IF NOT EXISTS agent_payloads(ref TEXT PRIMARY KEY, task_id TEXT NOT NULL,
              kind TEXT NOT NULL, data_json TEXT NOT NULL, expires REAL NOT NULL);
            """)
            db.execute("PRAGMA user_version=1")
            for ref, data in db.execute("SELECT ref,data_json FROM agent_payloads").fetchall():
                if not data.startswith(secure_json.PREFIX):
                    db.execute(
                        "UPDATE agent_payloads SET data_json=? WHERE ref=?",
                        (secure_json.encode_text(data), ref),
                    )
            for task, seq, data in db.execute(
                "SELECT task_id,sequence,result_json FROM node_journal WHERE result_json IS NOT NULL"
            ).fetchall():
                if not data.startswith(secure_json.PREFIX):
                    db.execute(
                        "UPDATE node_journal SET result_json=? WHERE task_id=? AND sequence=?",
                        (secure_json.encode_text(data), task, seq),
                    )

        self.protect_legacy_checkpoints()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db
        finally:
            db.close()

    def protect_legacy_checkpoints(self):
        with self.connect() as db:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table, column in (("checkpoints", "checkpoint"), ("writes", "value")):
                if table not in tables:
                    continue
                columns = {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
                if not {"type", column}.issubset(columns):
                    continue
                for rowid, kind, raw in db.execute(
                    f"SELECT rowid,type,{column} FROM {table}"
                ).fetchall():
                    if kind == "json" and raw is not None and not raw.startswith(b"protected:"):
                        if len(raw) > 512000:
                            raise ValueError("Legacy checkpoint size limit")
                        db.execute(
                            f"UPDATE {table} SET {column}=? WHERE rowid=?",
                            (b"protected:" + protect(raw), rowid),
                        )
                if table == "checkpoints" and "metadata" in columns:
                    for rowid, raw in db.execute(
                        "SELECT rowid,metadata FROM checkpoints WHERE metadata IS NOT NULL"
                    ).fetchall():
                        value = strict_json(raw)
                        clean = {
                            key: value[key] for key in ("source", "step", "parents") if key in value
                        }
                        db.execute(
                            "UPDATE checkpoints SET metadata=? WHERE rowid=?",
                            (json.dumps(clean), rowid),
                        )

    def register(self, task_id):
        with self.connect() as db:
            db.execute("INSERT INTO agent_threads(task_id) VALUES (?)", (task_id,))

    def cancel(self, task_id):
        with self.connect() as db:
            if (
                db.execute(
                    "UPDATE agent_threads SET cancelled=1 WHERE task_id=?", (task_id,)
                ).rowcount
                != 1
            ):
                raise KeyError("Unknown agent task")

    def cancelled(self, task_id):
        with self.connect() as db:
            row = db.execute(
                "SELECT cancelled FROM agent_threads WHERE task_id=?", (task_id,)
            ).fetchone()
        return row is None or bool(row[0])

    def put_payload(self, task_id, kind, value, *, ttl_seconds=86400):
        if kind not in {"goal", "observation", "proposal", "approval", "evidence", "route"}:
            raise ValueError("Unknown agent payload kind")
        if not 0 < ttl_seconds <= 86400:
            raise ValueError("Invalid payload retention")
        data = json.dumps(value, allow_nan=False)
        if len(data.encode("utf-8")) > 128000:
            raise ValueError("Payload size limit")
        ref = uuid4().hex
        with self.connect() as db:
            db.execute(
                "INSERT INTO agent_payloads VALUES (?,?,?,?,?)",
                (ref, task_id, kind, secure_json.encode_text(data), time.time() + ttl_seconds),
            )
        return ref

    def payload(self, task_id, kind, ref):
        with self.connect() as db:
            row = db.execute(
                "SELECT data_json FROM agent_payloads WHERE ref=? AND task_id=? AND kind=? AND expires>?",
                (ref, task_id, kind, time.time()),
            ).fetchone()
        if row is None:
            raise ValueError("Agent payload unavailable")
        return secure_json.decode(row[0])

    def purge_expired(self):
        with self.connect() as db:
            return db.execute(
                "DELETE FROM agent_payloads WHERE expires<=?", (time.time(),)
            ).rowcount

    def claim(self, task_id, sequence, node):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT node,result_json FROM node_journal WHERE task_id=? AND sequence=?",
                (task_id, sequence),
            ).fetchone()
            if row is not None:
                if row[0] != node:
                    raise ValueError("Node journal identity mismatch")
                return "complete" if row[1] is not None else "interrupted", secure_json.decode(
                    row[1]
                ) if row[1] else None
            db.execute("INSERT INTO node_journal VALUES (?,?,?,NULL)", (task_id, sequence, node))
        return "new", None

    def complete(self, task_id, sequence, result):
        data = secure_json.encode(result)
        with self.connect() as db:
            db.execute(
                "UPDATE node_journal SET result_json=? WHERE task_id=? AND sequence=?",
                (data, task_id, sequence),
            )

    def mark_terminal(self, task_id):
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO agent_retention(task_id,terminal_at) VALUES (?,?)",
                (task_id, time.time()),
            )

    def forget_task(self, task_id):
        with self.connect() as db:
            db.execute("PRAGMA secure_delete=ON")
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table, column in (
                ("agent_payloads", "task_id"),
                ("node_journal", "task_id"),
                ("agent_threads", "task_id"),
                ("agent_retention", "task_id"),
                ("checkpoints", "thread_id"),
                ("writes", "thread_id"),
            ):
                if table in tables:
                    db.execute(f"DELETE FROM {table} WHERE {column}=?", (task_id,))

    @asynccontextmanager
    async def saver(self):
        # One process owns the directory; never concurrently resume the same threads.
        lock = InstanceLock(self.root)
        lock.acquire()
        try:
            async with aiosqlite.connect(str(self.path)) as db:
                await db.execute("PRAGMA synchronous=FULL")
                yield PrivateSqliteSaver(db, serde=JSONSerializer())
        finally:
            lock.release()


class PrivateSqliteSaver(AsyncSqliteSaver):
    async def aput(self, config, checkpoint, metadata, new_versions):
        clean = {key: metadata[key] for key in ("source", "step", "parents") if key in metadata}
        return await super().aput(config, checkpoint, clean, new_versions)
