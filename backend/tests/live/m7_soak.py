"""Timed mixed-use reliability check. Default is a real two-hour wall-clock run.

Short runs validate the harness and are explicitly not M7 soak qualification.
"""

import argparse
import hashlib
import json
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
    args = parser.parse_args()
    if not 10 <= args.seconds <= 14400:
        parser.error("Duration must be 10 to 14400 seconds")
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
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
        "pressure_rejections": 0,
        "memory_cycles": 0,
        "backup_restores": 0,
        "stt_calls": 0,
        "failures": [],
        "implementation_start_sha256": implementation_hash(),
    }
    durations, rss, telemetry = [], [], []
    worker = TranscriptionWorker(str(args.model.resolve(strict=True))) if args.model else None
    try:
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
        report["qualified"] = bool(
            report["full_two_hour_soak"]
            and not report["failures"]
            and report["tasks_verified"] >= 100
            and report["backup_restores"] >= 2
            and report["rss_growth_from_warmed_baseline"] is not None
            and report["rss_growth_from_warmed_baseline"] <= 0.20
            and report["health_p95_seconds"] < 0.5
            and report["implementation_start_sha256"] == report["implementation_end_sha256"]
        )
    finally:
        closing.set()
        if worker:
            worker.close()
        server.should_exit = True
        server_thread.join(timeout=15)
        sock.close()
        (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "telemetry"}))


if __name__ == "__main__":
    main()
