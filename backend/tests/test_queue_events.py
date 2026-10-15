"""Tests for task queue (capacity limits, deduplication, worker) and sequenced events (persistence, SSE, reconnect)."""

import asyncio
import json
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from victus.api.app import create_app
from victus.api.routes.events import task_event_stream
from victus.bootstrap import build_services
from victus.settings import Settings
from victus.tasks.events import sanitize_payload
from victus.tasks.queue import QueueFullError
from victus.tools.contracts import ActionRequest

TOKEN = "test-only-" + "x" * 40
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "runtime", api_token=TOKEN)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as test_client:
        yield test_client


@pytest.fixture
def network_client(settings):
    """A real loopback server avoids buffering an infinite ASGI response in TestClient."""
    app = create_app(settings)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=3) as connection:
            yield connection, app
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()
        assert not thread.is_alive()


def request_body(filename="queue_test.txt", text="Queue and Events"):
    return {"tool": "fs.create_note", "arguments": {"filename": filename, "text": text}}


def wait_for_task(client, task_id: str, timeout: float = 8.0) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        res = client.get(f"/api/tasks/{task_id}", headers=HEADERS).json()
        if res["status"] in {"succeeded", "failed", "cancelled", "unknown"}:
            return res
        time.sleep(0.02)
    raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")


# ── Task Queue Tests ──────────────────────────────────────────────────────


class TestTaskQueue:
    def test_queue_capacity_limit(self, settings):
        """Queue accepts at most 3 pending tasks; 4th pending raises QueueFullError / 429."""
        services = build_services(settings)
        try:
            # Register a blocking tool to keep the 1 active worker busy
            services.tasks.mutation_lock.acquire()

            queue = services.tasks.queue
            action = ActionRequest.model_validate(request_body("block.txt"))

            # 1 active task starts running
            t1, _ = queue.submit(action)
            # Give worker a moment to pick up t1 so it becomes active
            deadline = time.monotonic() + 2
            while queue.active_task_id != t1 and time.monotonic() < deadline:
                time.sleep(0.01)
            assert queue.active_task_id == t1

            # Submit 3 queued tasks (max capacity = 3)
            q1, _ = queue.submit(ActionRequest.model_validate(request_body("q1.txt")))
            q2, _ = queue.submit(ActionRequest.model_validate(request_body("q2.txt")))
            q3, _ = queue.submit(ActionRequest.model_validate(request_body("q3.txt")))
            assert queue.queued_count == 3

            # 4th queued task must fail with QueueFullError
            with pytest.raises(QueueFullError):
                queue.submit(ActionRequest.model_validate(request_body("q4.txt")))

            # Unblock worker and let everything finish
        finally:
            services.tasks.mutation_lock.release()
            services.close()

    def test_post_tasks_returns_429_when_queue_full(self, client):
        """HTTP POST /api/tasks returns HTTP 429 when queue is at capacity."""
        # Submit 1 active + 3 queued tasks through the API
        tasks = client.app.state.services.tasks
        tasks.mutation_lock.acquire()
        responses = []
        try:
            first = client.post("/api/tasks", headers=HEADERS, json=request_body("active.txt"))
            assert first.status_code == 202
            responses.append(first.json()["task_id"])
            deadline = time.monotonic() + 2
            while tasks.queue.active_task_id is None and time.monotonic() < deadline:
                time.sleep(0.01)
            for i in range(3):
                r = client.post("/api/tasks", headers=HEADERS, json=request_body(f"fill_{i}.txt"))
                assert r.status_code == 202
                responses.append(r.json()["task_id"])
            assert (
                client.post(
                    "/api/tasks", headers=HEADERS, json=request_body("overflow.txt")
                ).status_code
                == 429
            )
        finally:
            tasks.mutation_lock.release()
        for tid in responses:
            wait_for_task(client, tid)

    def test_concurrent_client_request_ids_have_one_winner(self, client):
        barrier = threading.Barrier(8)

        def submit(_):
            barrier.wait(timeout=3)
            r = client.post(
                "/api/tasks",
                headers={**HEADERS, "X-Client-Request-ID": "concurrent"},
                json=request_body("concurrent.txt"),
            )
            assert r.status_code == 202
            return r.json()["task_id"]

        with ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(submit, range(8)))
        assert len(set(ids)) == 1
        assert wait_for_task(client, ids[0])["status"] == "succeeded"
        events = client.app.state.services.events.get_events(task_id=ids[0])
        assert [e.event_type for e in events] == ["task.queued", "task.started", "task.succeeded"]

    def test_client_request_id_deduplication(self, client):
        """Submitting duplicate client request ID returns the existing task ID."""
        client_req_id = "unique-client-req-999"

        # First submission
        r1 = client.post(
            "/api/tasks",
            headers={**HEADERS, "X-Client-Request-ID": client_req_id},
            json=request_body("dedup.txt", "Initial submission"),
        )
        assert r1.status_code == 202
        task_id_1 = r1.json()["task_id"]

        # Duplicate submission with same client request ID
        r2 = client.post(
            "/api/tasks",
            headers={**HEADERS, "X-Client-Request-ID": client_req_id},
            json=request_body("dedup.txt", "Duplicate submission"),
        )
        assert r2.status_code == 202
        task_id_2 = r2.json()["task_id"]

        assert task_id_1 == task_id_2

        # Verify task finishes
        result = wait_for_task(client, task_id_1)
        assert result["status"] == "succeeded"


# ── Sequenced Events Tests ────────────────────────────────────────────────


class TestSequencedEvents:
    def test_monotonic_event_ids_and_required_fields(self, settings):
        """Events use persistent autoincrement integer event_ids (not timestamps)."""
        services = build_services(settings)
        try:
            events = services.events
            e1 = events.record_event("task-1", "task.queued", {"tool": "fs.create_note"})
            e2 = events.record_event("task-1", "task.started", {"tool": "fs.create_note"})
            e3 = events.record_event("task-1", "task.succeeded", {"verified": True})

            # Check strictly monotonic ordering
            assert isinstance(e1.event_id, int)
            assert isinstance(e2.event_id, int)
            assert isinstance(e3.event_id, int)
            assert e1.event_id < e2.event_id < e3.event_id

            # Check all required fields present
            for ev in [e1, e2, e3]:
                assert ev.event_id > 0
                assert ev.task_id == "task-1"
                assert ev.event_type.startswith("task.")
                assert ev.timestamp  # non-empty ISO string
                assert isinstance(ev.safe_payload, dict)
        finally:
            services.close()

    def test_safe_payload_redaction(self):
        """Sensitive parameters (e.g. raw text, tokens, passwords) are masked in safe_payload."""
        raw = {
            "tool": "fs.create_note",
            "text": "super secret private note contents",
            "password": "my-secret-password",
            "token": "bearer-token-123",
            "nested": {"secret": "nested secret"},
            "safe_field": "hello.txt",
        }
        safe = sanitize_payload(raw)
        assert safe["safe_field"] == "hello.txt"
        assert safe["tool"] == "fs.create_note"
        assert "super secret" not in safe["text"]
        assert "<" in safe["text"] and "redacted" in safe["text"]
        assert safe["password"] == "<redacted>"
        assert safe["token"] == "<redacted>"
        assert safe["nested"]["secret"] == "<redacted>"

    def test_event_replay_order_after_cursor(self, settings):
        """Fetching events with after_cursor returns only events after that cursor in order."""
        services = build_services(settings)
        try:
            events = services.events
            e1 = events.record_event("task-A", "task.queued")
            e2 = events.record_event("task-A", "task.started")
            e3 = events.record_event("task-A", "task.succeeded")

            replayed = events.get_events(after_cursor=e1.event_id)
            assert len(replayed) == 2
            assert replayed[0].event_id == e2.event_id
            assert replayed[1].event_id == e3.event_id

            replayed_e2 = events.get_events(after_cursor=e2.event_id)
            assert len(replayed_e2) == 1
            assert replayed_e2[0].event_id == e3.event_id
        finally:
            services.close()


# ── SSE Streaming & Reconnection Tests ────────────────────────────────────


class TestEventStreaming:
    def test_sse_endpoint_requires_auth(self, client):
        """GET /api/events rejects unauthenticated requests."""
        assert client.get("/api/events").status_code == 401

    def test_sse_reconnect_receives_replay_and_snapshot(self, client):
        """Reconnecting with cursor returns events after cursor, followed by task.snapshot."""
        # 1. Create a task and wait for completion
        r = client.post("/api/tasks", headers=HEADERS, json=request_body("sse_test.txt"))
        assert r.status_code == 202
        task_id = r.json()["task_id"]
        wait_for_task(client, task_id)

        services = client.app.state.services

        async def check_stream():
            request = SimpleNamespace(app=client.app)

            async def connected():
                return False

            request.is_disconnected = connected
            initial = services.events.get_events(task_id=task_id)
            stream = task_event_stream(request, initial[0].event_id, task_id)
            try:
                chunks = []
                while True:
                    chunk = await asyncio.wait_for(anext(stream), timeout=2)
                    chunks.append(chunk)
                    if "event: task.snapshot" in chunk:
                        break
                assert "event: task.queued" not in "".join(chunks)
                assert "event: task.succeeded" in "".join(chunks)
                # Written exactly in the former replay/live handoff gap.
                live = services.events.record_event(task_id, "task.test_live")
                chunk = await asyncio.wait_for(anext(stream), timeout=2)
                assert f"id: {live.event_id}\n" in chunk
            finally:
                await stream.aclose()

        asyncio.run(check_stream())

    def test_real_authenticated_sse_reconnect_and_live_delivery(self, network_client):
        client, app = network_client
        assert client.get("/api/events").status_code == 401
        response = client.post("/api/tasks", headers=HEADERS, json=request_body("network.txt"))
        task_id = response.json()["task_id"]
        assert wait_for_task(client, task_id)["status"] == "succeeded"
        initial = app.state.services.events.get_events(task_id=task_id)
        with client.stream(
            "GET",
            f"/api/tasks/{task_id}/events",
            headers={**HEADERS, "Last-Event-ID": str(initial[0].event_id)},
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            lines = response.iter_lines()

            def next_record():
                for line in lines:
                    if line.startswith("data: "):
                        return json.loads(line[6:])
                raise AssertionError("Stream ended unexpectedly")

            replay = []
            while True:
                record = next_record()
                if record["event_type"] == "task.snapshot":
                    assert record["safe_payload"]["status"] == "succeeded"
                    break
                replay.append(record)
            assert [item["event_id"] for item in replay] == [e.event_id for e in initial[1:]]
            live = app.state.services.events.record_event(task_id, "task.live_test")
            assert next_record()["event_id"] == live.event_id

    @pytest.mark.parametrize(
        "url,headers,expected",
        [
            ("/api/events?cursor=-1", HEADERS, 422),
            ("/api/events", {**HEADERS, "Last-Event-ID": "bad"}, 422),
            ("/api/events?cursor=999999", HEADERS, 409),
            ("/api/tasks/missing/events", HEADERS, 404),
        ],
    )
    def test_invalid_cursors_and_missing_tasks(self, client, url, headers, expected):
        assert client.get(url, headers=headers).status_code == expected


def test_event_ids_survive_restart_and_concurrent_producers(settings):
    first = build_services(settings)
    event = first.events.record_event("task", "test.before_restart")
    first.close()
    second = build_services(settings)
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            produced = list(
                pool.map(
                    lambda i: second.events.record_event("task", "test.concurrent", {"index": i}),
                    range(40),
                )
            )
        stored = second.events.get_events(after_cursor=event.event_id)
        ids = [item.event_id for item in stored]
        assert len(ids) == len(set(ids)) == 40
        assert ids == sorted(item.event_id for item in produced)
        assert min(ids) > event.event_id
    finally:
        second.close()
