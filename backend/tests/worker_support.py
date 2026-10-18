"""Import-light spawned adapters; do not import pytest/FastAPI in effect workers."""

import os
import time

from victus.adapters.filesystem.operations import create_note


def blocking_effect(workspace, arguments):
    output = create_note(workspace, arguments)
    time.sleep(60)
    return output


def partial_write_effect(workspace, arguments):
    with (workspace / "write-attempts.txt").open("a", encoding="utf-8") as attempts:
        attempts.write("attempt\n")
        attempts.flush()
        os.fsync(attempts.fileno())
    output = workspace / arguments.filename
    with output.open("xb") as stream:
        stream.write(b"partial")
        stream.flush()
        os.fsync(stream.fileno())
        time.sleep(60)
        stream.write(b"-completed")
    return output


def crashing_effect(workspace, arguments):
    create_note(workspace, arguments)
    os._exit(7)


def error_with_private_text(workspace, arguments):
    raise RuntimeError("private payload should never appear in events")


def cooperative_effect(workspace, arguments, cancelled):
    output = create_note(workspace, arguments)
    if cancelled.wait(timeout=30):
        (workspace / "cooperated.txt").write_text("signal received", encoding="utf-8")
    return output


def gated_effect(workspace, arguments):
    (workspace / f"{arguments.filename}.started").write_text("started", encoding="utf-8")
    if arguments.filename == "first.txt":
        deadline = time.monotonic() + 10
        while not (workspace / "release.txt").exists():
            if time.monotonic() >= deadline:
                raise TimeoutError("Fixture gate deadline")
            time.sleep(0.01)
    return create_note(workspace, arguments)
