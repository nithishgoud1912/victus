"""Timed mixed-use reliability check. Default is a real two-hour wall-clock run.

Short runs validate the harness and are explicitly not M7 soak qualification.
"""

import argparse
import hashlib
import json
import multiprocessing
import secrets
import socket
import threading
import time
from pathlib import Path

import httpx
import uvicorn

from victus.api.app import create_app
from victus.memory.models import MemoryInput
from victus.runtime.resources import ResourcePressure
from victus.runtime.soak_results import finalize
from victus.runtime.source_inventory import source_identity
from victus.settings import Settings
from victus.storage.backups import restore
from victus.voice.stt import TranscriptionWorker


def implementation_hash():
    root = Path(__file__).resolve().parents[2] / "victus"
    value = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        value.update(path.relative_to(root).as_posix().encode())
        value.update(path.read_bytes())
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=7200)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path)
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Record a blocked attempt if normal mutation admission lacks resources",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Abort unqualified on a failure or three pressure rejections; never shorten the passing duration gate",
    )
    args = parser.parse_args()
    if not 10 <= args.seconds <= 14400:
        parser.error("Duration must be 10 to 14400 seconds")
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    source_start = source_identity(Path(__file__).resolve().parents[3])
    if args.require_ready:
        from victus.runtime.resources import resources, system_memory

        try:
            resources().check_current()
        except ResourcePressure as error:
            report = {
                "requested_seconds": args.seconds,
                "elapsed_seconds": 0,
                "full_two_hour_soak": False,
                "qualified": False,
                "blocked": "RESOURCE_PRESSURE"
                if str(error) == "LOCAL_RESOURCE_PRESSURE"
                else "RESOURCE_TELEMETRY_UNAVAILABLE",
                "boundary": "preflight",
                "implementation_start_sha256": implementation_hash(),
                "host_memory": system_memory(),
                "normal_memory_guards": True,
                "tasks_verified": 0,
            }
            (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report))
            return 2
    token = secrets.token_urlsafe(32)
    app = create_app(Settings(root / "runtime", token))
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level="error"))
    server_thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    server_thread.start()
    closing = threading.Event()
    report = {
        "requested_seconds": args.seconds,
        "full_two_hour_soak": False,
        "qualified": False,
        "tasks_verified": 0,
        "tasks_admitted": 0,
        "pressure_rejections": 0,
        "memory_cycles": 0,
        "backup_restores": 0,
        "stt_calls": 0,
        "failures": [],
        "implementation_start_sha256": implementation_hash(),
        "source_start_sha256": source_start,
        "process_measurement_scope": "multiprocessing children only; Windows OS descendants remain separate",
    }
    durations, rss, telemetry = [], [], []
    work = None
    worker = None
    try:
        if args.model:
            worker = TranscriptionWorker(str(args.model.resolve(strict=True)))
        deadline = time.monotonic() + 15
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        if not server.started:
            raise RuntimeError("Isolated API did not start")
        services = app.state.services

        def mixed_work():
            index = 0
            with httpx.Client(
                base_url=base,
                headers={"Authorization": "Bearer " + token},
                trust_env=False,
                timeout=10,
            ) as client:
                while not closing.is_set():
                    index += 1
                    operation = "task_submit"
                    try:
                        response = client.post(
                            "/api/tasks",
                            json={
                                "tool": "fs.create_note",
                                "arguments": {
                                    "filename": f"soak-{index}.txt",
                                    "text": "isolated soak fixture",
                                },
                            },
                            headers={"X-Client-Request-ID": f"soak-{index}"},
                        )
                        if response.status_code == 503:
                            report["pressure_rejections"] += 1
                        else:
                            response.raise_for_status()
                            report["tasks_admitted"] += 1
                            operation = "task_verify"
                            task_id = response.json()["task_id"]
                            task_deadline = time.monotonic() + 20
                            while not closing.is_set() and time.monotonic() < task_deadline:
                                task = client.get(f"/api/tasks/{task_id}").json()
                                if task["status"] not in {"queued", "prepared", "running"}:
                                    break
                                closing.wait(0.05)
                            if closing.is_set():
                                return
                            if not task.get("verified"):
                                raise RuntimeError("SOAK_TASK_UNVERIFIED")
                            report["tasks_verified"] += 1
                            while services.tasks.queue.active_task_id is not None:
                                if closing.wait(0.01):
                                    return
                        operation = "memory"
                        entry = services.memory.remember(
                            MemoryInput(
                                type="preference",
                                value="tone=concise",
                                provenance="explicit_user_preference",
                                confirmation="explicit_user_review",
                            )
                        )
                        assert services.memory.get(entry.memory_id).value == "tone=concise"
                        services.memory.forget(entry.memory_id)
                        report["memory_cycles"] += 1
                        operation = "retention"
                        services.retention.cleanup()
                        if index == 1 or index % 20 == 0:
                            operation = "backup_restore"
                            archive = root / f"backup-{index}"
                            services.backups.create(archive)
                            restore(archive, root / f"restored-{index}")
                            report["backup_restores"] += 1
                        if worker and (index == 1 or index % 4 == 0):
                            try:
                                operation = "stt"
                                assert not worker.transcribe(b"\0" * 32000, closing).strip()
                                report["stt_calls"] += 1
                            except ResourcePressure:
                                report["pressure_rejections"] += 1
                    except Exception as error:
                        if not closing.is_set():
                            report["failures"].append(
                                {"operation": operation, "error_type": type(error).__name__}
                            )
                    closing.wait(min(30, args.seconds / 4))

        work = threading.Thread(target=mixed_work, name="victus-soak-mixed", daemon=True)
        work.start()
        started = time.monotonic()
        warm_after = min(120, args.seconds / 3)
        last_heartbeat = started - 60
        with httpx.Client(
            base_url=base, headers={"Authorization": "Bearer " + token}, trust_env=False, timeout=3
        ) as client:
            while time.monotonic() - started < args.seconds:
                if args.fail_fast and (report["failures"] or report["pressure_rejections"] >= 3):
                    report["abort_reason"] = (
                        "FAILURE" if report["failures"] else "PERSISTENT_RESOURCE_PRESSURE"
                    )
                    break
                tick = time.monotonic()
                try:
                    response = client.get("/api/health")
                    response.raise_for_status()
                    durations.append(time.monotonic() - tick)
                except Exception:
                    report["failures"].append("HEALTH_UNRESPONSIVE")
                sample = services.resources.snapshot()
                current_rss = sample.get("process_rss_bytes")
                if current_rss and time.monotonic() - started >= warm_after:
                    rss.append(current_rss)
                if time.monotonic() - last_heartbeat >= 60:
                    telemetry.append(
                        {
                            "elapsed_seconds": time.monotonic() - started,
                            "rss_bytes": current_rss,
                            "available_bytes": sample.get("available_bytes"),
                            "vram": sample.get("vram"),
                        }
                    )
                    report["elapsed_seconds"] = time.monotonic() - started
                    (root / "progress.json").write_text(
                        json.dumps(report, indent=2), encoding="utf-8"
                    )
                    last_heartbeat = time.monotonic()
                closing.wait(0.5)
        report["elapsed_seconds"] = time.monotonic() - started
        closing.set()
        work.join(timeout=12)
        if work.is_alive():
            report["failures"].append("MIXED_WORK_SHUTDOWN_TIMEOUT")
        ordered = sorted(durations)
        report["health_requests"] = len(durations)
        report["health_p95_seconds"] = (
            ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))] if ordered else None
        )
        report["health_max_seconds"] = max(durations, default=None)
        report["rss_growth_from_warmed_baseline"] = (max(rss) / rss[0] - 1) if rss else None
        report["telemetry"] = telemetry
        report["implementation_end_sha256"] = implementation_hash()
        report["full_two_hour_soak"] = report["elapsed_seconds"] >= 7200
    except Exception as error:
        report["failures"].append({"operation": "harness", "error_type": type(error).__name__})
    finally:
        closing.set()
        if work is not None:
            work.join(timeout=12)
        if worker:
            try:
                worker.close()
            except Exception:
                report["failures"].append("STT_CLEANUP_FAILED")
        server.should_exit = True
        server_thread.join(timeout=15)
        report["server_shutdown_complete"] = not server_thread.is_alive()
        report["work_shutdown_complete"] = work is None or not work.is_alive()
        report["remaining_multiprocessing_children"] = sum(
            child.is_alive() for child in multiprocessing.active_children()
        )
        sock.close()
        try:
            report["source_end_sha256"] = source_identity(Path(__file__).resolve().parents[3])
        except Exception:
            report["failures"].append("SOURCE_END_INVENTORY_UNAVAILABLE")
        finalize(report)
        (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "telemetry"}))
    return 0 if report["qualified"] or report["smoke_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
