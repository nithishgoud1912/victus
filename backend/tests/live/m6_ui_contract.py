"""M6 dashboard contract checks. Does not open a microphone or synthesize real speech."""

import json
import subprocess
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / ".local/m6-browser"
OUT.mkdir(parents=True, exist_ok=True)
server = subprocess.Popen(
    [
        str(ROOT / ".local/toolchains/node-v24.22.0-win-x64/node.exe"),
        "node_modules/vite/bin/vite.js",
        "--host",
        "127.0.0.1",
        "--port",
        "5175",
    ],
    cwd=ROOT / "dashboard",
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=subprocess.CREATE_NO_WINDOW,
)
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(10000)
        page.add_init_script(
            "navigator.mediaDevices.getUserMedia = () => { throw new Error('Browser microphone must not be used') }"
        )
        errors = []
        mutations = []
        displayed = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        voice = {
            "enabled": True,
            "state": "idle",
            "revision": 0,
            "session_id": None,
            "speech_pending": False,
            "muted": False,
            "wake_suppressed": False,
        }

        def route(r):
            path = r.request.url.split("8765")[-1].split("?")[0]
            method = r.request.method
            headers = {
                "Access-Control-Allow-Origin": "http://127.0.0.1:5175",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*",
            }
            if method == "OPTIONS":
                r.fulfill(status=204, headers=headers)
                return
            if method == "POST":
                mutations.append(path)
            if path == "/api/integrations":
                body = {"cloud": "disabled", "cloud_pin": None, "upstream": None, "mcp_notes": False}
            elif path == "/api/memory":
                body = []
            elif path.startswith("/api/voice"):
                if path == "/api/voice" and voice["state"] == "transcribing":
                    voice.update(
                        state="reviewing",
                        revision=voice["revision"] + 1,
                        transcript={
                            "text": "create note voice.txt with text <b>review this</b>",
                            "language": "en",
                        },
                        proposal={
                            "tool": "fs.create_note",
                            "arguments": {"filename": "voice.txt", "text": "<b>review this</b>"},
                        },
                    )
                elif path == "/api/voice/start":
                    voice.update(
                        state="recording",
                        session_id="voice-fixture",
                        revision=voice["revision"] + 1,
                    )
                elif path == "/api/voice/finish":
                    voice.update(state="transcribing", revision=voice["revision"] + 1)
                elif path == "/api/voice/submit":
                    body = r.request.post_data_json
                    assert (
                        body["confirmation"] == "explicit_user_review"
                        and body["action"]["arguments"]["text"] == "corrected by user"
                    )
                    voice.update(
                        state="submitted",
                        revision=voice["revision"] + 1,
                        transcript=None,
                        proposal=None,
                        task_id="voice-task",
                    )
                elif path == "/api/voice" and voice.get("task_id") and not voice.get("summary"):
                    voice.update(
                        summary="Your note was created and verified.",
                        speech_pending=True,
                        revision=voice["revision"] + 1,
                    )
                elif path == "/api/voice/displayed":
                    # Browser POST fires only after the summary is committed to the DOM.
                    displayed.append(
                        page.get_by_text("Your note was created and verified.", exact=True).count()
                        == 1
                    )
                    voice.update(
                        state="speaking",
                        speech_pending=False,
                        wake_suppressed=True,
                        revision=voice["revision"] + 1,
                    )
                elif path == "/api/voice/mute":
                    voice.update(
                        muted=r.request.post_data_json["muted"], revision=voice["revision"] + 1
                    )
                elif path == "/api/voice/cancel":
                    voice.update(state="idle", speech_pending=False, revision=voice["revision"] + 1)
                body = voice.copy()
            elif path == "/api/session":
                body = {"authenticated": True, "expires_at": None}
            elif path == "/api/health":
                body = {
                    "status": "ok",
                    "mode": "fixture",
                    "stopped": False,
                    "tools": ["fs.create_note"],
                    "emergency_hotkey": "registered",
                }
            elif path == "/api/events":
                r.fulfill(
                    status=200, headers=headers, content_type="text/event-stream", body=": ping\n\n"
                )
                return
            elif path == "/api/stop":
                body = {"stopped": True, "reset": "restart_required"}
            else:
                raise AssertionError(path)
            r.fulfill(
                status=200, headers=headers, content_type="application/json", body=json.dumps(body)
            )

        page.route("http://127.0.0.1:8765/**", route)
        for _ in range(50):
            try:
                page.goto("http://127.0.0.1:5175/")
                break
            except Exception:
                time.sleep(0.1)
        expect(page.get_by_role("button", name="Start recording", exact=True)).to_be_enabled()
        page.get_by_role("button", name="Start recording", exact=True).focus()
        page.keyboard.press("Enter")
        expect(page.get_by_role("button", name="Finish recording", exact=True)).to_be_enabled()
        page.get_by_role("button", name="Finish recording", exact=True).focus()
        page.keyboard.press("Enter")
        expect(page.get_by_label("Reviewed filename")).to_have_value("voice.txt")
        expect(page.locator("#voice-transcript")).to_contain_text("<b>review this</b>")
        assert page.locator("#voice-transcript b").count() == 0
        assert "/api/voice/submit" not in mutations
        page.reload()
        expect(page.get_by_label("Reviewed note text")).to_be_visible()
        assert mutations == ["/api/voice/start", "/api/voice/finish"]
        page.get_by_label("Reviewed note text").fill("corrected by user")
        page.get_by_role("button", name="Submit reviewed transcript").evaluate(
            "(b)=>{b.click();b.click()}"
        )
        expect(page.get_by_text("Your note was created and verified.", exact=True)).to_be_visible()
        expect(page.get_by_text("Voice: speaking", exact=True)).to_be_visible()
        assert mutations.count("/api/voice/submit") == 1
        assert mutations.count("/api/voice/displayed") == 1 and displayed and all(displayed)
        page.get_by_role("button", name="Mute spoken results", exact=True).click()
        expect(page.get_by_role("button", name="Unmute spoken results", exact=True)).to_be_visible()
        page.screenshot(path=str(OUT / "laptop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.get_by_role("button", name="Stop all work", exact=True).focus()
        page.keyboard.press("Enter")
        assert mutations.count("/api/stop") == 1
        page.screenshot(path=str(OUT / "mobile.png"), full_page=True)
        assert not errors, errors
        (OUT / "report.json").write_text(
            json.dumps(
                {
                    "contract_browser": "passed",
                    "review_before_submit": True,
                    "reload_does_not_submit": True,
                    "duplicate_click_guard": True,
                    "display_ack_before_speech": True,
                    "mute": True,
                    "keyboard_capture_and_stop": True,
                    "mobile_no_overflow": True,
                    "real_microphone_tested": False,
                    "real_speech_tested": False,
                    "page_errors": errors,
                },
                indent=2,
            )
        )
        browser.close()
    print("M6 fixture browser checks passed")
finally:
    server.terminate()
    server.wait(timeout=10)
