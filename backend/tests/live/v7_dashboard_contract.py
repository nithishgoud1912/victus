"""Real browser / simulated HTTP: V7 readiness, research identity and unknown guidance."""

import argparse
import json
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit

from browser_support import creation_flags, launch_browser, node_executable
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    out = parser.parse_args().output.absolute()
    out.mkdir(parents=True, exist_ok=False)
    server = subprocess.Popen(
        [
            node_executable(ROOT),
            "node_modules/vite/bin/vite.js",
            "--host",
            "127.0.0.1",
            "--port",
            "5183",
            "--strictPort",
        ],
        cwd=ROOT / "dashboard",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags(),
    )
    state = {"blocked": False, "enabled": True, "submitted": False, "stopped": False}
    submissions, mutations, errors, checks = [], [], [], {}
    task = {
        "task_id": "research-task",
        "status": "unknown",
        "verified": False,
        "tool": "workflow.browser_research",
        "error_code": "WORKER_INTERRUPTED",
    }

    def route(r):
        path = urlsplit(r.request.url).path
        headers = {"Access-Control-Allow-Origin": "http://127.0.0.1:5183"}
        if r.request.method == "OPTIONS":
            r.fulfill(
                status=204,
                headers={
                    **headers,
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "*",
                },
            )
            return
        if r.request.method == "POST":
            mutations.append(path)
        if path == "/api/session":
            body = {"authenticated": True, "expires_at": None}
        elif path == "/api/health":
            body = {
                "status": "ok",
                "mode": "fixture",
                "stopped": state["stopped"],
                "tools": ["fs.create_note"],
                "emergency_hotkey": "disabled",
            }
        elif path == "/api/workflows/capabilities":
            body = {
                "notepad_checklist": {
                    "enabled": False,
                    "profiles": [],
                    "reason": "Native qualification pending",
                },
                "browser_research": {
                    "enabled": state["enabled"],
                    "scope": "fixture_only",
                    "source_ids": ["source-a", "source-b", "redirect-a"],
                    "reason": None
                    if state["enabled"]
                    else '<img data-v7-injected="true" onerror="alert(1)"> qualification pending',
                },
                "commands": {
                    "deterministic": ["note"],
                    "model_name": "fixture:4b",
                    "model_digest": "sha256:" + "a" * 64,
                    "reasoning_ready": True,
                    "reason": None,
                },
                "stopped": state["stopped"],
                "resource_blocked": state["blocked"],
                "resource_reason": "LOCAL_DISK_PRESSURE" if state["blocked"] else None,
            }
        elif path == "/api/memory":
            body = []
        elif path == "/api/integrations":
            body = {"cloud": "disabled", "cloud_pin": None, "upstream": None, "mcp_notes": False}
        elif path == "/api/voice":
            body = {"enabled": False, "state": "idle", "revision": 0}
        elif path == "/api/workflows/browser-research":
            submissions.append(
                {"id": r.request.headers["x-client-request-id"], "body": r.request.post_data_json}
            )
            if len(submissions) == 1:
                r.abort()
                return
            state["submitted"] = True
            r.fulfill(
                status=202,
                headers=headers,
                content_type="application/json",
                body=json.dumps({"task_id": task["task_id"], "status": "queued"}),
            )
            return
        elif path == "/api/tasks/research-task":
            body = task
        elif path == "/api/events":
            frame = ": ping\n\n"
            if state["submitted"]:
                frame = (
                    "id: 1\nevent: task.snapshot\ndata: "
                    + json.dumps(
                        {
                            "event_id": 1,
                            "task_id": task["task_id"],
                            "event_type": "task.snapshot",
                            "timestamp": "fixture",
                            "safe_payload": task,
                        }
                    )
                    + "\n\n"
                )
            r.fulfill(status=200, headers=headers, content_type="text/event-stream", body=frame)
            return
        elif path == "/api/stop":
            state["stopped"] = True
            body = {"stopped": True, "reset": "restart_required"}
        else:
            raise AssertionError(path)
        r.fulfill(
            status=200, headers=headers, content_type="application/json", body=json.dumps(body)
        )

    try:
        with sync_playwright() as pw:
            browser = launch_browser(pw, headless=True)
            page = browser.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
            page.set_default_timeout(12000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("http://127.0.0.1:8765/**", route)
            for _ in range(50):
                try:
                    page.goto("http://127.0.0.1:5183/")
                    break
                except Exception:
                    time.sleep(0.1)
            readiness = page.get_by_role("region", name="Dependency readiness", exact=True)
            expect(readiness).to_contain_text("Qualified and enabled")
            expect(readiness).to_contain_text("Pinned local model available: fixture:4b")
            expect(readiness).to_contain_text("Inference quality is not qualified")
            checks["actual_browser_model_readiness_and_quality_boundary"] = True
            form = page.get_by_role("region", name="Bundled browser research", exact=True)
            form.get_by_label("New report filename").fill("../escape.json")
            form.get_by_label("source-a", exact=True).check()
            form.get_by_label("source-b", exact=True).check()
            form.get_by_role("button", name="Create research report", exact=True).click()
            expect(form.get_by_role("alert")).to_contain_text("new .json basename")
            checks["invalid_destination_creates_no_request"] = not submissions
            form.get_by_label("New report filename").fill("sources.json")
            form.get_by_role("button", name="Create research report", exact=True).evaluate(
                "b=>{b.click();b.click()}"
            )
            expect(
                form.get_by_role("button", name="Retry same research", exact=True)
            ).to_be_visible()
            expect(form.get_by_label("New report filename")).to_be_disabled()
            expect(form.get_by_label("source-a", exact=True)).to_be_disabled()
            form.get_by_role("button", name="Retry same research", exact=True).click()
            expect(page.get_by_role("heading", name="Task: unknown", exact=True)).to_be_visible()
            expect(page.get_by_role("region", name="Task result")).to_contain_text(
                "without repeating the action"
            )
            checks["uncertain_and_double_click_reuse_exact_identity"] = (
                len(submissions) == 2
                and submissions[0] == submissions[1]
                and submissions[0]["body"]
                == {
                    "filename": "sources.json",
                    "source_ids": ["source-a", "source-b"],
                    "required_sources": 2,
                }
            )
            checks["unknown_guidance_has_no_effect_retry"] = (
                page.get_by_role("region", name="Task result").get_by_role("button").count() == 0
            )
            before = list(mutations)
            state["blocked"] = True
            page.reload()
            expect(readiness).to_contain_text(
                "Qualified; Temporarily blocked by low workspace disk space"
            )
            expect(
                form.get_by_role("button", name="Create research report", exact=True)
            ).to_be_disabled()
            expect(page.get_by_role("heading", name="Task: unknown", exact=True)).to_be_visible()
            checks["resource_pressure_separate_from_qualification"] = True
            checks["refresh_and_replay_do_not_mutate"] = mutations == before
            state["blocked"] = False
            state["enabled"] = False
            page.reload()
            expect(readiness).to_contain_text("qualification pending")
            checks["capability_reason_is_literal_text"] = (
                page.locator("img[data-v7-injected]").count() == 0
            )
            checks["mobile_has_no_horizontal_overflow"] = page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth"
            )
            stop = page.get_by_role("button", name="Stop all work", exact=True)
            stop.focus()
            page.keyboard.press("Enter")
            expect(page.get_by_role("button", name="Submit command", exact=True)).to_be_disabled()
            checks["keyboard_stop"] = mutations.count("/api/stop") == 1
            checks["no_page_errors"] = not errors
            browser.close()
        report = {
            "fixture_only": True,
            "hardware_qualified": False,
            "checks": checks,
            "passed": bool(checks) and all(checks.values()),
        }
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))
        if not report["passed"]:
            raise SystemExit(1)
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__ == "__main__":
    main()
