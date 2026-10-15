"""Shortcut wiring with a fake backend; does not register global keys."""

import threading

from victus.runtime.hotkey import EmergencyShortcut
from victus.safety.cancellation import CancellationController


class FakeHotkey:
    def __init__(self, available=True):
        self.available = available
        self.press = threading.Event()
        self.register_thread = None
        self.unregister_thread = None

    def register(self):
        self.register_thread = threading.get_ident()
        return self.available

    def pressed(self):
        return self.press.is_set()

    def unregister(self):
        self.unregister_thread = threading.get_ident()


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
