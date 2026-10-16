"""SQLite LangGraph checkpoints plus a durable node journal and restricted payloads."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from uuid import uuid4

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Interrupt

from victus.models._json import strict_json
from victus.runtime.instance_lock import InstanceLock


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
        return "json", data

    def loads_typed(self, value):
        kind, data = value
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
        self.root = data_dir / "agent"
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.root / "checkpoints.sqlite3"
        if self.path.is_symlink():
            raise ValueError("Checkpoint path cannot be a symlink")
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS agent_threads(task_id TEXT PRIMARY KEY, cancelled INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS node_journal(task_id TEXT NOT NULL, sequence INTEGER NOT NULL,
              node TEXT NOT NULL, result_json TEXT, PRIMARY KEY(task_id, sequence));
            CREATE TABLE IF NOT EXISTS agent_payloads(ref TEXT PRIMARY KEY, task_id TEXT NOT NULL,
              kind TEXT NOT NULL, data_json TEXT NOT NULL, expires REAL NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db
        finally:
            db.close()

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
                (ref, task_id, kind, data, time.time() + ttl_seconds),
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
        return strict_json(row[0])

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
                return "complete" if row[1] is not None else "interrupted", strict_json(
                    row[1]
                ) if row[1] else None
            db.execute("INSERT INTO node_journal VALUES (?,?,?,NULL)", (task_id, sequence, node))
        return "new", None

    def complete(self, task_id, sequence, result):
        data = JSONSerializer().dumps_typed(result)[1].decode("utf-8")
        with self.connect() as db:
            db.execute(
                "UPDATE node_journal SET result_json=? WHERE task_id=? AND sequence=?",
                (data, task_id, sequence),
            )

    @asynccontextmanager
    async def saver(self):
        # One process owns the directory; never concurrently resume the same threads.
        lock = InstanceLock(self.root)
        lock.acquire()
        try:
            async with aiosqlite.connect(str(self.path)) as db:
                await db.execute("PRAGMA synchronous=FULL")
                yield AsyncSqliteSaver(db, serde=JSONSerializer())
        finally:
            lock.release()
