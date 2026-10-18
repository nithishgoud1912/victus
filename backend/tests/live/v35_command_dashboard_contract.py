"""Real browser, simulated HTTP responses; command UI contracts only."""

import argparse
import json
import subprocess
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    out = Path(parser.parse_args().output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    server = subprocess.Popen(
        [
            str(ROOT / ".local/toolchains/node-v24.22.0-win-x64/node.exe"),
            "node_modules/vite/bin/vite.js",
            "--host",
            "127.0.0.1",
            "--port",
            "5181",
            "--strictPort",
        ],
        cwd=ROOT / "dashboard",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    checks = {}
    mutations = []
    submissions = []
    replies = []
    errors = []
    command_id = "c" * 32
    state = {
        "uncertain_submit": True,
        "uncertain_reply": True,
        "submitted": False,
        "stopped": False,
    }

    def clarification():
        return {
            "command_id": command_id,
            "state": "clarification",
            "missing": ["filename", "content"],
            "message": "Provide the missing values before any action.",
            "task_id": None,
        }

    def task():
        return {
            "task_id": "command-task",
            "tool": "internal.command." + command_id,
            "status": "succeeded",
            "verified": True,
            "output_name": "literal.txt",
        }

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 375, "height": 812}, reduced_motion="reduce")
            page.on("pageerror", lambda error: errors.append(str(error)))

            def route(r):
                path = r.request.url.split("8765")[-1].split("?")[0]
                headers = {"Access-Control-Allow-Origin": "http://127.0.0.1:5181"}
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
                body = {}
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
                            "reason": "Native qualification missing",
                        },
                        "browser_research": {
                            "enabled": False,
                            "scope": "fixture_only",
                            "source_ids": [],
                            "reason": "Browser qualification pending",
                        },
                        "stopped": state["stopped"],
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
                elif path == "/api/commands":
                    submissions.append(
                        {
                            "id": r.request.headers["x-client-request-id"],
                            "body": r.request.post_data_json,
                        }
                    )
                    if state["uncertain_submit"]:
                        state["uncertain_submit"] = False
                        r.abort()
                        return
                    body = clarification()
                elif path == "/api/commands/" + command_id:
                    body = clarification()
                elif path == "/api/commands/" + command_id + "/clarify":
                    if r.request.post_data_json.get("filename") == "../bad.txt":
                        r.fulfill(
                            status=422, headers=headers, content_type="application/json", body="{}"
                        )
                        return
                    replies.append(r.request.post_data_json)
                    if state["uncertain_reply"]:
                        state["uncertain_reply"] = False
                        r.abort()
                        return
                    state["submitted"] = True
                    body = {
                        "command_id": command_id,
                        "state": "submitted",
                        "task_id": "command-task",
                        "message": "Task submitted.",
                        "missing": [],
                    }
                elif path == "/api/tasks/command-task":
                    body = task()
                elif path == "/api/events":
                    frame = ": ping\n\n"
                    if state["submitted"]:
                        frame = (
                            "id: 1\nevent: task.snapshot\ndata: "
                            + json.dumps(
                                {
                                    "event_id": 1,
                                    "task_id": "command-task",
                                    "event_type": "task.snapshot",
                                    "timestamp": "fixture",
                                    "safe_payload": task(),
                                }
                            )
                            + "\n\n"
                        )
                    r.fulfill(
                        status=200, headers=headers, content_type="text/event-stream", body=frame
                    )
                    return
                elif path == "/api/stop":
                    state["stopped"] = True
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
            for _ in range(50):
                try:
                    page.goto("http://127.0.0.1:5181/")
                    break
                except Exception:
                    time.sleep(0.1)
            page.get_by_label("Task description", exact=True).fill("Create a note")
            page.get_by_role("button", name="Submit command", exact=True).evaluate(
                "b=>{b.click();b.click()}"
            )
            expect(page.get_by_label("Task description", exact=True)).to_be_disabled()
            page.get_by_role("button", name="Retry same command", exact=True).click()
            expect(page.get_by_label("New filename", exact=True)).to_be_visible()
            checks["uncertain_submit_and_double_click_preserve_identity"] = (
                len(submissions) == 2 and submissions[0] == submissions[1]
            )
            state["uncertain_submit"] = True
            page.get_by_role("button", name="Submit command", exact=True).click()
            expect(
                page.get_by_role("button", name="Retry same command", exact=True)
            ).to_be_visible()
            expect(page.get_by_label("New filename", exact=True)).to_have_count(0)
            page.get_by_role("button", name="Retry same command", exact=True).click()
            expect(page.get_by_label("New filename", exact=True)).to_be_visible()
            checks["new_uncertain_command_hides_previous_clarification"] = (
                len(submissions) == 4
                and submissions[2] == submissions[3]
                and submissions[2]["id"] != submissions[0]["id"]
            )
            count = len(mutations)
            page.reload()
            page.get_by_label("Saved command ID", exact=True).fill(command_id)
            page.get_by_role("button", name="Check saved command", exact=True).click()
            expect(page.get_by_label("New filename", exact=True)).to_be_visible()
            checks["refresh_and_lookup_are_read_only"] = len(mutations) == count
            page.get_by_label("New filename", exact=True).fill("../bad.txt")
            page.get_by_label("Literal note text", exact=True).fill("test")
            page.get_by_role("button", name="Continue command", exact=True).click()
            expect(page.get_by_role("alert")).to_be_visible()
            expect(page.get_by_label("New filename", exact=True)).to_be_enabled()
            checks["definite_rejection_allows_correction"] = True
            page.get_by_label("New filename", exact=True).fill("literal.txt")
            page.get_by_label("Literal note text", exact=True).fill("<img src=x onerror=alert(1)>")
            page.get_by_role("button", name="Continue command", exact=True).focus()
            page.keyboard.press("Enter")
            expect(page.get_by_label("Literal note text", exact=True)).to_be_disabled()
            expect(page.get_by_role("button", name="Submit command", exact=True)).to_be_disabled()
            page.get_by_role("button", name="Retry same response", exact=True).click()
            expect(page.get_by_role("heading", name="Verified output", exact=True)).to_be_visible()
            checks["uncertain_clarification_same_payload"] = (
                len(replies) == 2 and replies[0] == replies[1]
            )
            checks["literal_text_not_html"] = page.locator("img").count() == 0
            checks["mobile_reduced_motion"] = page.evaluate(
                'document.documentElement.scrollWidth<=innerWidth && matchMedia("(prefers-reduced-motion: reduce)").matches'
            )
            page.screenshot(path=str(out / "mobile-command.png"), full_page=True)
            page.get_by_role("button", name="Stop all work", exact=True).focus()
            page.keyboard.press("Enter")
            expect(page.get_by_role("button", name="Submit command", exact=True)).to_be_disabled()
            checks["keyboard_stop"] = mutations.count("/api/stop") == 1
            checks["no_browser_errors"] = not errors
            browser.close()
        report = {"fixture_only": True, "checks": checks, "passed": all(checks.values())}
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))
        assert report["passed"]
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__ == "__main__":
    main()
