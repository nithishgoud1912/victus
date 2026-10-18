"""Real Chromium plus authenticated source API; bundled fixtures only."""

import hashlib
import importlib.metadata
import json
import os
import secrets
import time
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

from victus.api.app import create_app
from victus.runtime.resources import system_memory
from victus.settings import Settings
from victus.workflows.fixture_research import FIXTURE_HASH, FixtureSite, ResearchExecutor
from victus.workflows.qualification_records import BROWSER_CHECKS, runtime_identity


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--repetitions", type=int, choices=range(1, 21), default=20)
    args = parser.parse_args(argv)
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    source_before = runtime_identity()
    with sync_playwright() as pw:
        executable = Path(pw.chromium.executable_path)
    token = secrets.token_urlsafe(48)
    headers = {"Authorization": "Bearer " + token}
    site = FixtureSite()
    checks = {}
    runs = []
    memory = []
    failure = None
    phase = "startup"
    try:
        with TestClient(
            create_app(Settings(data_dir=root, api_token=token)), base_url="http://127.0.0.1"
        ) as client:
            tasks = client.app.state.services.tasks
            executor = ResearchExecutor(site.origin, str(executable))
            tasks.research = executor
            if executor.spec().name not in tasks.registry.names():
                tasks.registry.register(executor.spec())

            def submit(filename, ids, required, key):
                return client.post(
                    "/api/workflows/browser-research",
                    headers={**headers, "X-Client-Request-ID": key},
                    json={"filename": filename, "source_ids": ids, "required_sources": required},
                )

            def wait(task_id):
                end = time.monotonic() + 80
                while time.monotonic() < end:
                    result = client.get("/api/tasks/" + task_id, headers=headers).json()
                    if result["status"] not in {
                        "queued",
                        "prepared",
                        "running",
                        "waiting_for_review",
                    }:
                        return result
                    time.sleep(0.05)
                raise TimeoutError("Fixture qualification deadline")

            def process_inventory():
                if os.name != "nt":
                    raise RuntimeError("Process cleanup probe requires Windows")
                from victus.adapters.uia.native import WindowsBackend

                backend = WindowsBackend()
                backend.initialize()
                try:
                    import playwright

                    driver = Path(playwright.__file__).parent / "driver/node.exe"
                    binaries = [executable, driver]
                    return {
                        (x["owned_pid"], x["process_created"])
                        for binary in binaries
                        for x in backend.launch_observations(binary)
                        if "process_created" in x
                    }
                finally:
                    backend.uninitialize()

            initial_processes = process_inventory()
            cleanup_verified = True
            exact_verified = True
            replay_verified = True
            for index in range(args.repetitions):
                filename = "sources.json" if index == 0 else f"sources-{index + 1:02}.json"
                ids = ["source-a" if index % 2 == 0 else "redirect-a", "source-b"]
                request_id = f"fixture-run-{index + 1}"
                phase = "admission_" + filename
                from victus.runtime.resources import ResourcePressure, resources

                ready_deadline = time.monotonic() + 30
                while True:
                    try:
                        resources().check_current()
                        break
                    except ResourcePressure:
                        if time.monotonic() >= ready_deadline:
                            failure = "RESOURCE_PRESSURE"
                            raise
                        time.sleep(0.25)
                if index % 2 == 0:
                    response = submit(filename, ids, 2, request_id)
                    admitted = response.status_code == 202
                    task_id = response.json().get("task_id")
                else:
                    response = client.post(
                        "/api/commands",
                        headers={**headers, "X-Client-Request-ID": request_id},
                        json={"text": f"research sources {', '.join(ids)} into {filename}"},
                    )
                    admitted = (
                        response.status_code == 200 and response.json().get("state") == "submitted"
                    )
                    task_id = response.json().get("task_id")
                if not admitted:
                    failure = (
                        "RESOURCE_PRESSURE"
                        if response.status_code == 503 and "pressure" in response.text
                        else "ADMISSION_REFUSED"
                    )
                    raise RuntimeError(failure)
                phase = "worker_" + filename
                result = wait(task_id)
                verified = result["status"] == "succeeded" and result["verified"]
                if not verified:
                    failure = result["error_code"]
                    raise RuntimeError("Verified browser result required")
                artifact = root / "workspace" / filename
                report = json.loads(artifact.read_text())
                exact = report["observed_count"] == 2 and all(
                    hashlib.sha256(s["text"].encode()).hexdigest() == s["text_sha256"]
                    for s in report["sources"]
                )
                if index % 2 == 0:
                    replay = (
                        submit(filename, ids, 2, request_id).json()["task_id"] == result["task_id"]
                    )
                else:
                    replay = (
                        client.post(
                            "/api/commands",
                            headers={**headers, "X-Client-Request-ID": request_id},
                            json={"text": "changed retry must preserve identity"},
                        ).json()["task_id"]
                        == result["task_id"]
                    )
                deadline = time.monotonic() + 3
                while process_inventory() - initial_processes and time.monotonic() < deadline:
                    time.sleep(0.05)
                cleanup = not (process_inventory() - initial_processes)
                cleanup_verified = cleanup_verified and cleanup
                exact_verified = exact_verified and exact
                replay_verified = replay_verified and replay
                runs.append(
                    {
                        "destination": filename,
                        "verified": bool(verified and exact),
                        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                        "replay": replay,
                        "owned_cleanup": cleanup,
                        "route": "structured" if index % 2 == 0 else "text",
                    }
                )
                memory.append(system_memory())
                print(
                    f"Fixture {index + 1}/{args.repetitions}: verified={verified and exact}, cleanup={cleanup}",
                    flush=True,
                )
            checks.update(
                exact_sources=exact_verified,
                replay=replay_verified,
                owned_cleanup=cleanup_verified,
                structured_route=bool(runs),
                text_route=any(r["route"] == "text" for r in runs),
            )
            response = submit("aliases.json", ["source-a", "redirect-a"], 2, "aliases")
            result = wait(response.json()["task_id"])
            checks["redirect_aliases"] = not result["verified"] and result["status"] != "succeeded"
            checks["destination_conflict"] = (
                submit("sources.json", ["source-b"], 1, "conflict").status_code == 422
            )
            bad = client.post(
                "/api/workflows/browser-research",
                headers=headers,
                json={
                    "filename": "bad.json",
                    "source_ids": ["http://169.254.169.254/"],
                    "required_sources": 1,
                },
            )
            checks["scope_rejection"] = bad.status_code == 422
            phase = "missing_binary"
            tasks.research = replace(executor, browser_executable=str(root / "absent-browser.exe"))
            missing = submit("missing.json", ["source-a"], 1, "missing")
            checks["missing_binary"] = (
                missing.status_code == 503 and not (root / "workspace/missing.json").exists()
            )
            tasks.research = executor
            import asyncio

            from victus.adapters.playwright.session import BrowserSession

            async def timeout_probe():
                session = BrowserSession(browser_executable=executable, timeout_ms=1)
                try:
                    await session.start()
                    return False
                except Exception:
                    return True
                finally:
                    await session.close()

            checks["timeout"] = asyncio.run(timeout_probe())
            phase = "interrupted_worker"
            interrupted = submit("interrupted.json", ["source-a", "source-b"], 2, "interrupted")
            if interrupted.status_code != 202:
                raise RuntimeError("Interrupted worker admission refused")
            deadline = time.monotonic() + 5
            while tasks.queue.supervisor.active_pid is None and time.monotonic() < deadline:
                time.sleep(0.005)
            active = tasks.queue.supervisor.active_pid is not None
            client.post("/api/stop", headers=headers)
            interrupted_result = wait(interrupted.json()["task_id"])
            checks["interrupted_worker"] = (
                active
                and interrupted_result["status"] != "succeeded"
                and not interrupted_result["verified"]
            )
            stopped = submit("stopped.json", ["source-a"], 1, "stopped")
            time.sleep(0.3)
            checks["stop_no_later_effect"] = (
                stopped.status_code == 202
                and not (root / "workspace/stopped.json").exists()
                and tasks.queue.supervisor.active_pid is None
                and not (process_inventory() - initial_processes)
            )
    except Exception as error:
        failure = failure or type(error).__name__
    finally:
        site.close()
    report = {
        "schema_version": 1,
        "kind": "fixture",
        "runtime_sha256": source_before,
        "runtime_end_sha256": runtime_identity(),
        "requested_runs": args.repetitions,
        "verified_runs": sum(run["verified"] for run in runs),
        "runs": runs,
        "memory_samples": memory,
        "fixture_only": True,
        "real_browser_requested": True,
        "normal_memory_guards": True,
        "checks": checks,
        "passed": bool(checks)
        and all(checks.values())
        and failure is None
        and source_before == runtime_identity(),
        "failure": failure,
        "boundary": phase if failure else None,
        "host_memory": system_memory(),
        "playwright_version": importlib.metadata.version("playwright"),
        "fixture_sha256": FIXTURE_HASH,
        "browser_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "browser_relative_path": "/".join(executable.parts[-3:]),
    }
    report["qualified"] = (
        report["passed"]
        and report["verified_runs"] >= 20
        and all(checks.get(key) is True for key in BROWSER_CHECKS)
    )
    root.mkdir(parents=True, exist_ok=True)
    (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"runs", "memory_samples"}}))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
