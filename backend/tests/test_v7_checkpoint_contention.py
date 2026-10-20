"""A checkpoint must commit while a synchronous journal writer occupies the loop."""

import asyncio
import sqlite3
import threading

import pytest
from langgraph.checkpoint.base import empty_checkpoint

from victus.storage.checkpoints import CheckpointStore


def test_checkpoint_commit_does_not_need_event_loop_to_release_journal_lock(tmp_path, monkeypatch):
    store = CheckpointStore(tmp_path)
    held, release = threading.Event(), threading.Event()
    connect = sqlite3.connect

    class Cursor(sqlite3.Cursor):
        def execute(self, sql, parameters=()):
            result = super().execute(sql, parameters)
            if sql.startswith("INSERT OR REPLACE INTO checkpoints"):
                held.set()
                if not release.wait(2):
                    raise RuntimeError("Test barrier was not released")
            return result

    class Connection(sqlite3.Connection):
        def cursor(self, factory=Cursor):
            return super().cursor(factory)

        def execute(self, sql, parameters=()):
            return self.cursor().execute(sql, parameters)

    monkeypatch.setattr(sqlite3, "connect", lambda *a, **kw: connect(*a, **kw, factory=Connection))

    async def run():
        async with store.saver() as saver:
            writing = asyncio.create_task(
                saver.aput(
                    {"configurable": {"thread_id": "task", "checkpoint_ns": ""}},
                    empty_checkpoint(),
                    {"source": "input", "step": 0},
                    {},
                )
            )
            try:
                assert await asyncio.to_thread(held.wait, 2)
                release.set()
                # This synchronous BEGIN IMMEDIATE must be able to wait for a
                # commit that is independent of event-loop scheduling.
                assert store.claim("task", 0, "finalize") == ("new", None)
                await writing
                assert await saver.aget_tuple({"configurable": {"thread_id": "task"}})
            finally:
                release.set()
                await asyncio.gather(writing, return_exceptions=True)

    asyncio.run(run())


def test_cancelled_checkpoint_write_is_reaped_before_owner_release(tmp_path, monkeypatch):
    from langgraph.checkpoint.sqlite import SqliteSaver

    store = CheckpointStore(tmp_path)
    held, release = threading.Event(), threading.Event()
    original = SqliteSaver.put

    def paused(self, *args):
        held.set()
        if not release.wait(2):
            raise RuntimeError("Test barrier was not released")
        return original(self, *args)

    monkeypatch.setattr(SqliteSaver, "put", paused)

    async def run():
        async with store.saver() as saver:
            writing = asyncio.create_task(
                saver.aput(
                    {"configurable": {"thread_id": "task", "checkpoint_ns": ""}},
                    empty_checkpoint(),
                    {"source": "input", "step": 0},
                    {},
                )
            )
            try:
                assert await asyncio.to_thread(held.wait, 1)
                writing.cancel()
                await asyncio.sleep(0)
                assert not writing.done()
                release.set()
                with pytest.raises(asyncio.CancelledError):
                    await writing
                assert await saver.aget_tuple({"configurable": {"thread_id": "task"}})
            finally:
                release.set()
                await asyncio.gather(writing, return_exceptions=True)

    asyncio.run(run())


def test_checkpoint_batch_failure_rolls_back_all_pending_writes(tmp_path):
    store = CheckpointStore(tmp_path)

    async def run():
        async with store.saver() as saver:
            await saver.setup()
            with store.connect() as db:
                db.execute("""CREATE TRIGGER reject_second BEFORE INSERT ON writes
                    WHEN NEW.idx = 1 BEGIN SELECT RAISE(ABORT, 'test batch failure'); END""")
            config = {
                "configurable": {
                    "thread_id": "task",
                    "checkpoint_ns": "",
                    "checkpoint_id": "checkpoint",
                }
            }
            with pytest.raises(sqlite3.IntegrityError):
                await saver.aput_writes(
                    config, [("first", "private one"), ("second", "private two")], "node"
                )
            with store.connect() as db:
                assert db.execute("SELECT COUNT(*) FROM writes").fetchone()[0] == 0
                db.execute("DROP TRIGGER reject_second")
            await saver.aput_writes(
                config, [("first", "private one"), ("second", "private two")], "node"
            )
            with store.connect() as db:
                rows = db.execute("SELECT value FROM writes").fetchall()
                assert len(rows) == 2
                assert all(row[0].startswith(b"protected:") for row in rows)
                assert db.execute("PRAGMA synchronous").fetchone()[0] == 2
            await saver.adelete_thread("task")
            with store.connect() as db:
                assert db.execute("SELECT COUNT(*) FROM writes").fetchone()[0] == 0

    asyncio.run(run())
