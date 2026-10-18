"""Real spawned workers, isolated effects and bounded stop/deadline tests."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from worker_support import (
    blocking_effect,
    cooperative_effect,
    crashing_effect,
    error_with_private_text,
    gated_effect,
    partial_write_effect,
)

from victus.adapters.filesystem.operations import create_note
from victus.api.app import create_app
from victus.bootstrap import build_services
from victus.runtime.resources import resources
from victus.runtime.supervisor import WorkerSupervisor
from victus.safety.cancellation import CancellationController
from victus.settings import Settings
from victus.tools.contracts import ActionRequest, TaskResult
from victus.tools.registry import ToolRegistry

TOKEN = "tests-only-" + "x" * 40
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def body(filename="effect.txt"):
    return {"tool": "fs.create_note", "arguments": {"filename": filename, "text": "effect"}}


def until(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(0.01)
    raise AssertionError("Condition not reached within bounded wait")


def finished(tasks, task_id):
    def terminal():
        task = tasks.database.get(task_id)
        return task if task and task.status not in {"queued", "running", "prepared"} else None

    return until(terminal)


def configure(tasks, execute=create_note, *, cooperative=None, timeout=5):
    original = tasks.registry.get("fs.create_note")
    registry = ToolRegistry()
    registry.register(
        replace(
            original,
            execute=execute,
            execute_cancellable=cooperative,
            timeout_seconds=timeout,
        )
    )
    tasks.registry = registry
    tasks.dispatcher.registry = registry


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "runtime", api_token=TOKEN)


@pytest.fixture
def services(settings):
    instance = build_services(settings)
    try:
        yield instance
    finally:
        instance.close()


def test_deadline_terminates_owned_process_and_preserves_unknown(services):
    tasks = services.tasks
    configure(tasks, blocking_effect, timeout=2)
    task_id, _ = tasks.enqueue(ActionRequest.model_validate(body()))
    until(lambda: (tasks.workspace / "effect.txt").exists())
    result = finished(tasks, task_id)
    assert result.status == "unknown" and not result.verified
    assert result.error_code == "WORKER_DEADLINE_EXCEEDED"
    assert tasks.queue.supervisor.active_pid is None
    assert services.ledger.get(result.action_id).status == "unknown"
    # Deadline does not silently retry the effect, and the scheduler remains usable.
    configure(tasks)
    next_id, _ = tasks.enqueue(ActionRequest.model_validate(body("next.txt")))
    assert finished(tasks, next_id).status == "succeeded"


def test_killed_partial_write_stays_unknown_without_retry_after_restart(settings):
    instance = build_services(settings)
    try:
        tasks = instance.tasks
        configure(tasks, partial_write_effect, timeout=2)
        action = ActionRequest.model_validate(body("partial.txt"))
        task_id, _ = tasks.enqueue(action, "partial-write-request")
        output = tasks.workspace / "partial.txt"
        until(lambda: output.exists() and output.read_bytes() == b"partial")
        result = finished(tasks, task_id)
        assert result.status == "unknown" and not result.verified
        assert result.error_code == "WORKER_DEADLINE_EXCEEDED"
        assert tasks.queue.supervisor.active_pid is None
        assert instance.ledger.get(result.action_id).status == "unknown"
        assert output.read_bytes() == b"partial"

        def terminal_events():
            batch = instance.events.get_events(task_id=task_id)
            return batch if any(event.event_type == "task.unknown" for event in batch) else None

        events = until(terminal_events)
        assert [event.event_type for event in events] == [
            "task.queued",
            "task.started",
            "task.unknown",
        ]
    finally:
        instance.close()

    resumed = build_services(settings)
    try:
        assert resumed.tasks.database.get(task_id).status == "unknown"
        assert resumed.ledger.get(result.action_id).status == "unknown"
        # Reconnecting/resubmitting the same request cannot replay the partial write.
        assert resumed.tasks.enqueue(action, "partial-write-request") == (task_id, False)
        next_id, _ = resumed.tasks.enqueue(ActionRequest.model_validate(body("after-partial.txt")))
        assert finished(resumed.tasks, next_id).status == "succeeded"
        assert output.read_bytes() == b"partial"
        assert (settings.workspace / "write-attempts.txt").read_text().splitlines() == ["attempt"]
        with resumed.tasks.database.connect() as connection:
            attempts = connection.execute(
                "SELECT COUNT(*) FROM action_attempts WHERE expected_effect_ref = ?",
                (f"task:{task_id}",),
            ).fetchone()[0]
        assert attempts == 1
    finally:
        resumed.close()


def test_stop_signals_cooperative_worker_and_cancels_queue(settings):
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        tasks = client.app.state.services.tasks
        configure(tasks, cooperative=cooperative_effect, timeout=15)
        first = client.post("/api/tasks", headers=HEADERS, json=body()).json()["task_id"]
        until(lambda: (tasks.workspace / "effect.txt").exists())
        queued = [
            client.post("/api/tasks", headers=HEADERS, json=body(f"q{i}.txt")).json()["task_id"]
            for i in range(3)
        ]
        started = time.monotonic()
        assert client.post("/api/stop", headers=HEADERS).status_code == 200
        assert time.monotonic() - started < 2
        assert finished(tasks, first).status == "unknown"
        assert (tasks.workspace / "effect.txt").read_text() == "effect"
        assert (tasks.workspace / "cooperated.txt").exists()
        assert all(finished(tasks, task_id).status == "cancelled" for task_id in queued)
        assert not any((tasks.workspace / f"q{i}.txt").exists() for i in range(3))
        assert tasks.queue.queued_count == 0
        assert (
            client.post("/api/tasks", headers=HEADERS, json=body("later.txt")).json()["status"]
            == "cancelled"
        )
        assert not (tasks.workspace / "later.txt").exists()


def test_stop_kills_noncooperative_worker_and_close_releases_ownership(settings):
    services = build_services(settings)
    tasks = services.tasks
    configure(tasks, blocking_effect, timeout=30)
    task_id, _ = tasks.enqueue(ActionRequest.model_validate(body()))
    until(lambda: (tasks.workspace / "effect.txt").exists())
    start = time.monotonic()
    services.close()
    assert time.monotonic() - start < 3
    assert finished(tasks, task_id).error_code == "STOPPED_DURING_ACTION"
    assert tasks.queue.supervisor.active_pid is None
    assert not tasks.queue._worker_thread.is_alive()
    resumed = build_services(settings)
    try:
        assert not resumed.tasks.stopped.is_set()
        assert resumed.tasks.database.get(task_id).status == "unknown"
    finally:
        resumed.close()


@pytest.mark.parametrize(
    "operation,code",
    [(crashing_effect, "WORKER_EXITED"), (error_with_private_text, "WORKER_ERROR")],
)
def test_crash_and_errors_are_unknown_and_redacted(services, operation, code):
    configure(services.tasks, operation)
    task_id, _ = services.tasks.enqueue(ActionRequest.model_validate(body()))
    result = finished(services.tasks, task_id)
    assert result.status == "unknown" and result.error_code == code
    assert services.ledger.get(result.action_id).status == "unknown"
    assert "private payload" not in str(services.events.get_events(task_id=task_id))


def test_queued_and_synchronous_calls_share_one_mutation_slot(services):
    tasks = services.tasks
    configure(tasks, gated_effect, timeout=15)
    first_id, _ = tasks.enqueue(ActionRequest.model_validate(body("first.txt")))
    until(lambda: (tasks.workspace / "first.txt.started").exists())
    second_id, _ = tasks.enqueue(ActionRequest.model_validate(body("second.txt")))
    with ThreadPoolExecutor(max_workers=1) as pool:
        third = pool.submit(tasks.run, ActionRequest.model_validate(body("third.txt")))
        until(lambda: tasks.queue.queued_count == 2)
        assert not (tasks.workspace / "second.txt.started").exists()
        assert not (tasks.workspace / "third.txt.started").exists()
        (tasks.workspace / "release.txt").write_text("release", encoding="utf-8")
        assert third.result(timeout=8).status == "succeeded"
    assert finished(tasks, first_id).status == "succeeded"
    assert finished(tasks, second_id).status == "succeeded"


def test_stop_during_mutation_lock_wait_dispatches_nothing(services):
    tasks = services.tasks
    tasks.mutation_lock.acquire()
    try:
        task_id, _ = tasks.enqueue(ActionRequest.model_validate(body()))
        until(lambda: tasks.queue.active_task_id == task_id)
        tasks.stop()
        assert finished(tasks, task_id).status == "cancelled"
        assert tasks.queue.supervisor.active_pid is None
        assert not (tasks.workspace / "effect.txt").exists()
    finally:
        tasks.mutation_lock.release()


def test_dispatch_barrier_rejects_start_after_stop():
    controller = CancellationController()
    controller.stop()
    starts = []
    assert controller.start(lambda: starts.append(True), None) is False
    assert starts == []


def test_stop_racing_with_worker_launch_signals_that_worker():
    controller = CancellationController()
    entered = threading.Event()
    release = threading.Event()
    signal = threading.Event()

    def launch():
        entered.set()
        assert release.wait(timeout=2)

    with ThreadPoolExecutor(max_workers=2) as pool:
        starting = pool.submit(controller.start, launch, signal)
        assert entered.wait(timeout=2)
        stopping = pool.submit(controller.stop)
        release.set()
        assert starting.result(timeout=2) is True
        stopping.result(timeout=2)
    assert signal.is_set() and controller.stopped.is_set()
    assert controller.start(lambda: None, threading.Event()) is False


def test_unpicklable_tool_fails_before_process_creation(services):
    configure(services.tasks, lambda workspace, args: create_note(workspace, args))
    result = services.tasks.run(ActionRequest.model_validate(body()))
    assert result.status == "failed" and result.error_code == "WORKER_START_FAILED"
    assert services.tasks.queue.supervisor.active_pid is None
    assert not (services.tasks.workspace / "effect.txt").exists()


def test_stop_racing_submissions_leaves_no_orphaned_work(services):
    tasks = services.tasks
    tasks.mutation_lock.acquire()
    try:
        barrier = threading.Barrier(9)

        def submit(index):
            barrier.wait(timeout=3)
            try:
                return tasks.enqueue(ActionRequest.model_validate(body(f"race{index}.txt")))[0]
            except Exception as error:
                from victus.tasks.queue import QueueFullError

                assert isinstance(error, QueueFullError)
                return None

        with ThreadPoolExecutor(max_workers=9) as pool:
            pending = [pool.submit(submit, i) for i in range(8)]
            barrier.wait(timeout=3)
            tasks.stop()
            task_ids = [future.result(timeout=3) for future in pending]
        for task_id in filter(None, task_ids):
            assert finished(tasks, task_id).status == "cancelled"
        assert not list(tasks.workspace.glob("race*.txt"))
        assert tasks.queue.queued_count == 0
    finally:
        tasks.mutation_lock.release()


def test_restart_cancels_abandoned_queue_and_retains_deduplication(settings):
    services = build_services(settings)
    task = TaskResult(task_id="abandoned", tool="fs.create_note", status="queued")
    services.tasks.database.save(task)
    with services.tasks.database.connect() as conn:
        conn.execute(
            "INSERT INTO client_requests (client_request_id,task_id) VALUES (?,?)",
            ("restart-request", task.task_id),
        )
    aid = services.ledger.prepare_action("fs.create_note", "1", {})
    services.ledger.mark_dispatching(aid)
    services.close()
    resumed = build_services(settings)
    try:
        assert resumed.tasks.database.get(task.task_id).status == "cancelled"
        assert resumed.tasks.enqueue(ActionRequest.model_validate(body()), "restart-request") == (
            task.task_id,
            False,
        )
        assert resumed.ledger.get(aid).status == "unknown"
        assert not resumed.ledger.list_unfinished()
        assert not (settings.workspace / "effect.txt").exists()
    finally:
        resumed.close()


@pytest.mark.parametrize("deadline", [0, -1, float("inf"), float("nan")])
def test_invalid_deadline_cannot_dispatch(services, deadline):
    configure(services.tasks, timeout=deadline)
    result = services.tasks.run(ActionRequest.model_validate(body()))
    assert result.error_code == "INVALID_DEADLINE"
    assert not (services.tasks.workspace / "effect.txt").exists()


def test_mutation_wait_has_finite_budget_without_dispatch(services):
    tasks = services.tasks
    configure(tasks, timeout=0.1)
    tasks.mutation_lock.acquire()
    try:
        task_id, _ = tasks.enqueue(ActionRequest.model_validate(body()))
        result = finished(tasks, task_id)
        assert result.status == "failed" and result.error_code == "MUTATION_SLOT_TIMEOUT"
        assert result.action_id is None
        assert tasks.queue.supervisor.active_pid is None
        assert not (tasks.workspace / "effect.txt").exists()
    finally:
        tasks.mutation_lock.release()


def test_shutdown_optional_failure_still_stops_and_reaps_worker(settings, monkeypatch):
    from victus.runtime.instance_lock import InstanceLock

    instance = build_services(settings)
    original_close = instance.voice.close
    configure(instance.tasks, blocking_effect, timeout=30)
    task_id, _ = instance.tasks.enqueue(ActionRequest.model_validate(body()))
    until(lambda: (instance.tasks.workspace / "effect.txt").exists())

    def broken_voice_close():
        raise RuntimeError("VOICE_SHUTDOWN_FAILED")

    monkeypatch.setattr(instance.voice, "close", broken_voice_close)
    try:
        with pytest.raises(RuntimeError):
            instance.close()
        assert instance.tasks.stopped.is_set()
        assert instance.tasks.queue.supervisor.active_pid is None
        assert not instance.tasks.queue._worker_thread.is_alive()
        assert finished(instance.tasks, task_id).status == "unknown"
        contender = InstanceLock(settings.data_dir)
        with pytest.raises(RuntimeError, match="owns this data directory"):
            contender.acquire()
    finally:
        monkeypatch.setattr(instance.voice, "close", original_close)
        instance.close()


class StubbornProcess:
    """Deterministic unkillable owned process; never targets a real OS PID."""

    def __init__(self, signal, *, partial_start=False):
        self.pid = None
        self.signal = signal
        self.partial_start = partial_start
        self.alive = False
        self.operations = []

    def start(self):
        self.pid = 123456
        self.alive = True
        if self.partial_start:
            raise OSError("partial spawn failure")

    def is_alive(self):
        return self.alive

    def join(self, timeout):
        self.operations.append(("join", timeout, self.signal.is_set()))

    def terminate(self):
        self.operations.append(("terminate", self.signal.is_set()))

    def kill(self):
        self.operations.append(("kill", self.signal.is_set()))

    def close(self):
        assert not self.alive
        self.operations.append(("close",))


class StubbornContext:
    def __init__(self, *, partial_start=False, ready_result=False):
        self.signal = threading.Event()
        self.process = StubbornProcess(self.signal, partial_start=partial_start)
        self.ready_result = ready_result

    def Pipe(self, **kwargs):
        from victus.tools.dispatcher import DispatchOutcome

        endpoint = SimpleNamespace(
            poll=lambda timeout: self.ready_result,
            close=lambda: None,
            recv=lambda: DispatchOutcome("succeeded", verified=True),
        )
        return endpoint, endpoint

    def Event(self):
        return self.signal

    def Process(self, **kwargs):
        return self.process


@pytest.mark.parametrize(
    "partial_start,ready_result", [(False, False), (True, False), (False, True)]
)
def test_unreapable_owned_worker_retains_slot_and_latches_stop(
    services, partial_start, ready_result
):
    configure(services.tasks, timeout=0.1)
    cancellation = CancellationController()
    supervisor = WorkerSupervisor(cancellation)
    fake = StubbornContext(partial_start=partial_start, ready_result=ready_result)
    supervisor.context = fake
    try:
        with pytest.raises(RuntimeError, match="Owned worker could not be stopped"):
            supervisor.run(services.tasks.dispatcher, ActionRequest.model_validate(body()))
        assert cancellation.stopped.is_set()
        assert fake.signal.is_set()
        assert supervisor.active_pid == fake.process.pid
        assert resources().mutation.locked()
        assert any(op[0] == "terminate" for op in fake.process.operations)
        assert any(op[0] == "kill" for op in fake.process.operations)
        assert all(op[-1] is True for op in fake.process.operations)
    finally:
        # The only surviving process here is a fake. Explicit fixture cleanup
        # must never be copied into production or used to release a live owner.
        fake.process.alive = False
        supervisor._reap(fake.process)
        supervisor._process = None
        if resources().mutation.locked():
            resources().mutation.release()


def test_stop_after_durable_dispatch_intent_never_calls_adapter(services, monkeypatch):
    from victus.storage.action_ledger import ActionLedger

    signal = threading.Event()
    original = ActionLedger.mark_dispatching

    def stop_at_commit(ledger, action_id):
        original(ledger, action_id)
        signal.set()

    monkeypatch.setattr(ActionLedger, "mark_dispatching", stop_at_commit)
    result = services.tasks.dispatcher.dispatch(ActionRequest.model_validate(body()), signal)
    assert result.status == "unknown" and not result.verified
    assert not (services.tasks.workspace / "effect.txt").exists()


def test_queue_keeps_mutation_and_directory_ownership_if_reaping_fails(settings):
    from victus.runtime.instance_lock import InstanceLock

    instance = build_services(settings)
    # Include durable task/intent preparation before this fake reaches dispatch.
    configure(instance.tasks, timeout=0.5)
    fake = StubbornContext()
    supervisor = instance.tasks.queue.supervisor
    supervisor.context = fake
    try:
        task_id, _ = instance.tasks.enqueue(ActionRequest.model_validate(body()))
        assert finished(instance.tasks, task_id).status == "unknown"
        assert instance.tasks.stopped.is_set()
        assert supervisor.active_pid == fake.process.pid
        assert instance.tasks.mutation_lock.locked()
        with pytest.raises(RuntimeError, match="ownership retained"):
            instance.close()
        contender = InstanceLock(settings.data_dir)
        with pytest.raises(RuntimeError, match="owns this data directory"):
            contender.acquire()
    finally:
        # This is a fake, not an OS worker. Real ownership must remain latched
        # until a real successful reap; no release/reset endpoint is introduced.
        fake.process.alive = False
        supervisor._reap(fake.process)
        supervisor._process = None
        if instance.tasks.mutation_lock.locked():
            instance.tasks.mutation_lock.release()
        instance.close()


def test_retained_directory_owner_survives_caller_unwind(tmp_path):
    import gc
    import weakref

    from victus.runtime.instance_lock import InstanceLock

    owner = InstanceLock(tmp_path)
    owner.acquire()
    owner.retain()
    reference = weakref.ref(owner)
    del owner
    gc.collect()
    contender = InstanceLock(tmp_path)
    try:
        assert reference() is not None
        with pytest.raises(RuntimeError, match="owns this data directory"):
            contender.acquire()
    finally:
        if reference() is not None:
            reference().release()
    contender.acquire()
    contender.release()


def test_stop_optional_failure_still_cancels_queue_and_voice(services, monkeypatch):
    tasks = services.tasks
    tasks.mutation_lock.acquire()
    voice_stopped = []
    original_stop = services.voice.stop

    def stop_voice():
        voice_stopped.append(True)
        original_stop()

    def cloud_failure():
        raise RuntimeError("cloud cleanup failure")

    services.cloud = SimpleNamespace(clear=cloud_failure)
    monkeypatch.setattr(services.voice, "stop", stop_voice)
    try:
        first, _ = tasks.enqueue(ActionRequest.model_validate(body()))
        until(lambda: tasks.queue.active_task_id == first)
        pending = [
            tasks.enqueue(ActionRequest.model_validate(body(f"pending{i}.txt")))[0]
            for i in range(2)
        ]
        with pytest.raises(RuntimeError, match="Stop latched"):
            services.stop()
        assert voice_stopped == [True]
        assert tasks.queue.queued_count == 0
        assert all(finished(tasks, task_id).status == "cancelled" for task_id in [first, *pending])
        assert list(tasks.workspace.iterdir()) == []
    finally:
        services.cloud = None
        tasks.mutation_lock.release()


def test_startup_cleanup_failure_retains_directory_and_still_closes_tasks(settings, monkeypatch):
    import victus.bootstrap as bootstrap
    from victus.runtime.instance_lock import _RETAINED_LOCKS, InstanceLock

    created = []
    original_tasks = bootstrap.TaskService

    def track_tasks(*args, **kwargs):
        instance = original_tasks(*args, **kwargs)
        created.append(instance)
        return instance

    class BrokenShortcut:
        def __init__(self, stop):
            pass

        def start(self):
            raise RuntimeError("shortcut startup fixture")

        def close(self):
            raise RuntimeError("shortcut cleanup fixture")

    monkeypatch.setattr(bootstrap, "TaskService", track_tasks)
    monkeypatch.setattr(bootstrap, "EmergencyShortcut", BrokenShortcut)
    configured = replace(settings, emergency_hotkey=True)
    retained = None
    try:
        with pytest.raises(RuntimeError, match="shortcut startup fixture"):
            build_services(configured)
        assert len(created) == 1 and created[0].stopped.is_set()
        assert not created[0].queue._worker_thread.is_alive()
        assert created[0].queue.supervisor.active_pid is None
        retained = next(
            owner for owner in _RETAINED_LOCKS if owner.path == settings.data_dir / "instance.lock"
        )
        with pytest.raises(RuntimeError, match="owns this data directory"):
            InstanceLock(settings.data_dir).acquire()
    finally:
        if retained is not None:
            retained.release()  # Actual owners are stopped; shortcut is a fake.
