"""Explicit local qualification entry points, supervised by the existing M1 worker."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import threading
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

from pydantic import Field

from victus.adapters.playwright.network import NetworkGuard, WebScope
from victus.adapters.playwright.session import BrowserSession
from victus.adapters.uia.applications import UIAWorker, load_profiles
from victus.runtime.instance_lock import InstanceLock
from victus.runtime.supervisor import WorkerSupervisor
from victus.safety.cancellation import CancellationController
from victus.storage.action_ledger import ActionLedger
from victus.storage.database import Database
from victus.tools.contracts import ActionProposal
from victus.tools.dispatcher import Dispatcher
from victus.tools.registry import RetryClass, RiskLevel, ToolRegistry, ToolSpec
from victus.tools.steps import WorkerAuthority
from victus.workflows.browser_research import (
    BrowserResearchTools,
    ResearchRequest,
    browser_research,
)
from victus.workflows.common import bytes_match, context_for, new_destination, write_new
from victus.workflows.create_notepad_checklist import (
    ChecklistRequest,
    NotepadTools,
    create_notepad_checklist,
)
from victus.workflows.diagnostics import PhaseDiagnostics
from victus.workflows.qualification_records import file_hash, runtime_identity


class NotepadRun(ChecklistRequest):
    profiles_file: str
    task_id: str


class BrowserRun(ResearchRequest):
    task_id: str
    browser_executable: str | None = None
    device_scale_factor: float = Field(default=1, ge=0.5, le=4)


def workflow_policy(workspace, arguments):
    new_destination(workspace, arguments.filename)
    if isinstance(arguments, NotepadRun):
        arguments.editor_text()
        profile = Path(arguments.profiles_file)
        if not profile.is_absolute() or not profile.is_file() or profile.is_symlink():
            raise PermissionError("Trusted local profile configuration required")
    else:
        arguments.reviewed_urls()


async def run_notepad(workspace, args):
    return await run_notepad_cancellable(workspace, args, None)


async def run_notepad_cancellable(workspace, args, cancelled):
    diagnostics = PhaseDiagnostics(workspace.parent / f"native-{args.task_id}.jsonl", args.task_id)
    try:
        return await _run_notepad_diagnosed(workspace, args, cancelled, diagnostics)
    finally:
        diagnostics.close()


async def _run_notepad_diagnosed(workspace, args, cancelled, diagnostics):
    with UIAWorker(load_profiles(Path(args.profiles_file)), diagnostics=diagnostics) as worker:
        tools = NotepadTools(worker, args, workspace, diagnostics=diagnostics)
        registry = ToolRegistry()
        tools.register(registry)
        context = context_for(
            workspace,
            args.task_id,
            cancelled,
            {
                "desktop:launch",
                "desktop:read",
                "desktop:interact",
                "filesystem:save",
                "filesystem:read",
            },
            tools.authorize,
            max_unreviewed_risk=RiskLevel.HIGH,
        )
        result = await create_notepad_checklist(Dispatcher(workspace, registry), context, args)
        if result.status != "succeeded":
            raise RuntimeError("CHECKLIST_WORKFLOW_NOT_VERIFIED")
    return workspace / args.filename


def verify_notepad(path, args):
    return bytes_match(path, args.editor_text().encode(args.encoding))


async def run_browser(workspace, args):
    return await run_browser_cancellable(workspace, args, None)


async def run_browser_cancellable(workspace, args, cancelled):
    async def execute():
        reviewed = args.reviewed_urls()

        def authorize(request):
            return (
                request.url in reviewed
                and request.method == "GET"
                and request.resource_type == "document"
                and request.body_sha256 == hashlib.sha256(b"").hexdigest()
            )

        guard = NetworkGuard(
            WebScope(
                args.task_id,
                frozenset({args.fixture_origin}),
                private_addresses=frozenset({"127.0.0.1", "::1"}),
            ),
            authorize=authorize,
        )
        session = BrowserSession(
            network_guard=guard,
            browser_executable=Path(args.browser_executable) if args.browser_executable else None,
            device_scale_factor=args.device_scale_factor,
        )
        tools = BrowserResearchTools(session, args, workspace)
        registry = ToolRegistry()
        tools.register(registry)
        context = context_for(
            workspace,
            args.task_id,
            cancelled,
            {"browser:read", "content:generate", "filesystem:save"},
            tools.authorize,
        )
        try:
            result = await browser_research(Dispatcher(workspace, registry), context, args)
            if result.status != "succeeded":
                raise RuntimeError("RESEARCH_PROMISE_NOT_VERIFIED")
        finally:
            await session.close()
        return workspace / args.filename

    return await execute()


def verify_research(path, args):
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        sources = report["sources"]
        return (
            report["kind"] == "browser_research"
            and report["status"] == "succeeded"
            and report["required_sources"] == args.required_sources
            and report["observed_count"] == len({source["url"] for source in sources})
            and report["observed_count"] == len(sources)
            and len({source["observation_id"] for source in sources}) == len(sources)
            and report["observed_count"] >= args.required_sources
            and all(
                source["text"].strip()
                and source["url"] in args.reviewed_urls()
                and len(source["text"]) <= 4000
                and source["observation_id"]
                and source["text_sha256"]
                == hashlib.sha256(source["text"].encode("utf-8")).hexdigest()
                for source in sources
            )
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def outer_spec(kind):
    browser = kind == "browser"
    return ToolSpec(
        name=f"workflow.{kind}",
        version="0.1.0",
        description="Supervised local qualification workflow",
        argument_model=BrowserRun if browser else NotepadRun,
        risk_floor=RiskLevel.HIGH,
        required_scope="workflow:qualified",
        timeout_seconds=120,
        resource_name="workflow_owner",
        retry_class=RetryClass.NONE,
        execute=run_browser if browser else run_notepad,
        execute_cancellable=run_browser_cancellable if browser else run_notepad_cancellable,
        verify=verify_research if browser else verify_notepad,
        policy=workflow_policy,
    )


def supervised_run(workspace, kind, request):
    registry = ToolRegistry()
    registry.register(outer_spec(kind))
    ledger = ActionLedger(Database(workspace.parent).path)
    outer = ledger.prepare_action(
        f"workflow.{kind}",
        "0.1.0",
        request.model_dump(),
        expected_effect_ref=f"task:{request.task_id}",
    )
    cancellation = CancellationController()
    supervisor = WorkerSupervisor(cancellation)
    try:
        outcome = supervisor.run(
            Dispatcher(workspace, registry),
            ActionProposal(tool=f"workflow.{kind}", arguments=request.model_dump()),
            authority=WorkerAuthority(
                request.task_id, outer, frozenset({"workflow:qualified"}), RiskLevel.HIGH
            ),
        )
    except KeyboardInterrupt:
        cancellation.stop()
        raise
    finally:
        # A killed native worker cannot claim rollback or replay. Preserve uncertain evidence.
        for action in ledger.list_unfinished():
            if action.action_id == outer or action.expected_effect_ref != f"task:{request.task_id}":
                continue
            if action.status == "prepared":
                ledger.mark_cancelled(action.action_id)
            else:
                ledger.mark_unknown(action.action_id, error_code="WORKFLOW_WORKER_INTERRUPTED")
    record = ledger.get(outer)
    if record.status == "prepared":
        ledger.mark_failed(outer, error_code=outcome.error_code)
    elif record.status in {"dispatching", "applied"}:
        ledger.mark_unknown(outer, error_code=outcome.error_code)
    return outcome


class FixtureSite:
    """Loopback-only fixture server, with no dependency on public websites."""

    def __init__(self, fixture_root: Path):
        root = fixture_root.resolve()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/source-a.html")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if self.path == "/escape":
                    self.send_response(302)
                    self.send_header("Location", "http://169.254.169.254/")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if self.path == "/slow.html":
                    import time

                    time.sleep(0.4)
                target = root / self.path.lstrip("/")
                if target.parent != root or not target.is_file():
                    self.send_error(404)
                    return
                body = target.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                if self.path == "/download.html":
                    self.send_header("Content-Disposition", "attachment; filename=unreviewed.txt")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.origin = f"http://127.0.0.1:{self.server.server_address[1]}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def qualify(
    kind,
    data_dir,
    *,
    repetitions=20,
    profiles_file=None,
    profile=None,
    browser_executable=None,
    fixture_root=None,
    encoding="utf-8",
):
    if kind not in {"notepad", "browser"}:
        raise ValueError("Unsupported qualification kind")
    if not 1 <= repetitions <= 20:
        raise ValueError("Qualification supports 1 to 20 independent repetitions")
    data_dir = data_dir.resolve()
    # A new root makes repetitions independent of any previous runtime/authority.
    data_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    workspace = data_dir / "workspace"
    workspace.mkdir(exist_ok=True, mode=0o700)
    lock = InstanceLock(data_dir)
    lock.acquire()
    report = {
        "schema_version": 2,
        "normal_memory_guards": True,
        "runtime_sha256": runtime_identity(),
        "kind": kind,
        "requested": repetitions,
        "runs": [],
        "native_windows": os.name == "nt",
        "playwright_version": importlib.metadata.version("playwright"),
    }
    try:
        new_destination(data_dir, f"{kind}-qualification.json")
        if kind == "notepad" and os.name == "nt":
            if profiles_file is None or not profile:
                raise ValueError("Explicit native profile required")
            profiles_sha256 = file_hash(profiles_file)
            (selected,) = [item for item in load_profiles(profiles_file) if item.name == profile]
            report.update(
                profile=profile,
                profiles_sha256=profiles_sha256,
                executable_sha256=file_hash(selected.executable),
            )
        if kind == "notepad" and os.name != "nt":
            report.update(
                status="blocked", executed=0, passed=0, error_code="WINDOWS_UIA_UNAVAILABLE"
            )
        else:
            site = FixtureSite(fixture_root) if kind == "browser" else None
            if site:
                site.__enter__()
            try:
                for index in range(repetitions):
                    from victus.runtime.resources import resources

                    resources().check_current()
                    resources().check_disk(workspace)
                    task_id = uuid4().hex
                    if kind == "browser":
                        request = BrowserRun(
                            fixture_origin=site.origin,
                            source_urls=[site.origin + "/redirect", site.origin + "/source-b.html"],
                            reviewed_redirect_urls=[site.origin + "/source-a.html"],
                            required_sources=2,
                            filename=f"research-{index + 1:02}.json",
                            task_id=task_id,
                            browser_executable=str(browser_executable)
                            if browser_executable
                            else None,
                            device_scale_factor=(1, 1.25, 1.5, 2)[index % 4],
                        )
                    else:
                        request = NotepadRun(
                            profiles_file=str(profiles_file.resolve()),
                            profile=profile,
                            items=["Inspect editor", "Verify saved bytes"],
                            filename=f"checklist-{task_id[:12]}-{index + 1:02}.txt",
                            task_id=task_id,
                            encoding=encoding,
                        )
                    outcome = supervised_run(workspace, kind, request)
                    record = {
                        "task_id": task_id,
                        **asdict(outcome),
                        "destination": request.filename,
                        "verified": outcome.verified,
                    }
                    receipts = [
                        entry
                        for entry in ActionLedger(data_dir / "victus.sqlite3").list_for_task(
                            task_id
                        )
                        if entry.tool_name == f"workflow.{kind}"
                    ]
                    record["action_id"] = receipts[0].action_id if len(receipts) == 1 else None
                    artifact = workspace / request.filename
                    record["sha256"] = file_hash(artifact) if outcome.verified else None
                    if kind == "notepad":
                        diagnostic = data_dir / f"native-{task_id}.jsonl"
                        if diagnostic.is_file():
                            phases = [
                                json.loads(line) for line in diagnostic.read_text().splitlines()
                            ]
                            errors = [phase for phase in phases if phase["state"] == "error"]
                            record["diagnostics"] = {
                                "private_file": diagnostic.name,
                                "records": len(phases),
                                "last_phase": phases[-1]["phase"] if phases else None,
                                "error_code": errors[-1]["error_code"] if errors else None,
                            }
                    if kind == "browser" and outcome.verified:
                        artifact = json.loads(
                            (workspace / request.filename).read_text(encoding="utf-8")
                        )
                        record["environment"] = artifact.get("environment", {})
                        record["observed_sources"] = artifact["observed_count"]
                    report["runs"].append(record)
                    print(f"{kind} {index + 1}/{repetitions}: {outcome.status}", flush=True)
                    if kind == "notepad" and not outcome.verified:
                        report["stopped_after_failed_native_run"] = True
                        break  # Never multiply uncertain native effects to fill a quota.
            finally:
                if site:
                    site.__exit__()
            report.update(
                executed=len(report["runs"]), passed=sum(run["verified"] for run in report["runs"])
            )
            report["status"] = "succeeded" if report["passed"] == repetitions else "failed"
    except (Exception, KeyboardInterrupt) as error:
        report.update(
            status="failed",
            executed=len(report["runs"]),
            passed=sum(run.get("verified") is True for run in report["runs"]),
            error_code="INTERRUPTED"
            if isinstance(error, KeyboardInterrupt)
            else "QUALIFICATION_FAILED",
        )
    finally:
        report["real_windows_dpi_gate"] = "pending_observed_physical_session"
        try:
            report["runtime_end_sha256"] = runtime_identity()
            if report["runtime_end_sha256"] != report["runtime_sha256"]:
                report.update(
                    status="failed", error_code="IMPLEMENTATION_CHANGED_DURING_QUALIFICATION"
                )
            if kind == "notepad" and report.get("profiles_sha256") is not None:
                if (
                    file_hash(profiles_file) != report["profiles_sha256"]
                    or file_hash(selected.executable) != report["executable_sha256"]
                ):
                    report.update(
                        status="failed", error_code="NATIVE_PROFILE_CHANGED_DURING_QUALIFICATION"
                    )
        except (OSError, ValueError, TypeError):
            report.update(status="failed", error_code="QUALIFICATION_IDENTITY_UNAVAILABLE")
        try:
            destination = write_new(
                data_dir,
                f"{kind}-qualification.json",
                (json.dumps(report, indent=2) + "\n").encode("utf-8"),
            )
        finally:
            lock.release()
    return destination
