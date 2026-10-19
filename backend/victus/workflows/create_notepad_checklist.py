"""New checklist -> inspected editor -> approved Save As -> exact file bytes."""

from __future__ import annotations

import asyncio
import time
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from pydantic import Field

from victus.adapters.uia.actions import PatternUnavailable, UIAActions, editor_text
from victus.adapters.uia.applications import ApplicationReference, UIABlocked, UIAWorker
from victus.adapters.uia.selectors import ControlReference, SelectorResolver
from victus.tools.registry import RiskLevel
from victus.workflows.common import (
    Arguments,
    StepFailed,
    WorkflowResult,
    bytes_match,
    digest,
    new_destination,
    spec,
    step,
)
from victus.workflows.diagnostics import safe_error


class ChecklistRequest(Arguments):
    profile: str
    items: list[str] = Field(min_length=1, max_length=50)
    filename: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.txt$")
    editor_key: str = "editor"
    open_save_controls: list[str] = Field(
        default_factory=lambda: ["file_menu", "save_as"], min_length=1, max_length=4
    )
    filename_key: str = "filename"
    save_key: str = "save"
    encoding: str = Field(default="utf-8", pattern=r"^(utf-8|utf-8-sig|utf-16)$")
    allow_keyboard: bool = False

    def editor_text(self):
        if any(
            not item.strip() or "\r" in item or "\n" in item or len(item) > 160
            for item in self.items
        ):
            raise ValueError("Checklist items must be bounded single lines")
        text = "Checklist\r\n" + "\r\n".join("[ ] " + item for item in self.items) + "\r\n"
        if len(text) > 4096 or len(text.encode("utf-8")) > 8192:
            raise ValueError("Checklist exceeds editor limits")
        return text


class Launch(Arguments):
    profile: str


class Inspect(Arguments):
    app_ref: str
    key: str


class SetText(Arguments):
    control_ref: str
    text: str


class Invoke(Arguments):
    app_ref: str
    control_ref: str
    expect_key: str


class Choose(Arguments):
    app_ref: str
    filename: str


class Save(Arguments):
    app_ref: str
    permit: str
    filename_ref: str
    save_ref: str


class VerifyFile(Arguments):
    filename: str


class NotepadTools:
    """Bound only inside the owner worker; no UIA handles are returned as data."""

    def __init__(self, worker, request: ChecklistRequest, workspace: Path, *, diagnostics=None):
        self.worker = worker
        self.request = request
        self.text = request.editor_text()
        self.expected = self.text.encode(request.encoding)
        self.resolver = SelectorResolver(worker)
        self.actions = UIAActions(self.resolver)
        self.app_ref = None
        self.editor_ref = None
        self._permits = {}
        self._control_refs = {}
        self._workspace = workspace
        self._cancelled = None
        self.diagnostics = diagnostics
        self.review_guard = None
        if isinstance(worker, UIAWorker):
            worker.set_operation_guard(self._check_stop)

    def _phase(self, name):
        return self.diagnostics.phase(name) if self.diagnostics is not None else nullcontext()

    def _check_stop(self):
        if self._cancelled is not None and self._cancelled.is_set():
            raise PermissionError("Workflow stopped before native action")

    def _cancellable(self, execute):
        def run(workspace, args, cancelled):
            self._cancelled = cancelled
            self._check_stop()
            return execute(workspace, args)

        return run

    def register(self, registry):
        definitions = [
            spec("uia.launch_profile", Launch, self.launch, self.verify_launch, "desktop:launch"),
            spec("uia.inspect_control", Inspect, self.inspect, self.verify_inspect, "desktop:read"),
            spec("uia.set_checklist", SetText, self.set_text, self.verify_text, "desktop:interact"),
            spec(
                "uia.verify_editor", SetText, self.verify_editor, self.verify_text, "desktop:read"
            ),
            spec(
                "fs.choose_save_destination",
                Choose,
                self.choose,
                self.verify_choose,
                "filesystem:save",
            ),
            spec(
                "uia.invoke_save_control",
                Invoke,
                self.invoke,
                self.verify_invoke,
                "desktop:interact",
            ),
            spec(
                "uia.save_checklist",
                Save,
                self.save,
                self.verify_save,
                "filesystem:save",
                risk=RiskLevel.HIGH,
            ),
            spec(
                "fs.verify_checklist",
                VerifyFile,
                self.verify_file,
                self.verify_saved_file,
                "filesystem:read",
            ),
        ]
        for tool in definitions:
            if self.diagnostics is not None:
                tool = replace(
                    tool,
                    execute=self.diagnostics.wrap(tool.name + ".execute", tool.execute),
                    verify=self.diagnostics.wrap(tool.name + ".verify", tool.verify),
                )
            registry.register(replace(tool, execute_cancellable=self._cancellable(tool.execute)))

    def authorize(self, tool, arguments):
        if tool.name == "uia.launch_profile":
            return arguments.profile == self.request.profile
        if isinstance(arguments, (SetText,)):
            return arguments.text == self.text and arguments.control_ref == self.editor_ref
        if isinstance(arguments, Choose):
            return arguments.filename == self.request.filename and arguments.app_ref == self.app_ref
        if isinstance(arguments, VerifyFile):
            return arguments.filename == self.request.filename
        if isinstance(arguments, Inspect):
            return arguments.app_ref == self.app_ref and arguments.key in {
                self.request.editor_key,
                self.request.filename_key,
                self.request.save_key,
                *self.request.open_save_controls,
            }
        if isinstance(arguments, Invoke):
            sequence = [*self.request.open_save_controls, self.request.filename_key]
            return arguments.app_ref == self.app_ref and any(
                arguments.control_ref == self._control_refs.get(key)
                and arguments.expect_key == sequence[index + 1]
                for index, key in enumerate(self.request.open_save_controls)
            )
        return (
            isinstance(arguments, Save)
            and arguments.app_ref == self.app_ref
            and arguments.filename_ref == self._control_refs.get(self.request.filename_key)
            and arguments.save_ref == self._control_refs.get(self.request.save_key)
            and arguments.permit in self._permits
        )

    def _read(self, reference):
        app, _, control = self.resolver._reacquire(ControlReference(reference), read_only=True)
        backend = self.worker._backend
        try:
            return editor_text(backend.read_value(control), app.profile)
        except Exception as error:
            if isinstance(error, PatternUnavailable) or isinstance(
                error, getattr(backend, "NoPattern", PatternUnavailable)
            ):
                return editor_text(backend.read_text(control), app.profile)
            raise

    def launch(self, workspace, args):
        # The first inspected editor must also be empty: never replace existing work.
        app = self.worker.launch(args.profile)
        self.app_ref = app.ref
        owned = self.worker._resolve_app(app)
        return {
            "app_ref": app.ref,
            "owned_pid": owned.identity.pid,
            "process_created": owned.identity.created,
        }

    def verify_launch(self, data, args):
        self.worker._resolve_app(ApplicationReference(data["app_ref"]))
        return True

    def inspect(self, workspace, args):
        reference = self.resolver.resolve(ApplicationReference(args.app_ref), args.key)
        self._control_refs[args.key] = reference.ref
        if args.key == self.request.editor_key:
            if self._read(reference.ref) != "":
                raise UIABlocked("EMPTY_EDITOR_NOT_PROVED")
            self.editor_ref = reference.ref
        _, root, _ = self.resolver._reacquire(reference)
        return {"control_ref": reference.ref, "window_dpi": self.worker._backend.window_dpi(root)}

    def verify_inspect(self, data, args):
        self.resolver._reacquire(ControlReference(data["control_ref"]))
        return True

    def set_text(self, workspace, args):
        self.actions.set_text(
            ControlReference(args.control_ref),
            args.text,
            allow_keyboard=self.request.allow_keyboard,
            require_empty=True,
        )
        return {"control_ref": args.control_ref, "text_sha256": digest(args.text.encode("utf-8"))}

    def verify_text(self, data, args):
        return self._read(data["control_ref"]) == args.text

    def verify_editor(self, workspace, args):
        return {
            "control_ref": args.control_ref,
            "text_sha256": digest(self._read(args.control_ref).encode("utf-8")),
        }

    def choose(self, workspace, args):
        path = new_destination(workspace, args.filename)
        permit = uuid4().hex
        self._permits[permit] = (path, args.app_ref, time.monotonic() + 60)
        return {"permit": permit, "filename": path.name}

    def verify_choose(self, data, args):
        path, app, expires = self._permits[data["permit"]]
        return (
            path.name == args.filename
            and app == args.app_ref
            and not path.exists()
            and time.monotonic() < expires
        )

    def invoke(self, workspace, args):
        self.actions.invoke(
            ControlReference(args.control_ref), allow_keyboard=self.request.allow_keyboard
        )
        return {"app_ref": args.app_ref, "expect_key": args.expect_key}

    async def verify_invoke(self, data, args):
        for _ in range(80):
            self._check_stop()
            try:
                self.resolver.resolve(ApplicationReference(args.app_ref), args.expect_key)
                return True
            except Exception:
                await asyncio.sleep(0.05)
        return False

    def save(self, workspace, args):
        approved = self._permits.pop(args.permit, None)
        if approved is None or approved[1] != args.app_ref or time.monotonic() > approved[2]:
            raise PermissionError("Save permit missing or expired")
        path = new_destination(workspace, self.request.filename)
        if approved[0] != path:
            raise PermissionError("Save destination changed; new review required")
        if self._read(self.editor_ref) != self.text:
            raise ValueError("Editor changed before save")
        self._check_stop()
        with self._phase("save.filename_write"):
            self.actions.set_text(
                ControlReference(args.filename_ref), str(path), allow_keyboard=False
            )
        with self._phase("save.filename_readback"):
            if self._read(args.filename_ref) != str(path):
                raise ValueError("Save filename was not verified")
        with self._phase("save.pre_dispatch"):
            if self._read(self.editor_ref) != self.text:
                raise ValueError("Editor changed during filename preparation")
            new_destination(workspace, path.name)  # Recheck immediately before native Save.
            self._check_stop()
            if self.review_guard is not None:
                self.review_guard()
        with self._phase("save.invoke"):

            def before_invoke():
                self._check_stop()
                if self.review_guard is not None:
                    self.review_guard()

            self.actions.invoke(
                ControlReference(args.save_ref), allow_keyboard=False, before_invoke=before_invoke
            )
        return {"filename": path.name, "expected_sha256": digest(self.expected)}

    async def verify_save(self, data, args):
        verified = False
        observed_failure = False
        last_code = "SAVE_POSTCONDITION_PENDING"
        try:
            for _ in range(80):
                self._check_stop()
                try:
                    # A matching file alone cannot prove Save completed: an overwrite
                    # prompt or another modal dialog may still be awaiting input.
                    self.resolver._reacquire(ControlReference(self.editor_ref))
                    if self._read(self.editor_ref) != self.text:
                        last_code = "SAVE_EDITOR_CHANGED"
                    elif bytes_match(self._workspace / data["filename"], self.expected):
                        verified = True
                        return True
                    else:
                        last_code = (
                            "SAVE_BYTES_MISMATCH"
                            if (self._workspace / data["filename"]).exists()
                            else "SAVE_ARTIFACT_MISSING"
                        )
                except Exception as error:
                    last_code = safe_error(error)
                    if not observed_failure:
                        observed_failure = True
                        profile = self.worker._profiles[self.request.profile]
                        self.worker._observe_launch("ownership.save_unverified", profile.executable)
                await asyncio.sleep(0.05)
            return False
        finally:
            if self.diagnostics is not None:
                self.diagnostics.record(
                    "save.postcondition",
                    "returned" if verified else "unverified",
                    error_code=None if verified else last_code,
                )

    def verify_file(self, workspace, args):
        return {
            "filename": args.filename,
            "sha256": digest((workspace / args.filename).read_bytes()),
        }

    def verify_saved_file(self, data, args):
        return data["sha256"] == digest(self.expected) and bytes_match(
            self._workspace / args.filename, self.expected
        )


async def create_notepad_checklist(
    dispatcher, context, request: ChecklistRequest
) -> WorkflowResult:
    """Explicit ordered steps; no adapter call occurs in this workflow function."""
    try:
        text = request.editor_text()
        launched = await step(dispatcher, context, "uia.launch_profile", profile=request.profile)
        app = launched["app_ref"]
        editor = await step(
            dispatcher, context, "uia.inspect_control", app_ref=app, key=request.editor_key
        )
        await step(
            dispatcher, context, "uia.set_checklist", control_ref=editor["control_ref"], text=text
        )
        await step(
            dispatcher, context, "uia.verify_editor", control_ref=editor["control_ref"], text=text
        )
        destination = await step(
            dispatcher,
            context,
            "fs.choose_save_destination",
            app_ref=app,
            filename=request.filename,
        )
        for index, key in enumerate(request.open_save_controls):
            control = await step(dispatcher, context, "uia.inspect_control", app_ref=app, key=key)
            next_key = (
                request.open_save_controls[index + 1]
                if index + 1 < len(request.open_save_controls)
                else request.filename_key
            )
            await step(
                dispatcher,
                context,
                "uia.invoke_save_control",
                app_ref=app,
                control_ref=control["control_ref"],
                expect_key=next_key,
            )
        filename = await step(
            dispatcher, context, "uia.inspect_control", app_ref=app, key=request.filename_key
        )
        save = await step(
            dispatcher, context, "uia.inspect_control", app_ref=app, key=request.save_key
        )
        save_context = context
        if context.review_save is not None:
            save_context = await context.review_save(
                Save(
                    app_ref=app,
                    permit=destination["permit"],
                    filename_ref=filename["control_ref"],
                    save_ref=save["control_ref"],
                )
            )
        await step(
            dispatcher,
            save_context,
            "uia.save_checklist",
            app_ref=app,
            permit=destination["permit"],
            filename_ref=filename["control_ref"],
            save_ref=save["control_ref"],
        )
        await step(dispatcher, context, "fs.verify_checklist", filename=request.filename)
        return WorkflowResult(
            "succeeded", request.filename, actions=tuple(x["action_id"] for x in context.trace)
        )
    except StepFailed as error:
        return WorkflowResult(
            error.outcome.status,
            error_code=error.outcome.error_code,
            actions=tuple(x["action_id"] for x in context.trace),
        )
