"""Bounded private phase evidence. Never record text, paths or exception messages."""

from __future__ import annotations

import inspect
import json
import os
import re
import time
from contextlib import contextmanager
from functools import wraps

from victus.adapters.uia.applications import UIABlocked, UIAUncertain


def safe_error(error):
    if isinstance(error, (UIABlocked, UIAUncertain)) and re.fullmatch(
        r"[A-Z][A-Z0-9_]{0,79}", str(error)
    ):
        return str(error)
    if isinstance(error, (TimeoutError, PermissionError, FileExistsError, ValueError)):
        return {
            TimeoutError: "PHASE_TIMEOUT",
            PermissionError: "PHASE_DENIED",
            FileExistsError: "DESTINATION_EXISTS",
            ValueError: "PHASE_VALUE_REJECTED",
        }.get(type(error), "PHASE_FAILED")
    return "PHASE_FAILED"


class PhaseDiagnostics:
    def __init__(self, path, task_id, *, limit=256):
        if not 1 <= limit <= 256 or not re.fullmatch(r"[a-f0-9]{32}", task_id):
            raise ValueError("Invalid diagnostic identity or bound")
        self.stream = path.open("x", encoding="utf-8")
        self.task_id, self.limit, self.count = task_id, limit, 0
        self.started = time.monotonic()

    def record(self, phase, state, *, elapsed_ms=0, error_code=None, metadata=None):
        if self.count >= self.limit:
            return
        if not re.fullmatch(r"[a-z0-9_.]{1,96}", phase):
            raise ValueError("Invalid diagnostic phase")
        if state not in {"started", "returned", "error", "unverified"} or (
            error_code is not None and not re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", error_code)
        ):
            raise ValueError("Invalid diagnostic state or code")
        safe = {}
        for key, value in (metadata or {}).items():
            if (
                key in {"app_ref", "control_ref"}
                and isinstance(value, str)
                and re.fullmatch(r"[a-f0-9]{32}", value)
            ):
                safe[key] = value
            elif (
                key
                in {
                    "owned_pid",
                    "process_created",
                    "window_dpi",
                    "window_handle",
                    "window_visible",
                    "matching_processes",
                    "matching_windows",
                    "inventory_truncated",
                }
                and type(value) is int
                and value >= 0
            ):
                safe[key] = value
        self.count += 1
        self.stream.write(
            json.dumps(
                {
                    "sequence": self.count,
                    "task_id": self.task_id,
                    "worker_pid": os.getpid(),
                    "phase": phase,
                    "state": state,
                    "elapsed_ms": round(elapsed_ms, 3),
                    "since_start_ms": round((time.monotonic() - self.started) * 1000, 3),
                    "error_code": error_code,
                    **safe,
                }
            )
            + "\n"
        )
        self.stream.flush()  # A killed worker still leaves its last entered phase.

    @contextmanager
    def phase(self, name, metadata=None):
        self.record(name, "started", metadata=metadata)
        started = time.monotonic()
        try:
            yield
        except BaseException as error:
            self.record(
                name,
                "error",
                elapsed_ms=(time.monotonic() - started) * 1000,
                error_code=safe_error(error),
                metadata=metadata,
            )
            raise
        else:
            self.record(
                name, "returned", elapsed_ms=(time.monotonic() - started) * 1000, metadata=metadata
            )

    def wrap(self, name, function):
        def metadata(args):
            value = args[-1] if args else None
            return {key: getattr(value, key, None) for key in ("app_ref", "control_ref")}

        def returned(result):
            if isinstance(result, dict):
                self.record(name, "returned", metadata=result)

        if inspect.iscoroutinefunction(function):

            @wraps(function)
            async def asynchronous(*args, **kwargs):
                with self.phase(name, metadata(args)):
                    result = await function(*args, **kwargs)
                    returned(result)
                    if result is False:
                        self.record(name, "unverified", error_code="POSTCONDITION_NOT_PROVED")
                    return result

            return asynchronous

        @wraps(function)
        def synchronous(*args, **kwargs):
            with self.phase(name, metadata(args)):
                result = function(*args, **kwargs)
                returned(result)
                if result is False:
                    self.record(name, "unverified", error_code="POSTCONDITION_NOT_PROVED")
                return result

        return synchronous

    def close(self):
        self.stream.close()
