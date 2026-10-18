"""M8 browser fixtures; no microphone, network transfer or credential use."""

import json
import subprocess
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / ".local/m8-browser"
OUT.mkdir(parents=True, exist_ok=True)
server = subprocess.Popen([
    str(ROOT / ".local/toolchains/node-v24.22.0-win-x64/node.exe"),
    "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", "5177",
], cwd=ROOT / "dashboard", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    creationflags=subprocess.CREATE_NO_WINDOW)
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
        errors, mutations, reviews = [], [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        voice = {"enabled": True, "state": "idle", "revision": 0,
                 "wake_available": True, "wake_listening": False}
        pin = {"name": "fixture/model", "digest": "sha256:" + "a" * 64}

        def route(r):
            path = r.request.url.split("8765")[-1].split("?")[0]
            method = r.request.method
            headers = {"Access-Control-Allow-Origin": "http://127.0.0.1:5177",
                       "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "*"}
            if method == "OPTIONS":
                r.fulfill(status=204, headers=headers)
                return
            if method == "POST":
                mutations.append(path)
            if path == "/api/session":
                body = {"authenticated": True, "expires_at": None}
            elif path == '/api/workflows/capabilities': body = {'notepad_checklist': {'enabled': False, 'profiles': [], 'reason': 'Native qualification and Save review qualification required.'}, 'stopped': False, 'resource_blocked': False}
            elif path == "/api/health":
                body = {"status": "ok", "mode": "fixture", "stopped": False,
                        "tools": ["fs.create_note"], "emergency_hotkey": "registered"}
            elif path == "/api/events":
                r.fulfill(status=200, headers=headers, content_type="text/event-stream", body=": ping\n\n")
                return
            elif path == "/api/memory":
                body = []
            elif path == "/api/integrations":
                body = {"cloud": "consent_required", "cloud_pin": pin,
                        "upstream": "SelectedProvider", "mcp_notes": True}
            elif path == "/api/integrations/cloud/preview":
                body = {"id": "a" * 32, "recipient": "OpenRouter / SelectedProvider / fixture/model",
                        "body": '<img src=x onerror="alert(1)"> exact private prompt',
                        "sha256": "b" * 64, "expires_in_seconds": 1.0}
            elif path == "/api/integrations/cloud/review":
                reviews.append(r.request.post_data_json)
                body = {"response": {"pin": pin, "content": '<b>review this answer</b>',
                         "usage": {"input_tokens": 8, "output_tokens": 6}}}
            elif path.startswith("/api/voice"):
                if path.endswith("wake/enable"):
                    voice.update(wake_listening=True, revision=voice["revision"] + 1)
                elif path.endswith("wake/disable"):
                    voice.update(wake_listening=False, revision=voice["revision"] + 1)
                body = voice
            elif path == "/api/stop":
                body = {"stopped": True, "reset": "restart_required"}
            else:
                raise AssertionError(path)
            r.fulfill(status=200, headers=headers, content_type="application/json", body=json.dumps(body))

        page.route("http://127.0.0.1:8765/**", route)
        for _ in range(60):
            try:
                page.goto("http://127.0.0.1:5177/")
                break
            except Exception:
                time.sleep(0.1)
        expect(page.get_by_role("button", name="Enable wake listening")).to_be_enabled()
        assert mutations == []
        page.get_by_role("button", name="Enable wake listening").focus()
        page.keyboard.press("Enter")
        expect(page.get_by_text("Wake word: Listening on this microphone")).to_be_visible()
        page.get_by_role("button", name="Disable wake listening").click()
        page.get_by_label("Text to propose for transfer").fill("private fixture prompt")
        page.get_by_role("button", name="Preview transfer", exact=True).click()
        expect(page.get_by_label("Exact request body")).to_contain_text('<img src=x')
        assert page.get_by_label("Exact request body").locator("img").count() == 0
        assert reviews == []
        page.get_by_role("button", name="Deny transfer", exact=True).focus()
        page.keyboard.press("Enter")
        assert reviews[0]["approve"] is False
        page.get_by_role("button", name="Preview transfer", exact=True).click()
        expect(page.get_by_role("button", name="Approve this transfer once")).to_be_disabled(timeout=3000)
        page.get_by_role("button", name="Deny transfer", exact=True).click()
        page.get_by_role("button", name="Preview transfer", exact=True).click()
        page.get_by_role("button", name="Approve this transfer once").evaluate("b=>{b.click();b.click()}")
        expect(page.get_by_text('<b>review this answer</b>', exact=True)).to_be_visible()
        assert len([r for r in reviews if r["approve"]]) == 1
        assert page.locator("pre b").count() == 0
        before = list(mutations)
        page.reload()
        expect(page.get_by_label("Text to propose for transfer")).to_have_value("")
        assert mutations == before
        page.get_by_label("Text to propose for transfer").fill("stop during review")
        page.get_by_role("button", name="Preview transfer", exact=True).click()
        expect(page.get_by_label("Exact cloud transfer preview")).to_be_visible()
        page.screenshot(path=str(OUT / "laptop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(OUT / "mobile.png"), full_page=True)
        stop = page.get_by_role("button", name="Stop all work", exact=True)
        stop.focus()
        page.keyboard.press("Enter")
        expect(page.get_by_label("Exact cloud transfer preview")).to_have_count(0)
        assert mutations.count("/api/stop") == 1
        assert not errors, errors
        (OUT / "report.json").write_text(json.dumps({
            "browser_contract": "passed", "keyboard_wake_controls": True,
            "exact_literal_preview": True, "deny_expiry_and_duplicate_guard": True,
            "reload_no_mutation": True, "mobile_no_overflow": True,
            "keyboard_stop_during_review": True, "page_errors": errors,
            "real_audio_or_cloud_tested": False,
        }, indent=2))
        browser.close()
    print("M8 browser contracts passed")
finally:
    server.terminate()
    server.wait(timeout=10)
