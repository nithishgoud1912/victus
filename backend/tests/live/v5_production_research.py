"""Real HTTP/SSE fixture admission after ordinary production bootstrap.

Requires an existing matching qualification directory for the positive campaign.
Never injects a registry, edits evidence, promotes a record or downloads an engine.
"""

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
from v3_baseline import counts, replay

from victus.workflows.qualification_records import _fixture_artifacts_match, runtime_identity


def run(output: Path, qualification_dir: Path, *, expect_unavailable: bool = False):
    root = output.absolute()
    if not qualification_dir.is_absolute() or not qualification_dir.is_dir():
        raise ValueError("An existing absolute qualification directory is required")
    root.mkdir(parents=False, exist_ok=False)
    runtime = root / "runtime"
    token = secrets.token_urlsafe(48)
    headers = {"Authorization": "Bearer " + token}
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    env = {k: v for k, v in os.environ.items() if not k.startswith("VICTUS_")}
    env.update(
        VICTUS_DATA_DIR=str(runtime),
        VICTUS_API_TOKEN=token,
        VICTUS_QUALIFICATION_DIR=str(qualification_dir),
    )
    checks = {}
    report = {
        "schema_version": 1,
        "kind": "production_fixture_probe",
        "transport": "real loopback HTTP/SSE",
        "injected_capabilities": False,
        "normal_memory_guards": True,
        "expect_unavailable": expect_unavailable,
        "runtime_sha256": runtime_identity(),
        "status": "running",
        "passed": False,
        "qualified": False,
        "checks": checks,
    }
    process = None
    try:
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
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}", timeout=20, trust_env=False
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
                        raise TimeoutError("Production service did not become ready")
                    time.sleep(0.1)
                checks["capabilities_require_auth"] = (
                    client.get("/api/workflows/capabilities").status_code == 401
                )
                capability = client.get("/api/workflows/capabilities", headers=headers).json()
                research = capability["browser_research"]
                checks["fixture_scope_only"] = research["scope"] == "fixture_only"
                body = {
                    "filename": "structured.json",
                    "source_ids": ["source-a", "source-b"],
                    "required_sources": 2,
                }
                before = counts(runtime)
                if not research["enabled"]:
                    blocked = client.post(
                        "/api/workflows/browser-research",
                        headers={**headers, "X-Client-Request-ID": "v5-blocked"},
                        json=body,
                    )
                    checks["unavailable_creates_no_work"] = (
                        blocked.status_code == 503 and counts(runtime) == before
                    )
                    checks["unavailable_reason_present"] = bool(research["reason"])
                    report["status"] = (
                        "passed" if expect_unavailable and all(checks.values()) else "blocked"
                    )
                    report["blocker"] = "MATCHING_BROWSER_QUALIFICATION_UNAVAILABLE"
                elif expect_unavailable:
                    report["status"] = "failed"
                    report["failure_type"] = "UnexpectedCapabilityAdmission"
                else:
                    checks["production_bootstrap_admitted"] = research["enabled"] is True
                    checks["catalog_exact"] = set(research["source_ids"]) == {
                        "source-a",
                        "source-b",
                        "redirect-a",
                    }

                    def terminal(task):
                        until = time.monotonic() + 60
                        while time.monotonic() < until:
                            result = client.get(f"/api/tasks/{task}", headers=headers).json()
                            if result["status"] not in {"queued", "prepared", "running"}:
                                return result
                            time.sleep(0.05)
                        raise TimeoutError("Research did not terminate")

                    for route, filename in [
                        ("structured", "structured.json"),
                        ("text", "command.json"),
                    ]:
                        request_headers = {**headers, "X-Client-Request-ID": f"v5-{route}"}
                        url = (
                            "/api/workflows/browser-research"
                            if route == "structured"
                            else "/api/commands"
                        )
                        payload = (
                            body
                            if route == "structured"
                            else {"text": f"research sources source-a, source-b into {filename}"}
                        )
                        response = client.post(url, headers=request_headers, json=payload)
                        response.raise_for_status()
                        task = response.json()["task_id"]
                        result = terminal(task)
                        artifact = runtime / "workspace" / filename
                        import hashlib
                        import importlib.metadata

                        checks[f"{route}_verified_sources"] = (
                            result["status"] == "succeeded"
                            and result["verified"] is True
                            and _fixture_artifacts_match(
                                runtime / "report.json",
                                [
                                    {
                                        "destination": filename,
                                        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                                    }
                                ],
                                importlib.metadata.version("playwright"),
                            )
                        )
                        before = counts(runtime)
                        duplicate = client.post(url, headers=request_headers, json=payload)
                        checks[f"{route}_replay_no_effect"] = (
                            duplicate.json() == response.json() and counts(runtime) == before
                        )
                        client.get(f"/api/tasks/{task}", headers=headers).raise_for_status()
                        events = replay(client, headers, task)
                        ids = [int(e["id"]) for e in events if e["event"] != "task.snapshot"]
                        checks[f"{route}_sse_read_only"] = (
                            bool(ids) and ids == sorted(set(ids)) and counts(runtime) == before
                        )
                        later = replay(client, headers, task, ids[-1])
                        checks[f"{route}_cursor_read_only"] = (
                            len(later) == 1 and counts(runtime) == before
                        )
                    before = counts(runtime)
                    invalid = client.post(
                        "/api/workflows/browser-research",
                        headers={**headers, "X-Client-Request-ID": "v5-public"},
                        json={
                            **body,
                            "filename": "public.json",
                            "source_ids": ["https://example.org"],
                        },
                    )
                    checks["public_scope_refused"] = (
                        invalid.status_code == 422 and counts(runtime) == before
                    )
                    client.post("/api/stop", headers=headers).raise_for_status()
                    stopped = client.post(
                        "/api/workflows/browser-research",
                        headers={**headers, "X-Client-Request-ID": "v5-stop"},
                        json={**body, "filename": "after-stop.json"},
                    )
                    checks["stop_no_later_effect"] = (
                        stopped.status_code == 202
                        and stopped.json()["status"] == "cancelled"
                        and not (runtime / "workspace/after-stop.json").exists()
                    )
                    report["status"] = "passed" if all(checks.values()) else "failed"
    except Exception as error:
        report.update(status="failed", failure_type=type(error).__name__)
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        report["runtime_end_sha256"] = runtime_identity()
        report["passed"] = (
            report["status"] == "passed"
            and report["runtime_sha256"] == report["runtime_end_sha256"]
        )
        (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--qualification-dir", type=Path, required=True)
    parser.add_argument("--expect-unavailable", action="store_true")
    args = parser.parse_args()
    report = run(args.output, args.qualification_dir, expect_unavailable=args.expect_unavailable)
    print(json.dumps(report))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
