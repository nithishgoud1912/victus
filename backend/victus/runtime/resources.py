"""Process-wide inference/mutation slots and cached, read-only pressure telemetry."""

import asyncio
import ctypes
import os
import shutil
import subprocess
import threading
import time
from collections import deque
from contextlib import asynccontextmanager, contextmanager


class ResourcePressure(RuntimeError):
    pass


def system_memory():
    if os.name == "nt":
        from ctypes import wintypes

        class Memory(ctypes.Structure):
            _fields_ = [
                ("length", wintypes.DWORD),
                ("load", wintypes.DWORD),
                *[
                    (name, ctypes.c_ulonglong)
                    for name in (
                        "total",
                        "available",
                        "page",
                        "available_page",
                        "virtual",
                        "available_virtual",
                        "extended",
                    )
                ],
            ]

        value = Memory()
        value.length = ctypes.sizeof(value)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
            return {}

        class Counters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("faults", wintypes.DWORD),
                *[
                    (name, ctypes.c_size_t)
                    for name in (
                        "peak",
                        "rss",
                        "pool_peak",
                        "pool",
                        "nonpaged_peak",
                        "nonpaged",
                        "pagefile",
                        "pagefile_peak",
                    )
                ],
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("kernel32")
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        ctypes.windll.psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        )
        return {
            "available_bytes": value.available,
            "total_bytes": value.total,
            "process_rss_bytes": counters.rss if ok else None,
        }
    try:
        from pathlib import Path

        data = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
        page_size = os.sysconf("SC_PAGE_SIZE")
        rss = int(Path("/proc/self/statm").read_text().split()[1]) * page_size
        return {
            "available_bytes": int(data["MemAvailable"].split()[0]) * 1024,
            "total_bytes": int(data["MemTotal"].split()[0]) * 1024,
            "process_rss_bytes": rss,
        }
    except (OSError, ValueError, KeyError):
        return {}


def gpu_memory():
    executable = shutil.which("nvidia-smi")
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            timeout=2,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        rows = [
            [int(x.strip()) for x in row.split(",")] for row in result.stdout.decode().splitlines()
        ]
        return {
            "used_bytes": sum(x[0] for x in rows) * 1024**2,
            "total_bytes": sum(x[1] for x in rows) * 1024**2,
        }
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


class ResourceSupervisor:
    def __init__(self, *, min_available=2 * 1024**3, probe=system_memory):
        self.inference = threading.Lock()
        self.mutation = threading.Lock()
        self.min_available, self.probe = min_available, probe
        self.context_tokens = 4096
        self.max_queued = 3
        self._lock = threading.Lock()
        self._sample = {"available_bytes": None, "process_rss_bytes": None}
        self._timings = deque(maxlen=128)
        self._seen = set()
        self._allocation_errors = 0
        self._closing = threading.Event()
        self._thread = None
        self._users = 0

    def start(self):
        with self._lock:
            self._users += 1
            if self._thread is None:
                self._closing.clear()
                self._thread = threading.Thread(
                    target=self._sample_loop, name="victus-resources", daemon=True
                )
                self._thread.start()

    def _sample_loop(self):
        last_gpu = 0.0
        while not self._closing.is_set():
            try:
                sample = self.probe()
                with self._lock:
                    self._sample.update(sample, sampled_at=time.time())
                if time.monotonic() - last_gpu > 30:
                    gpu = gpu_memory()
                    with self._lock:
                        self._sample["vram"] = gpu
                    last_gpu = time.monotonic()
            except Exception:
                with self._lock:
                    self._sample["telemetry_error"] = True
            self._closing.wait(1)

    def snapshot(self):
        with self._lock:
            return {
                **self._sample,
                "inference_busy": self.inference.locked(),
                "mutation_busy": self.mutation.locked(),
                "context_tokens": self.context_tokens,
                "stt_device": "cpu",
                "max_queued": self.max_queued,
                "allocation_errors": self._allocation_errors,
                "timings": list(self._timings),
            }

    def check(self):
        with self._lock:
            available = self._sample.get("available_bytes")
            if (
                available is not None and available < self.min_available
            ) or self._allocation_errors >= 2:
                raise ResourcePressure("LOCAL_RESOURCE_PRESSURE")

    def check_disk(self, root, *, required=64 * 1024**2):
        try:
            if shutil.disk_usage(root).free < required:
                raise ResourcePressure("LOCAL_DISK_PRESSURE")
        except OSError:
            raise ResourcePressure("LOCAL_DISK_UNAVAILABLE") from None

    def allocation_failed(self):
        with self._lock:
            self._allocation_errors += 1

    def _record(self, kind, started, failed, warm=None):
        with self._lock:
            self._timings.append(
                {
                    "kind": kind,
                    "warm": kind in self._seen if warm is None else warm,
                    "seconds": time.monotonic() - started,
                    "failed": failed,
                }
            )
            self._seen.add(kind)

    @contextmanager
    def inference_slot(self, kind, cancel=None, timeout=90, warm=None):
        deadline = time.monotonic() + timeout
        while True:
            self.check()
            if cancel is not None and cancel.is_set():
                raise ResourcePressure("INFERENCE_CANCELLED")
            if time.monotonic() >= deadline:
                raise ResourcePressure("INFERENCE_SLOT_TIMEOUT")
            if self.inference.acquire(timeout=0.025):
                break
        started, failed = time.monotonic(), True
        try:
            self.check()
            yield
            failed = False
        except MemoryError:
            self.allocation_failed()
            raise
        finally:
            self._record(kind, started, failed, warm)
            self.inference.release()

    @asynccontextmanager
    async def async_inference_slot(self, kind, cancel=None, timeout=60):
        deadline = time.monotonic() + timeout
        while True:
            self.check()
            if cancel is not None and cancel.is_set():
                raise ResourcePressure("INFERENCE_CANCELLED")
            if time.monotonic() >= deadline:
                raise ResourcePressure("INFERENCE_SLOT_TIMEOUT")
            if self.inference.acquire(blocking=False):
                break
            await asyncio.sleep(0.02)
        started, failed = time.monotonic(), True
        try:
            self.check()
            yield
            failed = False
        except MemoryError:
            self.allocation_failed()
            raise
        finally:
            self._record(kind, started, failed)
            self.inference.release()

    def close(self):
        with self._lock:
            self._users = max(0, self._users - 1)
            if self._users:
                return
            self._closing.set()
            thread = self._thread
        if thread is not None:
            thread.join(timeout=3)
            if thread.is_alive():
                raise RuntimeError("Resource sampler did not stop")
        with self._lock:
            self._thread = None


_DEFAULT = ResourceSupervisor()


def resources():
    return _DEFAULT
