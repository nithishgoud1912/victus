"""M7 dashboard checks using contract fixtures; no personal memory is imported."""

import json
import subprocess
import time
from pathlib import Path

from browser_support import creation_flags, launch_browser, node_executable
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / ".local/m7-browser"
OUT.mkdir(parents=True, exist_ok=True)
server = subprocess.Popen(
    [
        str(node_executable(ROOT)),
        "node_modules/vite/bin/vite.js",
        "--host",
        "127.0.0.1",
        "--port",
        "5176",
    ],
    cwd=ROOT / "dashboard",
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=creation_flags(),
)
try:
    with sync_playwright() as pw:
        browser = launch_browser(pw, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        entries = []
        mutations = []
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def route(r):
            path = r.request.url.split("8765")[-1].split("?")[0]
            method = r.request.method
            headers = {
                "Access-Control-Allow-Origin": "http://127.0.0.1:5176",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*",
            }
            if method == "OPTIONS":
                r.fulfill(status=204, headers=headers)
                return
            if method != "GET":
                mutations.append(path)
            if path == "/api/integrations":
                body = {
                    "cloud": "disabled",
                    "cloud_pin": None,
                    "upstream": None,
                    "mcp_notes": False,
                }
            elif path == "/api/session":
                body = {"authenticated": True, "expires_at": None}
            elif path == "/api/workflows/capabilities":
                body = {
                    "notepad_checklist": {
                        "enabled": False,
                        "profiles": [],
                        "reason": "Native qualification and Save review qualification required.",
                    },
                    "stopped": False,
                    "resource_blocked": False,
                }
            elif path == "/api/health":
                body = {
                    "status": "ok",
                    "mode": "fixture",
                    "stopped": False,
                    "tools": ["fs.create_note"],
                    "emergency_hotkey": "disabled",
                }
            elif path == "/api/voice":
                body = {"enabled": False, "state": "idle", "revision": 0}
            elif path == "/api/events":
                r.fulfill(
                    status=200, headers=headers, content_type="text/event-stream", body=": ping\n\n"
                )
                return
            elif path == "/api/memory" and method == "GET":
                body = entries
            elif path == "/api/memory" or (path.startswith("/api/memory/") and method == "POST"):
                data = r.request.post_data_json
                assert data["confirmation"] == "explicit_user_review"
                entries[:] = [
                    {
                        "memory_id": "m1",
                        "type": data["type"],
                        "value": data["value"],
                        "provenance": data["provenance"],
                        "created_at": 1,
                        "updated_at": 1,
                        "last_confirmed_at": 1,
                        "context_only": True,
                    }
                ]
                body = entries[0]
            elif path == "/api/memory/m1" and method == "DELETE":
                entries.clear()
                body = {"forgotten": True}
            elif path == "/api/memory/export":
                body = {"entries": entries, "context_only": True}
            elif path == "/api/diagnostics/preview":
                body = {
                    "preview_id": "p1",
                    "sha256": "fixture-hash",
                    "contents": '{"redacted":true}',
                    "expires_at": time.time() + 300,
                }
            elif path == "/api/diagnostics/export":
                assert (
                    page.get_by_label("Diagnostic export preview").inner_text()
                    == '{"redacted":true}'
                )
                assert r.request.post_data_json["confirmation"] == "explicit_user_review"
                body = {"contents": '{"redacted":true}', "sha256": "fixture-hash"}
            else:
                raise AssertionError(path)
            r.fulfill(
                status=200, headers=headers, content_type="application/json", body=json.dumps(body)
            )

        page.route("http://127.0.0.1:8765/**", route)
        for _ in range(50):
            try:
                page.goto("http://127.0.0.1:5176/")
                break
            except Exception:
                time.sleep(0.1)
        page.get_by_text("Memory and diagnostics", exact=True).click()
        page.get_by_label("Reviewed memory value").fill("tone=<b>concise</b>")
        page.get_by_role("button", name="Remember reviewed value", exact=True).evaluate(
            "(b)=>{b.click();b.click()}"
        )
        expect(page.get_by_role("button", name="Forget memory", exact=True)).to_be_visible()
        assert mutations.count("/api/memory") == 1
        assert page.locator("details li b").count() == 0
        page.reload()
        page.get_by_text("Memory and diagnostics", exact=True).click()
        expect(page.get_by_role("button", name="Forget memory", exact=True)).to_be_visible()
        assert mutations == ["/api/memory"]
        page.get_by_role("button", name="Edit memory", exact=True).click()
        page.get_by_label("Reviewed memory value").fill("tone=friendly")
        page.get_by_role("button", name="Save reviewed edit", exact=True).click()
        expect(page.get_by_text("tone=friendly", exact=True)).to_be_visible()
        page.get_by_role("button", name="Review redacted diagnostics", exact=True).click()
        expect(page.get_by_label("Diagnostic export preview")).to_be_visible()
        assert "/api/diagnostics/export" not in mutations
        with page.expect_download() as download:
            page.get_by_role("button", name="Download reviewed diagnostics", exact=True).click()
        download.value.save_as(str(OUT / "diagnostics.json"))
        assert json.loads((OUT / "diagnostics.json").read_text()) == {"redacted": True}
        page.get_by_role("button", name="Forget memory", exact=True).focus()
        page.keyboard.press("Enter")
        expect(page.get_by_role("button", name="Forget memory", exact=True)).to_have_count(0)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.screenshot(path=str(OUT / "mobile.png"), full_page=True)
        assert not errors, errors
        (OUT / "report.json").write_text(
            json.dumps(
                {
                    "reviewed_memory_crud": True,
                    "no_reload_mutation": True,
                    "duplicate_click_guard": True,
                    "literal_value_rendering": True,
                    "diagnostic_review_before_download": True,
                    "keyboard_forget": True,
                    "mobile_no_overflow": True,
                    "page_errors": errors,
                },
                indent=2,
            )
        )
        browser.close()
    print("M7 browser checks passed")
finally:
    server.terminate()
    server.wait(timeout=10)
