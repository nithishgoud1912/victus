"""Closed bundled fixture capability. No caller-controlled URLs or network scope."""

import hashlib
import importlib.metadata
import json
import os
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from victus.adapters.playwright.network import NetworkGuard, WebScope
from victus.adapters.playwright.session import BrowserSession
from victus.tools.dispatcher import Dispatcher
from victus.tools.registry import RetryClass, RiskLevel, ToolRegistry, ToolSpec
from victus.workflows.browser_research import (
    BrowserResearchTools,
    ResearchRequest,
    browser_research,
)
from victus.workflows.common import context_for
from victus.workflows.contracts import BROWSER_RESEARCH_TOOL, BrowserResearchSubmission
from victus.workflows.qualification_records import (
    BROWSER_CHECKS,
    file_hash,
    qualification_path,
    qualified_record,
    runtime_identity,
)

PAGES = {
    "/source-a.html": "<!doctype html><title>Fixture source A</title><h1>Source A</h1><p>Deterministic adapters execute approved actions.</p><p>Independent verification checks actual resulting state.</p>",
    "/source-b.html": "<!doctype html><title>Fixture source B</title><h1>Source B</h1><p>A generated summary is not proof that a source was observed.</p><p>Completion requires distinct verified source URLs.</p>",
}
PATHS = {"source-a": "/source-a.html", "source-b": "/source-b.html", "redirect-a": "/redirect"}
FIXTURE_HASH = hashlib.sha256(json.dumps(PAGES, sort_keys=True).encode()).hexdigest()


class FixtureSite:
    def __init__(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/source-a.html")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if self.path not in PAGES:
                    self.send_error(404)
                    return
                data = PAGES[self.path].encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        )
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()
        if self.thread.is_alive():
            raise RuntimeError("Fixture owner did not stop")



def qualified_browser():
    try:
        record = qualified_record(qualification_path("fixture"),
                                  "fixture", BROWSER_CHECKS)
        if record is None:
            return None
        if (
            record["fixture_sha256"] != FIXTURE_HASH
            or record["playwright_version"] != importlib.metadata.version("playwright")
            or record["qualified"] is not True
        ):
            return None
        relative = Path(record["browser_relative_path"])
        if (relative.is_absolute() or ".." in relative.parts
                or len(relative.parts) != 3 or relative.suffix.lower() != ".exe"):
            return None
        cache = Path(
            os.getenv("PLAYWRIGHT_BROWSERS_PATH")
            or Path(os.environ["LOCALAPPDATA"]) / "ms-playwright"
        )
        path = cache / relative
        if (
            path.is_symlink()
            or file_hash(path) != record["browser_sha256"]
        ):
            return None
        return path.resolve()
    except (KeyError, OSError, ValueError, TypeError):
        return None


@dataclass(frozen=True)
class ResearchExecutor:
    origin: str
    browser_executable: str
    runtime_sha256: str = field(default_factory=runtime_identity)

    def request(self, args):
        return ResearchRequest(
            fixture_origin=self.origin,
            source_urls=[self.origin + PATHS[x] for x in args.source_ids],
            reviewed_redirect_urls=[self.origin + "/source-a.html"],
            required_sources=args.required_sources,
            filename=args.filename,
        )

    async def __call__(self, workspace, args, cancelled, authority):
        if runtime_identity() != self.runtime_sha256:
            raise PermissionError("Qualified research implementation changed")
        request = self.request(args)
        reviewed = request.reviewed_urls()
        guard = NetworkGuard(
            WebScope(
                authority.task_id,
                frozenset({self.origin}),
                private_addresses=frozenset({"127.0.0.1"}),
            ),
            authorize=lambda r: (
                r.url in reviewed
                and r.method == "GET"
                and r.resource_type == "document"
                and r.body_sha256 == hashlib.sha256(b"").hexdigest()
            ),
        )
        session = BrowserSession(
            network_guard=guard, browser_executable=Path(self.browser_executable), timeout_ms=5000
        )
        tools = BrowserResearchTools(session, request, workspace)
        registry = ToolRegistry()
        tools.register(registry)
        context = context_for(
            workspace,
            authority.task_id,
            cancelled,
            {"browser:read", "content:generate", "filesystem:save"},
            tools.authorize,
        )
        context.resource_owned = True
        try:
            result = await browser_research(Dispatcher(workspace, registry), context, request)
            if result.status != "succeeded":
                raise RuntimeError("Fixture source promise not verified")
            return workspace / args.filename
        finally:
            await session.close()

    def verify(self, path, args):
        from victus.workflows.qualification import verify_research

        return verify_research(path, self.request(args))

    def spec(self):
        return ToolSpec(
            name=BROWSER_RESEARCH_TOOL,
            version="0.1.0",
            description="Bundled fixture research only",
            argument_model=BrowserResearchSubmission,
            risk_floor=RiskLevel.LOW,
            required_scope="fs:write",
            timeout_seconds=90,
            resource_name="workflow_owner",
            retry_class=RetryClass.NONE,
            execute=reject_unowned,
            execute_owned=self,
            verify=self.verify,
        )


def reject_unowned(*_):
    raise PermissionError("Owned fixture execution required")
