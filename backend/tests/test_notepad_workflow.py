"""Twenty explicit SIMULATED Notepad runs; these are not Windows qualification."""

import asyncio
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from victus.adapters.uia.applications import (
    ApplicationProfile,
    ControlSelector,
    ProcessIdentity,
    UIAWorker,
)
from victus.tools.dispatcher import Dispatcher
from victus.tools.registry import RiskLevel, ToolRegistry
from victus.workflows.common import context_for
from victus.workflows.create_notepad_checklist import (
    ChecklistRequest,
    NotepadTools,
    create_notepad_checklist,
)


class FakeControl:
    def __init__(self, kind, identifier, name="", root=None):
        self.element_info = SimpleNamespace(
            process_id=21,
            control_type=kind,
            automation_id=identifier,
            name=name,
            runtime_id=(21, identifier),
        )
        self.enabled = True
        self.value = ""
        self.children = []
        self.handle = 100 if identifier == "main" else 200

    def is_visible(self):
        return True

    def is_enabled(self):
        return self.enabled

    def descendants(self, control_type):
        return [
            control
            for control in self.children
            if control.element_info.control_type == control_type
        ]


class FakeBackend:
    def __init__(self, executable, *, dpi=96, duplicate=False, initial="", wrong_bytes=False):
        self.executable = executable
        self.dpi = dpi
        self.duplicate = duplicate
        self.wrong_bytes = wrong_bytes
        self.main = FakeControl("Window", "main")
        self.editor = FakeControl("Edit", "editor")
        self.editor.value = initial
        self.file_menu = FakeControl("MenuItem", "file_menu")
        self.save_as = FakeControl("MenuItem", "save_as")
        self.dialog = FakeControl("Window", "save_dialog")
        self.filename = FakeControl("Edit", "filename")
        self.save_button = FakeControl("Button", "save")
        self.main.children = [self.editor, self.file_menu, self.save_as]
        self.dialog.children = [self.filename, self.save_button]
        self.dialog_open = False
        self.calls = []

    def initialize(self):
        pass

    def uninitialize(self):
        pass

    def launch(self, executable, arguments):
        self.calls.append(("launch", str(executable)))
        return SimpleNamespace(pid=21, poll=lambda: None)

    def identity(self, pid):
        return ProcessIdentity(21, 1, str(self.executable))

    def connect(self, pid):
        return SimpleNamespace(windows=self.windows)

    def windows(self):
        return ([self.main, self.main] if self.duplicate else [self.main]) + (
            [self.dialog] if self.dialog_open else []
        )

    def terminate_owned(self, process):
        raise AssertionError("No unrelated process termination")

    def read_value(self, control):
        return control.value

    def read_text(self, control):
        return control.value

    def window_dpi(self, root):
        return self.dpi

    def set_value(self, control, text):
        self.calls.append(("set", control.element_info.automation_id))
        control.value = text

    def invoke(self, control):
        key = control.element_info.automation_id
        self.calls.append(("invoke", key))
        if key == "save_as":
            self.dialog_open = True
            self.main.enabled = False
        if key == "save":
            # Only this simulated native Save writes the checklist, not a workflow shortcut.
            data = b"wrong bytes" if self.wrong_bytes else self.editor.value.encode("utf-8")
            Path(self.filename.value).write_bytes(data)
            self.dialog_open = False
            self.main.enabled = True


def execute(
    tmp_path, *, dpi=96, duplicate=False, initial="", wrong_bytes=False, configure=None,
    diagnostics=None,
):
    root = tmp_path / "workspace"
    root.mkdir()
    executable = tmp_path / "qualified-notepad.exe"
    executable.write_bytes(b"simulation only")
    controls = {
        "editor": ControlSelector("Edit", automation_id="editor"),
        "file_menu": ControlSelector("MenuItem", automation_id="file_menu"),
        "save_as": ControlSelector("MenuItem", automation_id="save_as"),
        "filename": ControlSelector("Edit", automation_id="filename", root_window="save_dialog"),
        "save": ControlSelector("Button", automation_id="save", root_window="save_dialog"),
    }
    profile = ApplicationProfile(
        "qualified-notepad",
        executable,
        ControlSelector("Window", automation_id="main"),
        controls,
        windows={"save_dialog": ControlSelector("Window", automation_id="save_dialog")},
    )
    backend = FakeBackend(
        executable, dpi=dpi, duplicate=duplicate, initial=initial, wrong_bytes=wrong_bytes
    )
    request = ChecklistRequest(
        profile="qualified-notepad", items=["Inspect", "Save", "Verify"], filename="checklist.txt"
    )
    with UIAWorker((profile,), _backend=backend) as worker:
        tools = NotepadTools(worker, request, root, diagnostics=diagnostics)
        registry = ToolRegistry()
        tools.register(registry)
        context = context_for(
            root,
            "simulated",
            threading.Event(),
            {
                "desktop:launch",
                "desktop:read",
                "desktop:interact",
                "filesystem:save",
                "filesystem:read",
            },
            tools.authorize,
            # This harness reviews the bounded workflow and its domain save permit.
            max_unreviewed_risk=RiskLevel.HIGH,
        )
        if configure is not None:
            configure(tools, context, backend, registry)
        result = asyncio.run(create_notepad_checklist(Dispatcher(root, registry), context, request))
    return result, backend, context, root, request


@pytest.mark.parametrize("repetition", range(20))
def test_twenty_simulated_runs_through_shared_dispatcher(tmp_path, repetition):
    result, backend, context, root, request = execute(
        tmp_path, dpi=(96, 120, 144, 192)[repetition % 4]
    )
    assert result.status == "succeeded"
    assert (root / "checklist.txt").read_bytes() == request.editor_text().encode("utf-8")
    assert backend.calls.count(("invoke", "save")) == 1
    names = [row["tool"] for row in context.trace]
    assert names[:5] == [
        "uia.launch_profile",
        "uia.inspect_control",
        "uia.set_checklist",
        "uia.verify_editor",
        "fs.choose_save_destination",
    ]
    assert names[-2:] == ["uia.save_checklist", "fs.verify_checklist"]
    assert all(context.ledger.get(row["action_id"]).status == "verified" for row in context.trace)


@pytest.mark.parametrize("case", ["duplicate", "nonempty", "wrong-bytes"])
def test_unsafe_or_unproved_notepad_workflow_never_succeeds(tmp_path, case):
    result, backend, context, root, request = execute(
        tmp_path,
        duplicate=case == "duplicate",
        initial="unsaved work" if case == "nonempty" else "",
        wrong_bytes=case == "wrong-bytes",
    )
    assert result.status != "succeeded"
    if case != "wrong-bytes":
        assert not (root / "checklist.txt").exists()
        assert ("set", "editor") not in backend.calls


@pytest.mark.parametrize("case", ["existing", "denied", "expired", "stop", "stale", "changed-path"])
def test_save_boundaries_preserve_files_and_prevent_native_save(tmp_path, case):
    from dataclasses import replace

    def configure(tools, context, backend, registry):
        if case == "existing":
            (tools._workspace / tools.request.filename).write_bytes(b"existing contents")
            return
        original = registry.get("uia.save_checklist")

        def before_save(root, args):
            if case == "denied":
                raise PermissionError("review denied")
            if case == "stop":
                context.cancelled.set()
            elif case == "expired":
                path, app, _ = tools._permits[args.permit]
                tools._permits[args.permit] = (path, app, 0)
            elif case == "stale":
                backend.editor.element_info.runtime_id = (999, "restarted")
            elif case == "changed-path":
                path, app, expiry = tools._permits[args.permit]
                tools._permits[args.permit] = (path.with_name("changed.txt"), app, expiry)

        registry._tools[original.name] = replace(original, policy=before_save)

    result, backend, context, root, request = execute(tmp_path, configure=configure)
    assert result.status != "succeeded"
    assert ("invoke", "save") not in backend.calls
    assert not (root / "changed.txt").exists()
    target = root / request.filename
    if case == "existing":
        assert target.read_bytes() == b"existing contents"
    else:
        assert not target.exists()


def test_filename_changes_after_value_write_never_invoke_save(tmp_path):
    def configure(tools, context, backend, registry):
        set_value = backend.set_value

        def changed(control, text):
            set_value(control, text)
            if control is backend.filename:
                control.value = str(tools._workspace / "changed.txt")

        backend.set_value = changed

    result, backend, context, root, request = execute(tmp_path, configure=configure)
    assert result.status == "unknown"
    assert ("invoke", "save") not in backend.calls
    assert not list(root.glob("*.txt"))


def test_stop_during_filename_write_prevents_save_and_keeps_partial_effect_unknown(tmp_path):
    def configure(tools, context, backend, registry):
        set_value = backend.set_value

        def stopped(control, text):
            set_value(control, text)
            if control is backend.filename:
                context.cancelled.set()

        backend.set_value = stopped

    result, backend, context, root, request = execute(tmp_path, configure=configure)
    assert result.status == "unknown"
    assert backend.editor.value == request.editor_text()
    assert ("invoke", "save") not in backend.calls
    assert not (root / request.filename).exists()


def test_editor_change_during_filename_preparation_prevents_native_save(tmp_path):
    import json

    from victus.workflows.diagnostics import PhaseDiagnostics

    def configure(tools, context, backend, registry):
        set_value = backend.set_value

        def changed(control, text):
            set_value(control, text)
            if control is backend.filename:
                backend.editor.value = "changed during filename preparation"

        backend.set_value = changed

    path = tmp_path / "diagnostics.jsonl"
    diagnostics = PhaseDiagnostics(path, "a" * 32)
    try:
        result, backend, context, root, request = execute(
            tmp_path, configure=configure, diagnostics=diagnostics)
    finally:
        diagnostics.close()
    assert result.status == "unknown"
    assert ("invoke", "save") not in backend.calls
    assert not (root / request.filename).exists()
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert any(row["phase"] == "save.pre_dispatch" and row["state"] == "error"
               for row in records)
    assert "changed during filename preparation" not in path.read_text()


def test_diagnosed_workflow_keeps_exact_output_and_reports_save_phases(tmp_path):
    import json

    from victus.workflows.diagnostics import PhaseDiagnostics

    path = tmp_path / "diagnostics.jsonl"
    diagnostics = PhaseDiagnostics(path, "b" * 32)
    try:
        result, backend, context, root, request = execute(tmp_path, diagnostics=diagnostics)
    finally:
        diagnostics.close()
    assert result.status == "succeeded"
    assert (root / request.filename).read_bytes() == request.editor_text().encode()
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert {"save.filename_write", "save.filename_readback", "save.pre_dispatch", "save.invoke",
            "save.postcondition"} <= {row["phase"] for row in records}
    assert len(records) <= 256
    assert "Checklist" not in path.read_text()


def test_matching_bytes_do_not_hide_pending_overwrite_dialog(tmp_path, monkeypatch):
    async def immediate_sleep(_):
        pass

    monkeypatch.setattr("victus.workflows.create_notepad_checklist.asyncio.sleep", immediate_sleep)

    def configure(tools, context, backend, registry):
        invoke = backend.invoke

        def pending(control):
            if control is backend.save_button:
                backend.calls.append(("invoke", "save"))
                Path(backend.filename.value).write_bytes(backend.editor.value.encode())
                # Simulate a concurrent matching file plus unconfirmed overwrite UI.
                assert backend.dialog_open and not backend.main.enabled
            else:
                invoke(control)

        backend.invoke = pending

    result, backend, context, root, request = execute(tmp_path, configure=configure)
    assert result.status == "unknown"
    assert (root / request.filename).read_bytes() == request.editor_text().encode()
    assert backend.dialog_open and not backend.main.enabled
