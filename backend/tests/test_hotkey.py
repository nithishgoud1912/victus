"""Shortcut wiring with a fake backend; does not register global keys."""

import threading
import time

from victus.bootstrap import build_services
from victus.runtime.hotkey import EmergencyShortcut
from victus.safety.cancellation import CancellationController
from victus.settings import Settings
from victus.tools.contracts import ActionRequest


class FakeHotkey:
    def __init__(self, available=True):
        self.available = available
        self.press = threading.Event()
        self.register_thread = None
        self.unregister_thread = None
        self.unregistered = threading.Event()

    def register(self):
        self.register_thread = threading.get_ident()
        return self.available

    def pressed(self):
        return self.press.is_set()

    def unregister(self):
        self.unregister_thread = threading.get_ident()
        self.unregistered.set()


def test_shortcut_calls_same_emergency_latch_and_unregisters():
    cancellation = CancellationController()
    backend = FakeHotkey()
    shortcut = EmergencyShortcut(cancellation.stop, lambda: backend)
    shortcut.start()
    try:
        assert shortcut.status == "registered"
        backend.press.set()
        assert cancellation.stopped.wait(timeout=1)
    finally:
        shortcut.close()
    assert backend.unregister_thread == backend.register_thread
    assert backend.register_thread != threading.get_ident()


def test_unavailable_shortcut_is_visible_and_does_not_stop_service():
    cancellation = CancellationController()
    shortcut = EmergencyShortcut(cancellation.stop, lambda: FakeHotkey(available=False))
    shortcut.start()
    shortcut.close()
    assert shortcut.status == "unavailable_or_in_use"
    assert not cancellation.stopped.is_set()


def test_shortcut_fixture_uses_service_stop_and_drains_queue(tmp_path):
    services = build_services(
        Settings(data_dir=tmp_path / "runtime", api_token="test-only-" + "x" * 40)
    )
    backend = FakeHotkey()
    shortcut = EmergencyShortcut(services.stop, lambda: backend)
    services.tasks.mutation_lock.acquire()
    try:
        action = ActionRequest(
            tool="fs.create_note", arguments={"filename": "key.txt", "text": "test"}
        )
        first, _ = services.tasks.enqueue(action)
        deadline = time.monotonic() + 3
        while services.tasks.queue.active_task_id != first and time.monotonic() < deadline:
            time.sleep(0.01)
        assert services.tasks.queue.active_task_id == first
        queued, _ = services.tasks.enqueue(action)
        shortcut.start()
        backend.press.set()
        assert services.tasks.stopped.wait(2)
        deadline = time.monotonic() + 3
        while (
            services.tasks.database.get(queued).status != "cancelled"
            and time.monotonic() < deadline
        ):
            time.sleep(0.01)
        assert services.tasks.database.get(queued).status == "cancelled"
        assert not (services.tasks.workspace / "key.txt").exists()
    finally:
        shortcut.close()
        services.tasks.mutation_lock.release()
        services.close()
    assert backend.unregister_thread == backend.register_thread


def test_shortcut_callback_error_is_visible_and_unregisters():
    backend = FakeHotkey()

    def broken_stop():
        raise RuntimeError("fixture component cleanup failure")

    shortcut = EmergencyShortcut(broken_stop, lambda: backend)
    shortcut.start()
    try:
        backend.press.set()
        assert backend.unregistered.wait(2)
        assert shortcut.status == "error"
    finally:
        shortcut.close()
    assert backend.unregister_thread == backend.register_thread


def test_shortcut_registration_error_is_visible_without_stopping():
    cancellation = CancellationController()

    def unavailable_backend():
        raise OSError("fixture Windows dependency unavailable")

    shortcut = EmergencyShortcut(cancellation.stop, unavailable_backend)
    shortcut.start()
    shortcut.close()
    assert shortcut.status == "error"
    assert not cancellation.stopped.is_set()
