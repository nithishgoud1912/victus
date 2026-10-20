"""Explicit loopback source smoke test with real pressure guards and fresh data."""

import argparse
import hashlib
import json
import os
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import httpx


def counts(root):
    with sqlite3.connect(f"{(root / 'victus.sqlite3').as_uri()}?mode=ro", uri=True) as db:
        return tuple(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("tasks", "action_attempts", "task_events", "command_intakes")
        )


def replay(client, headers, task_id, cursor=0):
    events = []
    with client.stream(
        "GET",
        "/api/events",
        headers={**headers, "Last-Event-ID": str(cursor)},
        params={"task_id": task_id},
    ) as response:
        response.raise_for_status()
        frame = []
        for line in response.iter_lines():
            if line:
                frame.append(line)
                continue
            if frame:
                event = dict(part.split(": ", 1) for part in frame if ": " in part)
                events.append(event)
                if event.get("event") == "task.snapshot":
                    return events
                frame = []
    raise RuntimeError("Event snapshot not delivered")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.data_dir.resolve()
    root.mkdir(parents=True, exist_ok=False)
    token = secrets.token_urlsafe(48)
    headers = {"Authorization": "Bearer " + token}
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    env = {key: value for key, value in os.environ.items() if not key.startswith("VICTUS_")}
    env.update(VICTUS_DATA_DIR=str(root), VICTUS_API_TOKEN=token)
    checks = {}
    report = {
        "transport": "real loopback HTTP/SSE",
        "physical_ui_test": False,
        "memory_safeguard_enabled": True,
        "selected_user_runtime": None,
        "checks": checks,
    }
    from victus.runtime.resources import system_memory

    report["available_memory_bytes"] = system_memory().get("available_bytes")
    with (root / "server.log").open("x", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "victus.api.app:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "error",
            ],
            env=env,
            stdout=log,
            stderr=log,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}", timeout=15, trust_env=False
            ) as client:
                deadline = time.monotonic() + 25
                while True:
                    try:
                        health = client.get("/api/health", headers=headers)
                        if health.status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError("Source server did not become ready")
                    time.sleep(0.1)
                checks["health_authenticated"] = "fs.create_note" in health.json()["tools"] and set(
                    health.json()["tools"]
                ) <= {"fs.create_note", "workflow.browser_research"}
                checks["health_requires_auth"] = client.get("/api/health").status_code == 401
                checks["events_require_auth"] = client.get("/api/events").status_code == 401
                before = counts(root)
                rejected = client.post(
                    "/api/workflows/notepad-checklist",
                    headers=headers,
                    json={
                        "profile": "notepad-win11-11.2607.14.0",
                        "items": ["Inspect"],
                        "filename": "native.txt",
                    },
                )
                checks["native_gated_before_admission"] = (
                    rejected.status_code == 503 and counts(root) == before
                )
                content = "VICTUS V3.0 isolated baseline"
                body = {
                    "tool": "fs.create_note",
                    "arguments": {"filename": "baseline.txt", "text": content},
                }
                request_headers = {**headers, "X-Client-Request-ID": "v30-note"}
                admitted = client.post("/api/tasks", headers=request_headers, json=body)
                checks["note_admitted"] = admitted.status_code == 202
                if admitted.status_code != 202:
                    report["admission_status"] = admitted.status_code
                    raise RuntimeError("Note blocked; inspect resource/admission evidence")
                task_id = admitted.json()["task_id"]
                deadline = time.monotonic() + 25
                while True:
                    result = client.get(f"/api/tasks/{task_id}", headers=headers).json()
                    if result["status"] not in {"queued", "prepared", "running"}:
                        break
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Note did not reach terminal state")
                    time.sleep(0.05)
                target = root / "workspace/baseline.txt"
                checks["note_verified_exact_bytes"] = (
                    result["status"] == "succeeded"
                    and result["verified"]
                    and target.read_bytes() == content.encode()
                )
                report["note_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
                before = counts(root)
                duplicate = client.post("/api/tasks", headers=request_headers, json=body)
                checks["duplicate_same_task_no_effect"] = (
                    duplicate.status_code == 202
                    and duplicate.json()["task_id"] == task_id
                    and counts(root) == before
                )
                checks["snapshot_requires_auth"] = (
                    client.get(f"/api/tasks/{task_id}").status_code == 401
                )
                checks["snapshot_read_only"] = (
                    client.get(f"/api/tasks/{task_id}", headers=headers).json() == result
                    and counts(root) == before
                )
                events = replay(client, headers, task_id)
                ids = [int(event["id"]) for event in events if event["event"] != "task.snapshot"]
                checks["ordered_event_replay"] = bool(ids) and ids == sorted(set(ids))
                checks["event_snapshot_read_only"] = (
                    events[-1]["event"] == "task.snapshot" and counts(root) == before
                )
                resumed = replay(client, headers, task_id, ids[-1])
                checks["cursor_reconnect_no_resubmission"] = (
                    len(resumed) == 1
                    and resumed[0]["event"] == "task.snapshot"
                    and counts(root) == before
                )

                def wait_command(task_id):
                    deadline = time.monotonic() + 35
                    while time.monotonic() < deadline:
                        result = client.get(f"/api/tasks/{task_id}", headers=headers).json()
                        if result["status"] not in {"queued", "prepared", "running"}:
                            return result
                        time.sleep(0.05)
                    raise TimeoutError("Command terminal result unavailable")

                command_headers = {**headers, "X-Client-Request-ID": "v40-command"}
                checks["command_requires_auth"] = (
                    client.post("/api/commands", json={"text": "Create a note"}).status_code == 401
                )
                command = client.post(
                    "/api/commands",
                    headers=command_headers,
                    json={"text": 'Create a note command.txt containing "Exact command bytes"'},
                )
                checks["command_admitted"] = (
                    command.status_code == 200 and command.json()["state"] == "submitted"
                )
                if not checks["command_admitted"]:
                    report["command_admission_status"] = command.status_code
                    raise RuntimeError("Command blocked; no retry with a new identity")
                task_id = command.json()["task_id"]
                result = wait_command(task_id)
                checks["command_graph_verified_exact_bytes"] = (
                    result["status"] == "succeeded"
                    and result["verified"]
                    and (root / "workspace/command.txt").read_bytes() == b"Exact command bytes"
                    and (root / "agent/checkpoints.sqlite3").is_file()
                )
                before = counts(root)
                checks["command_replay_no_effect"] = (
                    client.post(
                        "/api/commands",
                        headers=command_headers,
                        json={"text": "different uncertain retry"},
                    ).json()
                    == command.json()
                    and counts(root) == before
                )
                clarification = client.post(
                    "/api/commands",
                    headers={**headers, "X-Client-Request-ID": "v40-clarification"},
                    json={"text": "Create a note"},
                ).json()
                checks["missing_values_no_task"] = (
                    clarification["state"] == "clarification"
                    and set(clarification["missing"]) == {"filename", "content"}
                    and counts(root)[:3] == before[:3]
                )
                before = counts(root)
                endpoint = "/api/commands/" + clarification["command_id"]
                checks["clarification_snapshot_read_only"] = (
                    client.get(endpoint, headers=headers).json() == clarification
                    and counts(root) == before
                )
                completed = client.post(
                    endpoint + "/clarify",
                    headers=headers,
                    json={"filename": "clarified.txt", "content": "Confirmed literal content"},
                )
                result = wait_command(completed.json()["task_id"])
                checks["clarification_verified_exact_bytes"] = (
                    result["status"] == "succeeded"
                    and result["verified"]
                    and (root / "workspace/clarified.txt").read_bytes()
                    == b"Confirmed literal content"
                )
                before = counts(root)
                checks["clarification_replay_original_identity"] = (
                    client.post(
                        endpoint + "/clarify",
                        headers=headers,
                        json={"filename": "changed.txt", "content": "changed"},
                    ).json()
                    == completed.json()
                    and counts(root) == before
                    and not (root / "workspace/changed.txt").exists()
                )
                checks["stop_latched"] = client.post("/api/stop", headers=headers).json()["stopped"]
                stopped_command = client.post(
                    "/api/commands",
                    headers={**headers, "X-Client-Request-ID": "v40-stopped-command"},
                    json={"text": 'Create a note stopped-command.txt containing "blocked"'},
                )
                checks["stop_blocks_command_effect"] = (
                    stopped_command.status_code == 200
                    and stopped_command.json()["state"] == "stopped"
                    and not (root / "workspace/stopped-command.txt").exists()
                )
                after = client.post(
                    "/api/tasks",
                    headers={**headers, "X-Client-Request-ID": "v30-stopped"},
                    json={
                        "tool": "fs.create_note",
                        "arguments": {"filename": "after-stop.txt", "text": "must not be written"},
                    },
                )
                checks["stop_blocks_later_effect"] = (
                    after.status_code == 202
                    and after.json()["status"] == "cancelled"
                    and not (root / "workspace/after-stop.txt").exists()
                )
        except Exception as error:
            report["failure_type"] = type(error).__name__  # No payload-bearing exception text.
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    report["baseline_version"] = 2
    report["expected_checks"] = 23
    report["passed"] = len(checks) == 23 and all(checks.values()) and "failure_type" not in report
    (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
