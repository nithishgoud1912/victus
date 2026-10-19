"""Browser contract fixtures only; no native UIA qualification is claimed."""

import argparse
import json
import subprocess
import time
from pathlib import Path

from browser_support import creation_flags, launch_browser, node_executable
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / ".local/v33-browser-03"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    out = parser.parse_args().output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    node = node_executable(ROOT)
    server = subprocess.Popen(
        [
            str(node),
            "node_modules/vite/bin/vite.js",
            "--host",
            "127.0.0.1",
            "--port",
            "5179",
            "--strictPort",
        ],
        cwd=ROOT / "dashboard",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags(),
    )
    checks = {}
    try:
        with sync_playwright() as pw:
            browser = launch_browser(pw, headless=True)
            page = browser.new_page(
                viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
            )
            page.set_default_timeout(12000)
            state = {
                "submitted": False,
                "approved": False,
                "enabled": True,
                "expired": False,
                "session_expired": False,
                "unknown": False,
                "stop": False,
            }
            mutations, submissions, cursors, errors = [], [], [], []
            page.on("pageerror", lambda error: errors.append(str(error)))

            def task():
                return {
                    "task_id": "review-task",
                    "tool": "workflow.notepad_checklist",
                    "status": "unknown"
                    if state["unknown"]
                    else "succeeded"
                    if state["approved"]
                    else "waiting_for_review",
                    "approval_id": "save-review",
                    "verified": state["approved"] and not state["unknown"],
                    "output_name": "study.txt" if state["approved"] else None,
                }

            def approval():
                return {
                    "approval_id": "save-review",
                    "task_id": "review-task",
                    "action_id": "save-action",
                    "tool_name": "uia.save_checklist",
                    "tool_version": "0.1.0",
                    "canonical_args_hash": "a" * 64,
                    "policy_version": "native-save-v1",
                    "target_identity": "native:" + "b" * 64,
                    "observation_identity": "c" * 64,
                    "preview_ref": "private-ref",
                    "expires_at": time.time() + (-1 if state["expired"] else 50),
                    "state": "expired"
                    if state["expired"]
                    else "consumed"
                    if state["approved"]
                    else "pending",
                    "created_at": time.time(),
                    "updated_at": time.time(),
                }

            def route(r):
                path = r.request.url.split("8765")[-1].split("?")[0]
                headers = {"Access-Control-Allow-Origin": "http://127.0.0.1:5179"}
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
                if state["session_expired"] and path == "/api/workflows/capabilities":
                    r.fulfill(
                        status=401, headers=headers, content_type="application/json", body="{}"
                    )
                    return
                body = {}
                if path == "/api/session":
                    body = {"authenticated": True, "expires_at": None}
                elif path == "/api/health":
                    body = {
                        "status": "ok",
                        "mode": "fixture",
                        "stopped": state["stop"],
                        "tools": ["fs.create_note"],
                        "emergency_hotkey": "disabled",
                    }
                elif path == "/api/workflows/capabilities":
                    body = {
                        "notepad_checklist": {
                            "enabled": state["enabled"],
                            "profiles": ["fixture-qualified"] if state["enabled"] else [],
                            "reason": None
                            if state["enabled"]
                            else "Native qualification is missing.",
                        },
                        "stopped": state["stop"],
                        "resource_blocked": False,
                    }
                elif path == "/api/memory":
                    body = []
                elif path == "/api/integrations":
                    body = {
                        "cloud": "disabled",
                        "cloud_pin": None,
                        "upstream": None,
                        "mcp_notes": False,
                    }
                elif path == "/api/voice":
                    body = {"enabled": False, "state": "idle", "revision": 0}
                elif path == "/api/workflows/notepad-checklist":
                    submissions.append(
                        {
                            "id": r.request.headers["x-client-request-id"],
                            "body": r.request.post_data_json,
                        }
                    )
                    if len(submissions) == 1:
                        r.abort()  # Uncertain transport: retry must preserve identity and payload.
                        return
                    state["submitted"] = True
                    body = {"task_id": "review-task", "status": "queued"}
                elif path == "/api/tasks/review-task":
                    body = task()
                elif path == "/api/events":
                    cursors.append(r.request.url)
                    frame = ": ping\n\n"
                    if state["submitted"]:
                        event = {
                            "event_id": 4,
                            "task_id": "review-task",
                            "event_type": "task.snapshot",
                            "timestamp": "fixture",
                            "safe_payload": task(),
                        }
                        frame = "id: 4\nevent: task.snapshot\ndata: " + json.dumps(event) + "\n\n"
                    r.fulfill(
                        status=200, headers=headers, content_type="text/event-stream", body=frame
                    )
                    return
                elif path == "/api/approvals/save-review":
                    body = approval()
                elif path.endswith("/preview"):
                    body = {
                        "destination": "C:/isolated/workspace/study.txt",
                        "text": "Checklist\r\n[ ] <img src=x onerror=alert(1)>\r\n",
                        "encoding": "utf-8",
                    }
                elif path.endswith("/resolve"):
                    state["approved"] = True
                    body = {**approval(), "state": "approved"}
                elif path == "/api/stop":
                    state["stop"] = True
                    body = {"stopped": True, "reset": "restart_required"}
                else:
                    raise AssertionError(path)
                r.fulfill(
                    status=200,
                    headers=headers,
                    content_type="application/json",
                    body=json.dumps(body),
                )

            page.route("http://127.0.0.1:8765/**", route)
            for _ in range(60):
                try:
                    page.goto("http://127.0.0.1:5179/")
                    break
                except Exception:
                    time.sleep(0.1)
            form = page.get_by_role("region", name="Notepad checklist")
            expect(form.get_by_label("Checklist filename")).to_be_enabled()
            form.get_by_label("Checklist filename").fill("study.txt")
            form.get_by_label("Checklist items, one per line").fill("Inspect\nSave")
            form.get_by_role("button", name="Create checklist", exact=True).evaluate(
                "button => {button.click();button.click()}"
            )
            retry = form.get_by_role("button", name="Retry same checklist")
            expect(retry).to_be_enabled()
            expect(form.get_by_label("Checklist filename")).to_be_disabled()
            retry.click()
            expect(page.get_by_role("region", name="Action approval")).to_be_visible()
            assert len(submissions) == 2 and submissions[0] == submissions[1]
            checks["uncertain_retry_same_identity_payload_and_no_double_click"] = True
            count = len(mutations)
            page.reload()
            review = page.get_by_role("region", name="Action approval")
            expect(review).to_be_visible()
            assert len(mutations) == count
            checks["refresh_recovers_review_from_snapshot_without_post"] = True
            expect(page.get_by_label("Exact action preview")).to_contain_text("<img src=x")
            assert page.get_by_label("Exact action preview").locator("img").count() == 0
            checks["literal_preview"] = True
            page.screenshot(path=str(out / "desktop-review.png"), full_page=True)
            page.set_viewport_size({"width": 375, "height": 812})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
            page.screenshot(path=str(out / "mobile-review.png"), full_page=True)
            checks["mobile_no_overflow_and_reduced_motion"] = True
            approve = page.get_by_role("button", name="Approve once")
            approve.focus()
            page.keyboard.press("Enter")
            expect(approve).to_be_disabled()
            expect(page.get_by_role("heading", name="Verified output", exact=True)).to_be_visible()
            assert mutations.count("/api/approvals/save-review/resolve") == 1
            checks["keyboard_approve_once_and_verified_result"] = True
            state.update(approved=False, expired=True)
            page.reload()
            expect(page.get_by_role("button", name="Approve once")).to_be_disabled()
            checks["expired_review_disabled"] = True
            state.update(unknown=True, enabled=False)
            page.reload()
            expect(page.get_by_role("heading", name="Task: unknown", exact=True)).to_be_visible()
            expect(form.get_by_role("button", name="Create checklist", exact=True)).to_be_disabled()
            expect(form.get_by_role("status")).to_contain_text("Native qualification is missing")
            assert page.get_by_role("heading", name="Verified output", exact=True).count() == 0
            checks["unavailable_reason_and_unknown_not_success"] = True
            state["session_expired"] = True
            page.reload()
            expect(form.get_by_role("status")).to_contain_text("session ended")
            checks["expired_session_blocks_checklist"] = True
            stop = page.get_by_role("button", name="Stop all work", exact=True)
            stop.focus()
            page.keyboard.press("Enter")
            assert mutations.count("/api/stop") == 1
            checks["keyboard_stop_always_available"] = True
            checks["no_browser_errors"] = not errors
            checks["reconnect_uses_cursor"] = any("cursor=4" in value for value in cursors)
            browser.close()
        (out / "report.json").write_text(
            json.dumps(
                {"fixture_only": True, "checks": checks, "passed": all(checks.values())}, indent=2
            )
        )
        print(json.dumps(checks))
        assert all(checks.values())
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__ == "__main__":
    main()
