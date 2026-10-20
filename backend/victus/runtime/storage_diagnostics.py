"""Explicit finite storage probe in a new isolated root; never release evidence."""

from __future__ import annotations

import json
import multiprocessing
import os
import platform
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

from victus.storage.checkpoints import CheckpointStore
from victus.storage.paths import safe_path

_CRASH_EXIT = 73


def _commit_then_exit(root: str, sequence: int) -> None:
    store = CheckpointStore(Path(root))
    store.claim("storage-probe", sequence, "diagnostic")
    store.complete("storage-probe", sequence, {"sequence": sequence})
    os._exit(_CRASH_EXIT)


def _filesystem(path: Path) -> dict:
    result = {"disk_free_bytes": shutil.disk_usage(path).free}
    if hasattr(os, "statvfs"):
        sample = os.statvfs(path)
        result["free_inodes"] = sample.f_favail
    # Mount names and host paths are deliberately excluded from the report.
    try:
        mounts = []
        for line in Path("/proc/self/mountinfo").read_text().splitlines():
            before, after = line.split(" - ", 1)
            mount = Path(before.split()[4].replace("\\040", " "))
            if path.is_relative_to(mount):
                mounts.append((len(mount.parts), after.split()[0]))
        if mounts:
            result["filesystem_type"] = max(mounts)[1]
    except (OSError, ValueError, IndexError):
        pass
    return result


def probe(output: Path, *, repetitions: int = 3, timeout: float = 15) -> dict:
    """Commit a claimed node, kill its process, then read it without replaying it."""
    if type(repetitions) is not int or not 1 <= repetitions <= 20:
        raise ValueError("One to twenty diagnostic repetitions required")
    if type(timeout) not in {int, float} or not 0 < timeout <= 60:
        raise ValueError("A finite diagnostic timeout is required")
    output = output.absolute()
    safe_path(output.parent, output.name)
    for parent in output.parents:
        if parent.is_symlink() or getattr(parent.stat(), "st_file_attributes", 0) & 0x400:
            raise ValueError("Linked diagnostic output rejected")
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    from victus.workflows.qualification_records import runtime_identity

    report = {
        "schema_version": 1,
        "kind": "storage_diagnostic",
        "qualified": False,
        "status": "running",
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
        "platform": platform.system(),
        "filesystem": _filesystem(output),
        "requested": repetitions,
        "runtime_sha256": runtime_identity(),
        "cases": [],
    }

    def persist():
        temporary = output / "report.pending.json"
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(json.dumps(report, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(output / "report.json")

    persist()
    try:
        for sequence in range(repetitions):
            root = output / f"case-{sequence + 1:02}"
            root.mkdir(mode=0o700)
            case = {"sequence": sequence, "passed": False}
            process = multiprocessing.get_context("spawn").Process(
                target=_commit_then_exit, args=(str(root), sequence)
            )
            try:
                process.start()
                process.join(timeout)
                if process.is_alive():
                    case["error_code"] = "DIAGNOSTIC_CHILD_TIMEOUT"
                    process.terminate()
                    process.join(2)
                    if process.is_alive():
                        process.kill()
                        process.join(2)
                case["exit_code"] = process.exitcode
                if process.exitcode != _CRASH_EXIT:
                    case.setdefault("error_code", "DIAGNOSTIC_CHILD_FAILED")
                else:
                    # Reopening must consume the committed result, never execute it again.
                    store = CheckpointStore(root)
                    claim, result = store.claim("storage-probe", sequence, "diagnostic")
                    with closing(sqlite3.connect(store.path)) as db:
                        integrity = db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
                        full = db.execute("PRAGMA synchronous").fetchone()[0] == 2
                        wal = db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
                    case.update(integrity_ok=integrity, full_durability=full, wal=wal)
                    case["passed"] = (
                        claim == "complete"
                        and result == {"sequence": sequence}
                        and integrity
                        and full
                        and wal
                    )
            except (OSError, sqlite3.Error, RuntimeError, ValueError) as error:
                case["error_code"] = type(error).__name__
                if isinstance(error, sqlite3.Error):
                    case["sqlite_errorcode"] = getattr(error, "sqlite_errorcode", None)
                    case["sqlite_errorname"] = getattr(error, "sqlite_errorname", None)
            finally:
                if process.pid is not None and process.is_alive():
                    process.kill()
                    process.join(2)
                if process.pid is None or not process.is_alive():
                    process.close()
            report["cases"].append(case)
            persist()
            if not case["passed"]:
                break
        report["status"] = (
            "passed"
            if len(report["cases"]) == repetitions and all(c["passed"] for c in report["cases"])
            else "failed"
        )
        return report
    finally:
        if report["status"] == "running":
            report["status"] = "interrupted"
        report["runtime_end_sha256"] = runtime_identity()
        persist()
