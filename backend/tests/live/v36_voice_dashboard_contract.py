"""Voice command/reconnect browser fixtures. No hardware or speech qualification."""

import argparse
import json
import subprocess
import time
from pathlib import Path

from browser_support import creation_flags, launch_browser, node_executable
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    server = subprocess.Popen(
        [
            str(node_executable(ROOT)),
            "node_modules/vite/bin/vite.js",
            "--host",
            "127.0.0.1",
            "--port",
            "5182",
            "--strictPort",
        ],
        cwd=ROOT / "dashboard",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags(),
    )
    checks = {}
    mutations = []
    submissions = []
    replies = []
    errors = []
    command_id = "d" * 32
    voice = {
        "enabled": True,
        "state": "reviewing",
        "session_id": "fixture-voice",
        "revision": 1,
        "transcript": {"text": "<img src=x onerror=alert(1)> Create a note", "language": "en"},
        "proposal": None,
        "muted": True,
        "speech_pending": False,
        "wake_available": False,
    }
    stopped = False
    try:
        with sync_playwright() as pw:
            browser = launch_browser(pw, headless=True)
            page = browser.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
            page.on("pageerror", lambda error: errors.append(str(error)))

            def route(r):
                nonlocal stopped
                path = r.request.url.split("8765")[-1].split("?")[0]
                headers = {
                    "Access-Control-Allow-Origin": "http://127.0.0.1:5182",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "*",
                }
                if r.request.method == "OPTIONS":
                    r.fulfill(status=204, headers=headers)
                    return
                if r.request.method == "POST":
                    mutations.append(path)
                if path == "/api/session":
                    body = {"authenticated": True, "expires_at": None}
                elif path == "/api/health":
                    body = {
                        "status": "ok",
                        "mode": "fixture",
                        "stopped": stopped,
                        "tools": ["fs.create_note"],
                        "emergency_hotkey": "disabled",
                    }
                elif path == "/api/workflows/capabilities":
                    body = {
                        "notepad_checklist": {
                            "enabled": False,
                            "profiles": [],
                            "reason": "Native qualification required",
                        },
                        "browser_research": {
                            "enabled": False,
                            "scope": "fixture_only",
                            "source_ids": [],
                            "reason": "Browser qualification pending",
                        },
                        "stopped": stopped,
                        "resource_blocked": False,
                    }
                elif path == "/api/integrations":
                    body = {
                        "cloud": "disabled",
                        "cloud_pin": None,
                        "upstream": None,
                        "mcp_notes": False,
                    }
                elif path == "/api/memory":
                    body = []
                elif path == "/api/voice":
                    body = voice.copy()
                elif path == "/api/voice/submit":
                    submissions.append(r.request.post_data_json)
                    if len(submissions) == 1:
                        r.abort()
                        return
                    voice.update(
                        state="clarifying",
                        revision=2,
                        transcript=None,
                        command={
                            "command_id": command_id,
                            "state": "clarification",
                            "missing": ["filename", "content"],
                            "message": "Provide missing values before any action.",
                        },
                    )
                    r.abort()
                    return
                elif path == "/api/voice/clarify":
                    replies.append(r.request.post_data_json)
                    if len(replies) == 1:
                        r.abort()
                        return
                    voice.update(
                        state="submitted",
                        revision=3,
                        task_id="voice-task",
                        command={
                            "command_id": command_id,
                            "state": "submitted",
                            "missing": [],
                            "task_id": "voice-task",
                            "message": "Task submitted.",
                        },
                        summary="Your task completed with a verified output.",
                    )
                    body = voice.copy()
                elif path == "/api/stop":
                    stopped = True
                    voice.update(
                        state="error", revision=4, error_code="VOICE_STOPPED", command=None
                    )
                    body = {"stopped": True, "reset": "restart_required"}
                elif path == "/api/events":
                    r.fulfill(
                        status=200,
                        headers=headers,
                        content_type="text/event-stream",
                        body=": ping\n\n",
                    )
                    return
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
                    page.goto("http://127.0.0.1:5182/")
                    break
                except Exception:
                    time.sleep(0.1)
            expect(page.get_by_label("Reviewed command", exact=True)).to_be_visible()
            assert page.locator("#voice-transcript img").count() == 0
            checks["literal_transcript"] = True
            count = len(mutations)
            page.reload()
            expect(page.get_by_label("Reviewed command", exact=True)).to_be_visible()
            checks["refresh_before_review_is_read_only"] = len(mutations) == count
            page.get_by_label("Reviewed command", exact=True).fill("Create a note")
            page.get_by_role("button", name="Submit reviewed transcript", exact=True).evaluate(
                "b=>{b.click();b.click()}"
            )
            expect(page.get_by_label("Reviewed command", exact=True)).to_be_disabled()
            expect(page.get_by_label("Review as", exact=True)).to_be_disabled()
            page.get_by_role("button", name="Retry same reviewed transcript", exact=True).click()
            expect(page.get_by_label("Voice filename", exact=True)).to_be_visible()
            checks["reviewed_command_and_uncertain_response_recovered"] = (
                len(submissions) == 2
                and submissions[0] == submissions[1]
                and submissions[0]["command"]["text"] == "Create a note"
                and submissions[0]["confirmation"] == "explicit_user_review"
            )
            count = len(mutations)
            page.reload()
            expect(page.get_by_label("Voice filename", exact=True)).to_be_visible()
            checks["refresh_during_clarification_never_submits"] = len(mutations) == count
            page.get_by_label("Voice filename", exact=True).fill("voice.txt")
            page.get_by_label("Voice note text", exact=True).fill("Private literal text")
            page.get_by_role("button", name="Confirm voice clarification", exact=True).focus()
            page.keyboard.press("Enter")
            expect(page.get_by_label("Voice filename", exact=True)).to_be_disabled()
            page.get_by_role("button", name="Retry same voice clarification", exact=True).click()
            expect(
                page.get_by_text("Your task completed with a verified output.", exact=True)
            ).to_be_visible()
            checks["explicit_keyboard_clarification"] = (
                len(replies) == 2
                and replies[0] == replies[1]
                and replies[0]["fields"]
                == {"filename": "voice.txt", "content": "Private literal text"}
            )
            checks["confirmation_not_save_approval"] = not any(
                "/approvals/" in path for path in mutations
            )
            checks["summary_does_not_read_private_text"] = (
                "Private literal text" not in voice["summary"]
            )
            checks["mobile_reduced_motion"] = page.evaluate(
                'document.documentElement.scrollWidth<=innerWidth && matchMedia("(prefers-reduced-motion: reduce)").matches'
            )
            page.screenshot(path=str(out / "mobile-reviewed-voice.png"), full_page=True)
            page.get_by_role("button", name="Stop all work", exact=True).focus()
            page.keyboard.press("Enter")
            expect(page.get_by_role("button", name="Start recording", exact=True)).to_be_disabled()
            checks["keyboard_stop"] = mutations.count("/api/stop") == 1
            checks["no_page_errors"] = not errors
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
