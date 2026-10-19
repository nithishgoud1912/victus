"""Read-only Windows process-tree observation for qualification, never cleanup authority."""

import os
import threading
import time
from pathlib import Path


class OwnedProcessMonitor:
    """Track exact creation identities of matching descendants of this harness.

    Historical descendants remain tracked after reparenting. No PID discovered
    here is ever terminated. Observation errors prevent a qualification pass.
    """

    def __init__(self, binaries):
        self.binaries = {os.path.normcase(str(Path(p).resolve())) for p in binaries}
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._lock = threading.Lock()
        self._remaining = set()
        self._observed = set()
        self._error = None
        self._sampled = 0.0
        self._thread = threading.Thread(target=self._observe, daemon=True)

    def start(self):
        if os.name != "nt":
            raise RuntimeError("OWNED_PROCESS_PROBE_REQUIRES_WINDOWS")
        self._thread.start()
        if not self._ready.wait(5) or self.error:
            self.close()
            raise RuntimeError("OWNED_PROCESS_PROBE_UNAVAILABLE")
        return self

    @property
    def error(self):
        with self._lock:
            return self._error

    @property
    def observed_count(self):
        with self._lock:
            return len(self._observed)

    def quiescent(self):
        with self._lock:
            return (
                self._error is None
                and self._sampled > 0
                and time.monotonic() - self._sampled < 1
                and not self._remaining
            )

    def _observe(self):
        from victus.adapters.uia.native import WindowsBackend

        backend = WindowsBackend()
        initialized = False
        try:
            backend.initialize()
            initialized = True
            root = backend.identity(os.getpid())
            known = {root.pid: root}
            while not self._stop.is_set():
                entries = backend._process_entries()
                if len(entries) > 65536:
                    raise RuntimeError("PROCESS_INVENTORY_LIMIT")
                parents = {pid: parent for pid, parent, _ in entries}
                live = {}
                # Prove each retained parent is still the same process before
                # inheriting its ancestry. PID reuse never grants ownership.
                for pid, identity in known.items():
                    if pid in parents:
                        try:
                            current = backend.identity(pid)
                        except Exception:
                            if not any(entry[0] == pid for entry in backend._process_entries()):
                                continue
                            raise RuntimeError("PROCESS_IDENTITY_UNAVAILABLE") from None
                        if current == identity:
                            live[pid] = current
                pending = list(entries)
                for _ in range(64):
                    added = False
                    for pid, parent, _ in pending:
                        if pid in live or parent not in live:
                            continue
                        try:
                            identity = backend.identity(pid)
                        except Exception:
                            # A child may exit between the two OS calls.
                            if not any(entry[0] == pid for entry in backend._process_entries()):
                                continue
                            raise RuntimeError("PROCESS_IDENTITY_UNAVAILABLE") from None
                        if identity.created < live[parent].created:
                            continue
                        live[pid] = identity
                        added = True
                    if not added:
                        break
                else:
                    raise RuntimeError("PROCESS_ANCESTRY_LIMIT")
                if len(live) > 4096:
                    raise RuntimeError("OWNED_PROCESS_LIMIT")
                known.update(live)
                remaining = {
                    (identity.pid, identity.created)
                    for identity in live.values()
                    if os.path.normcase(identity.executable) in self.binaries
                }
                with self._lock:
                    self._observed.update(remaining)
                    self._remaining = remaining
                    self._sampled = time.monotonic()
                self._ready.set()
                self._stop.wait(0.025)
        except Exception:
            with self._lock:
                self._error = "OWNED_PROCESS_OBSERVATION_FAILED"
            self._ready.set()
        finally:
            if initialized:
                try:
                    backend.uninitialize()
                except Exception:
                    with self._lock:
                        self._error = "OWNED_PROCESS_OBSERVER_CLEANUP_FAILED"

    def close(self):
        self._stop.set()
        if self._thread.ident is not None:
            self._thread.join(5)
        if self._thread.is_alive():
            raise RuntimeError("OWNED_PROCESS_OBSERVER_DID_NOT_STOP")
