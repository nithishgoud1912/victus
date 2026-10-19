"""Real Chromium qualification against Vite and the built local dashboard."""

import argparse
import json
import secrets
import socket
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import uvicorn
from browser_support import launch_browser
from playwright.sync_api import expect, sync_playwright

from victus.api.app import create_app
from victus.settings import Settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    token = secrets.token_urlsafe(32)
    app = create_app(
        Settings(root / "runtime", token, dashboard_dev_origin="http://127.0.0.1:5173")
    )
    sock = socket.socket()
    sock.bind(("127.0.0.1", 8765))  # Fail rather than attach to another service.
    sock.listen(128)
    server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level="error"))
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.started, "Qualification backend did not start"
        with sync_playwright() as playwright:
            browser = launch_browser(playwright, headless=True)
            errors = []
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("http://127.0.0.1:5173/")
            page.get_by_label("Session token").wait_for(state="visible")
            expect(page.get_by_label("Session token")).to_be_editable()
            page.screenshot(path=str(root / "desktop-disconnected.png"), full_page=True)
            page.get_by_label("Session token").fill(token)
            page.get_by_role("button", name="Connect to VICTUS").click()
            page.get_by_role("heading", name="Your workspace is connected.").wait_for()
            assert page.evaluate("localStorage.length + sessionStorage.length") == 0
            assert not context.cookies(), "Development must use memory, not cookies"
            page.screenshot(path=str(root / "desktop-connected.png"), full_page=True)
            task = page.evaluate("""async () => {
                const source = performance.getEntriesByType('resource').find(x => x.name.includes('/src/api/client.ts'));
                const {apiRequest} = await import(source.name);
                const options = {body: {tool: 'fs.create_note', arguments: {filename: 'transport-note.txt', text: 'Dashboard transport verified'}}, requestId: 'dashboard-smoke-note-1'};
                const first = await apiRequest('POST /api/tasks', options);
                const duplicate = await apiRequest('POST /api/tasks', options);
                return {first, duplicate};
            }""")
            assert task["first"]["task_id"] == task["duplicate"]["task_id"]
            with httpx.Client(
                trust_env=False, headers={"Authorization": "Bearer " + token}
            ) as client:
                for _ in range(200):
                    task_state = client.get(
                        f"http://127.0.0.1:8765/api/tasks/{task['first']['task_id']}"
                    ).json()
                    if task_state["status"] not in {"queued", "prepared", "running"}:
                        break
                    time.sleep(0.05)
            assert task_state["status"] == "succeeded" and task_state["verified"]
            assert (
                root / "runtime/workspace/transport-note.txt"
            ).read_text() == "Dashboard transport verified"
            page.get_by_role("button", name="Disconnect").click()
            page.get_by_label("Session token").wait_for(state="visible")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(root / "mobile.png"), full_page=True)
            context.close()

            production = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = production.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            health_auth_headers = []

            def observe(request):
                if urlsplit(request.url).path == "/api/health":
                    health_auth_headers.append("authorization" in request.all_headers())

            page.on("request", observe)
            page.goto("http://127.0.0.1:8765/")
            expect(page.get_by_label("Session token")).to_be_editable()
            page.get_by_label("Session token").fill(token)
            page.get_by_role("button", name="Connect to VICTUS").click()
            page.get_by_role("heading", name="Your workspace is connected.").wait_for()
            cookie = production.cookies()[0]
            assert (
                cookie["name"] == "victus_session"
                and cookie["httpOnly"]
                and cookie["sameSite"] == "Strict"
            )
            assert page.evaluate("localStorage.length + sessionStorage.length") == 0
            page.reload()
            page.get_by_role("heading", name="Your workspace is connected.").wait_for()
            assert health_auth_headers and not any(health_auth_headers)
            page.screenshot(path=str(root / "production.png"), full_page=True)
            page.get_by_role("button", name="Disconnect").click()
            page.get_by_label("Session token").wait_for(state="visible")
            assert page.evaluate("fetch('/api/health').then(r => r.status)") == 401
            assert not production.cookies()
            assert not errors, errors
            production.close()
            browser.close()
        report = {
            "dev_origin": "http://127.0.0.1:5173",
            "dev_memory_session": True,
            "typed_note_verified": True,
            "deduplicated_task_id": task["first"]["task_id"],
            "production_http_only_session": True,
            "production_reload_restored": True,
            "production_no_bearer_after_bootstrap": True,
            "logout_revoked": True,
            "no_browser_storage": True,
            "mobile_no_overflow": True,
            "page_errors": errors,
        }
        (root / "report.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report))
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        if thread.is_alive():
            raise RuntimeError("Qualification backend did not stop")


if __name__ == "__main__":
    main()
