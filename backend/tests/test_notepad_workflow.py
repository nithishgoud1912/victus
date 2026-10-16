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
from victus.tools.registry import ToolRegistry
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


def execute(tmp_path, *, dpi=96, duplicate=False, initial="", wrong_bytes=False):
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
        tools = NotepadTools(worker, request, root)
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
        )
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
