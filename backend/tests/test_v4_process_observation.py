"""Read-only process observation with a fake OS boundary, runnable on Linux."""

import os
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from victus.runtime.owned_processes import OwnedProcessMonitor


def wait_until(predicate):
    end = time.monotonic() + 2
    while not predicate() and time.monotonic() < end:
        time.sleep(0.01)
    assert predicate()


def test_matching_process_name_does_not_make_unrelated_process_owned(tmp_path, monkeypatch):
    from victus.adapters.uia.applications import ProcessIdentity

    root_pid, child_pid, other_pid = os.getpid(), 987001, 987002
    binary = tmp_path / "chromium"
    binary.write_bytes(b"synthetic binary")
    lock = threading.Lock()
    identities = {
        root_pid: ProcessIdentity(root_pid, 1, "harness"),
        child_pid: ProcessIdentity(child_pid, 2, str(binary)),
        other_pid: ProcessIdentity(other_pid, 3, str(binary)),
    }
    entries = [
        (root_pid, 0, "harness"),
        (child_pid, root_pid, "chromium"),
        (other_pid, 999999, "chromium"),
    ]
    backend = Mock()

    def snapshot():
        with lock:
            return list(entries)

    backend._process_entries.side_effect = snapshot
    backend.identity.side_effect = lambda pid: identities[pid]
    monkeypatch.setattr("victus.adapters.uia.native.WindowsBackend", lambda: backend)
    monitor = OwnedProcessMonitor([binary])
    # Exercise the portable observation logic; start() intentionally rejects Linux.
    monitor._thread.start()
    assert monitor._ready.wait(2)
    try:
        wait_until(lambda: monitor.observed_count == 1)
        assert not monitor.quiescent()
        with lock:
            entries[:] = [row for row in entries if row[0] != child_pid]
        wait_until(monitor.quiescent)
        assert monitor.observed_count == 1
    finally:
        monitor.close()
    backend.terminate_owned.assert_not_called()
    backend.initialize.assert_called_once()
    backend.uninitialize.assert_called_once()


def test_process_identity_failure_prevents_cleanup_proof(tmp_path, monkeypatch):
    backend = Mock()
    backend.initialize.side_effect = RuntimeError("PRIVATE OS detail")
    monkeypatch.setattr("victus.adapters.uia.native.WindowsBackend", lambda: backend)
    monitor = OwnedProcessMonitor([tmp_path / "browser"])
    monitor._thread.start()
    assert monitor._ready.wait(2)
    monitor.close()
    assert monitor.error == "OWNED_PROCESS_OBSERVATION_FAILED"
    assert monitor.quiescent() is False
    assert "PRIVATE" not in monitor.error


def test_native_monitor_start_is_explicitly_windows_only(tmp_path, monkeypatch):
    import victus.runtime.owned_processes as module

    monitor = OwnedProcessMonitor([tmp_path / "browser"])
    monkeypatch.setattr(module, "os", SimpleNamespace(name="posix"))
    with pytest.raises(RuntimeError, match="REQUIRES_WINDOWS"):
        monitor.start()
