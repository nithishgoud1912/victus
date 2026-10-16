"""Bounded local stdio transport. Only the bundled pinned server may launch.

On Windows a kill-on-close Job Object prevents an orphan server if the outer
task worker is terminated. Server stderr is discarded, never forwarded to audit.
"""

import hashlib
import importlib.metadata
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from victus.adapters.mcp import reference_server

PROTOCOL = "2025-11-25"
# Updated only with a reviewed server release, not derived from discovered output.
REFERENCE_SHA256 = "9378c743aae3c8000efae931b7350eb0043f177824eeb39748999c78be049b24"


class MCPError(RuntimeError):
    def __init__(self, code="MCP_PROTOCOL_ERROR"):
        super().__init__(code)


class LocalMCPClient:
    def __init__(self, workspace: Path, *, cancelled=None, timeout=4.0):
        if not 0 < timeout <= 10:
            raise ValueError("Invalid MCP timeout")
        self.workspace = workspace.resolve(strict=True)
        self.cancelled, self.timeout = cancelled, timeout
        self.process = self.job = self.reader = None
        self.messages = queue.Queue(maxsize=2)
        self.reader_failed = threading.Event()
        self.sequence = 0

    def __enter__(self):
        source = Path(reference_server.__file__).read_bytes().replace(b"\r\n", b"\n")
        if (importlib.metadata.version("victus-assistant") != "0.1.0"
                or hashlib.sha256(source).hexdigest() != REFERENCE_SHA256):
            raise MCPError("MCP_SERVER_PIN_MISMATCH")
        self.deadline = time.monotonic() + self.timeout
        self._check()
        env = {k: v for k, v in os.environ.items()
               if k.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH"}}
        try:
            command = ([sys.executable, "mcp-note-server"] if getattr(sys, "frozen", False)
                       else [sys.executable, "-I", "-m", "victus.adapters.mcp.reference_server"])
            self.process = subprocess.Popen(
                [*command, "--workspace", str(self.workspace)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                env=env, cwd=self.workspace,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if os.name == "nt":
                import win32api
                import win32job

                self.job = win32job.CreateJobObject(None, "")
                limits = win32job.QueryInformationJobObject(
                    self.job, win32job.JobObjectExtendedLimitInformation)
                limits["BasicLimitInformation"]["LimitFlags"] |= (
                    win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
                win32job.SetInformationJobObject(
                    self.job, win32job.JobObjectExtendedLimitInformation, limits)
                handle = win32api.OpenProcess(0x0100 | 0x0001, False, self.process.pid)
                try:
                    win32job.AssignProcessToJobObject(self.job, handle)
                finally:
                    handle.Close()
            self.reader = threading.Thread(target=self._read, daemon=True)
            self.reader.start()
            result = self.call("initialize", {"protocolVersion": PROTOCOL,
                "capabilities": {}, "clientInfo": {"name": "victus", "version": "0.1.0"}})
            if (result.get("protocolVersion") != PROTOCOL
                    or result.get("serverInfo") != {"name": "victus-note", "version": "0.1.0"}
                    or result.get("capabilities") != {"tools": {"listChanged": False}}):
                raise MCPError("MCP_SERVER_IDENTITY_MISMATCH")
            self._write({"jsonrpc": "2.0", "method": "notifications/initialized"})
            return self
        except Exception:
            self.close()
            raise MCPError("MCP_START_FAILED") from None

    def _check(self):
        if self.cancelled is not None and self.cancelled.is_set():
            raise MCPError("MCP_CANCELLED")
        if time.monotonic() >= self.deadline:
            raise MCPError("MCP_TIMEOUT")

    def _read(self):
        try:
            while True:
                raw = self.process.stdout.readline(65537)
                if not raw or len(raw) > 65536 or not raw.endswith(b"\n"):
                    break
                self.messages.put_nowait(raw)
        except Exception:
            pass
        finally:
            self.reader_failed.set()

    def _write(self, message):
        self._check()
        raw = json.dumps(message, allow_nan=False, separators=(",", ":")).encode() + b"\n"
        if len(raw) > 32768:
            raise MCPError("MCP_INPUT_TOO_LARGE")
        # A dedicated writer keeps a blocked pipe inside the same deadline.
        finished = threading.Event()
        failed = []

        def write():
            try:
                self.process.stdin.write(raw)
                self.process.stdin.flush()
            except Exception:
                failed.append(True)
            finally:
                finished.set()

        threading.Thread(target=write, daemon=True).start()
        while not finished.wait(0.01):
            self._check()
        if failed:
            raise MCPError()

    def call(self, method, params):
        self.sequence += 1
        self._write({"jsonrpc": "2.0", "id": self.sequence, "method": method, "params": params})
        while True:
            self._check()
            try:
                raw = self.messages.get(timeout=0.01)
                value = json.loads(raw)
                if (set(value) != {"jsonrpc", "id", "result"} or value["jsonrpc"] != "2.0"
                        or type(value["id"]) is not int or value["id"] != self.sequence
                        or not isinstance(value["result"], dict)):
                    raise ValueError()
                return value["result"]
            except queue.Empty:
                if self.reader_failed.is_set():
                    raise MCPError()
            except Exception:
                raise MCPError() from None

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait(timeout=1)
            for pipe in (self.process.stdin, self.process.stdout):
                if pipe:
                    pipe.close()
        if self.job is not None:
            self.job.Close()
            self.job = None

    def __exit__(self, *_):
        self.close()
