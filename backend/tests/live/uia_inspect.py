"""Explicit process-scoped inspection; never guesses a window or sends input."""

import argparse
import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path

from victus.adapters.uia.applications import UIABlocked
from victus.adapters.uia.native import WindowsBackend


def describe(control):
    info = control.element_info
    return {
        "control_type": info.control_type,
        "automation_id": info.automation_id,
        "name": info.name,
        "class_name": info.class_name,
        "process_id": info.process_id,
        "runtime_id": list(info.runtime_id),
        "visible": control.is_visible(),
        "enabled": control.is_enabled(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--pid", type=int)
    target.add_argument("--launch-executable", type=Path)
    parser.add_argument("--argument", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Inspection output must be a new private file")
    backend = WindowsBackend()
    backend.initialize()
    report = {"inspection_only": True, "input_sent": False}
    try:
        process = None
        if args.launch_executable:
            executable = args.launch_executable
            if not executable.is_absolute() or not executable.is_file() or executable.is_symlink():
                raise UIABlocked("EXECUTABLE_UNAVAILABLE")
            report["executable_sha256"] = hashlib.sha256(executable.read_bytes()).hexdigest()
            process = backend.launch(executable, args.argument)
            args.pid = process.pid
        identity = backend.identity(args.pid)
        report["identity"] = asdict(identity)
        if args.launch_executable and Path(identity.executable) != args.launch_executable:
            raise UIABlocked("PROCESS_IMAGE_MISMATCH")
        connection = backend.connect(identity.pid)
        deadline = time.monotonic() + 5
        windows = []
        while time.monotonic() < deadline:
            if process is not None and process.poll() is not None:
                raise UIABlocked("LAUNCH_EXITED_HANDOFF_NOT_OWNED")
            windows = connection.windows()
            if windows:
                break
            time.sleep(0.05)
        if not windows:
            raise UIABlocked("OWNED_WINDOW_UNAVAILABLE")
        report["windows"] = [
            {
                "root": describe(window),
                "controls": [describe(c) for c in window.descendants()][:256],
            }
            for window in windows
        ]
        report["status"] = "inspected"
    except UIABlocked as error:
        report.update(status="blocked", error_code=str(error))
    except Exception:
        report.update(status="blocked", error_code="NATIVE_INSPECTION_UNAVAILABLE")
    finally:
        backend.uninitialize()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "error_code") if key in report}))


if __name__ == "__main__":
    main()
