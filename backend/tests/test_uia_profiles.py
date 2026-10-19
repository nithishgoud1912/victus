"""UIA actor tests with a fake native boundary; no desktop actions on this host."""

import pickle
from dataclasses import replace
from unittest.mock import Mock

import pytest

from victus.adapters.uia.actions import PatternUnavailable, UIAActions
from victus.adapters.uia.applications import (
    ApplicationProfile,
    ControlSelector,
    ProcessIdentity,
    UIABlocked,
    UIAUncertain,
    UIAWorker,
)
from victus.adapters.uia.selectors import SelectorResolver


def control(pid, kind, auto_id, name, runtime):
    wrapper = Mock()
    wrapper.element_info = Mock(
        process_id=pid, control_type=kind, automation_id=auto_id, runtime_id=runtime
    )
    wrapper.element_info.name = name
    wrapper.is_visible.return_value = True
    wrapper.is_enabled.return_value = True
    wrapper.has_keyboard_focus.return_value = True
    return wrapper


@pytest.fixture
def actor(tmp_path):
    executable = tmp_path / "qualified.exe"
    executable.write_bytes(b"fake-test-executable")
    profile = ApplicationProfile(
        "qualified",
        executable,
        ControlSelector("Window", automation_id="main"),
        {
            "editor": ControlSelector("Edit", automation_id="editor", name="Document"),
            "save": ControlSelector("Button", automation_id="save", name="Save"),
        },
        allow_keyboard_fallback=True,
    )
    backend = Mock()
    process = Mock(pid=21)
    process.poll.return_value = None
    backend.launch.return_value = process
    backend.identity.return_value = ProcessIdentity(21, 99, str(executable))
    backend.is_foreground.return_value = True
    backend.read_value.return_value = "expected"
    backend.read_text.return_value = ""
    editor = control(21, "Edit", "editor", "Document", (1, 2))
    button = control(21, "Button", "save", "Save", (1, 3))
    window = control(21, "Window", "main", "Qualified", (1,))
    window.handle = 100
    window.descendants.return_value = [editor, button]
    backend.connect.return_value.windows.return_value = [window]
    worker = UIAWorker((profile,), _backend=backend)
    worker.start()
    application = worker.launch("qualified")
    resolver = SelectorResolver(worker)
    yield Mock(
        worker=worker,
        backend=backend,
        profile=profile,
        process=process,
        editor=editor,
        button=button,
        window=window,
        application=application,
        resolver=resolver,
        actions=UIAActions(resolver),
    )
    worker.close()


def test_allowlist_and_process_identity(actor):
    with pytest.raises(UIABlocked, match="ALLOWLISTED"):
        actor.worker.launch("unlisted")
    assert actor.backend.launch.call_count == 1
    assert actor.backend.launch.call_args.args == (actor.profile.executable, ())
    with pytest.raises(TypeError):
        pickle.dumps(actor.worker)


def test_value_pattern_then_independent_read_no_keyboard(actor):
    ref = actor.resolver.resolve(actor.application, "editor")
    result = actor.actions.set_text(ref, "expected")
    assert result.status == "verified" and result.method == "value_pattern"
    actor.backend.set_value.assert_called_once_with(actor.editor, "expected")
    actor.backend.read_value.assert_called_once_with(actor.editor)
    actor.backend.send_unicode.assert_not_called()
    actor.backend.read_value.return_value = "different"
    assert actor.actions.set_text(ref, "expected").status == "unverified"


def test_invoke_requires_application_postcondition(actor):
    ref = actor.resolver.resolve(actor.application, "save")
    assert actor.actions.invoke(ref).status == "unverified"
    actor.backend.invoke.assert_called_once_with(actor.button)
    actor.backend.send_enter.assert_not_called()


@pytest.mark.parametrize("duplicate", ["windows", "controls"])
def test_multiple_matches_never_choose_first(actor, duplicate):
    if duplicate == "windows":
        actor.backend.connect.return_value.windows.return_value = [actor.window, actor.window]
    else:
        actor.window.descendants.return_value = [actor.editor, actor.editor]
    with pytest.raises(UIABlocked, match="AMBIGUOUS"):
        actor.resolver.resolve(actor.application, "editor")
    actor.backend.set_value.assert_not_called()


@pytest.mark.parametrize("change", ["pid-reused", "exited", "replaced"])
def test_restart_or_replaced_control_requires_reacquisition(actor, change):
    ref = actor.resolver.resolve(actor.application, "editor")
    if change == "pid-reused":
        actor.backend.identity.return_value = replace(
            actor.backend.identity.return_value, created=100
        )
    elif change == "exited":
        actor.process.poll.return_value = 0
    else:
        actor.editor.element_info.runtime_id = (9, 9)
    with pytest.raises(UIABlocked, match="REACQUIRE"):
        actor.actions.set_text(ref, "private")
    actor.backend.set_value.assert_not_called()


def test_foreign_process_not_selected(actor):
    actor.editor.element_info.process_id = 77
    with pytest.raises(UIABlocked, match="MISSING"):
        actor.resolver.resolve(actor.application, "editor")


def test_keyboard_requires_both_permissions(actor):
    actor.backend.set_value.side_effect = PatternUnavailable
    ref = actor.resolver.resolve(actor.application, "editor")
    with pytest.raises(UIABlocked, match="NOT_REVIEWED"):
        actor.actions.set_text(ref, "a")
    actor.worker._applications[actor.application.ref].profile = replace(
        actor.profile, allow_keyboard_fallback=False
    )
    with pytest.raises(UIABlocked, match="NOT_REVIEWED"):
        actor.actions.set_text(ref, "a", allow_keyboard=True)
    actor.backend.send_unicode.assert_not_called()


def test_unicode_literal_and_foreground_checked_each_time(actor):
    actor.backend.set_value.side_effect = PatternUnavailable
    ref = actor.resolver.resolve(actor.application, "editor")
    assert actor.actions.set_text(ref, "^{}", allow_keyboard=True).status == "unverified"
    assert [call.args[0] for call in actor.backend.send_unicode.call_args_list] == [94, 123, 125]
    assert actor.backend.is_foreground.call_count == 3


def test_foreground_changes_stops_next_key(actor):
    actor.backend.set_value.side_effect = PatternUnavailable
    actor.backend.is_foreground.side_effect = [True, False]
    ref = actor.resolver.resolve(actor.application, "editor")
    with pytest.raises(UIAUncertain, match="INTERRUPTED"):
        actor.actions.set_text(ref, "abc", allow_keyboard=True)
    actor.backend.send_unicode.assert_called_once_with(ord("a"))


def test_keyboard_enter_requires_foreground_and_focus(actor):
    actor.backend.invoke.side_effect = PatternUnavailable
    ref = actor.resolver.resolve(actor.application, "save")
    actor.button.has_keyboard_focus.return_value = False
    with pytest.raises(UIABlocked, match="FOREGROUND_OR_FOCUS"):
        actor.actions.invoke(ref, allow_keyboard=True)
    actor.backend.send_enter.assert_not_called()


def test_pattern_failure_never_falls_back_or_exposes_text(actor):
    actor.backend.set_value.side_effect = RuntimeError("PRIVATE_TYPED_TEXT")
    ref = actor.resolver.resolve(actor.application, "editor")
    with pytest.raises(UIAUncertain, match="VALUE_WRITE_UNCERTAIN"):
        actor.actions.set_text(ref, "PRIVATE_TYPED_TEXT", allow_keyboard=True)
    actor.backend.send_unicode.assert_not_called()


def test_thread_identity_and_shutdown(actor, monkeypatch):
    monkeypatch.setattr("victus.adapters.uia.applications.threading.get_ident", lambda: -1)
    with pytest.raises(UIABlocked, match="FOREIGN"):
        actor.resolver.resolve(actor.application, "editor")
    monkeypatch.undo()
    actor.worker.close()
    actor.worker.close()
    actor.backend.uninitialize.assert_called_once()
    actor.backend.terminate_owned.assert_not_called()


def test_non_windows_backend_is_blocked():
    import os

    from victus.adapters.uia.native import WindowsBackend

    if os.name != "nt":
        with pytest.raises(UIABlocked, match="WINDOWS"):
            WindowsBackend().initialize()


def test_no_keyboard_replacement_of_nonempty_editor(actor):
    actor.backend.set_value.side_effect = PatternUnavailable
    actor.backend.read_text.return_value = "existing unsaved text"
    ref = actor.resolver.resolve(actor.application, "editor")
    with pytest.raises(UIABlocked, match="REPLACEMENT"):
        actor.actions.set_text(ref, "new", allow_keyboard=True)
    actor.backend.send_unicode.assert_not_called()


def test_native_launcher_uses_argv_without_shell(monkeypatch, tmp_path):
    from victus.adapters.uia.native import WindowsBackend

    popen = Mock()
    monkeypatch.setattr("victus.adapters.uia.native.subprocess.Popen", popen)
    executable = tmp_path / "approved.exe"
    WindowsBackend().launch(executable, ("literal;not-a-shell-command",))
    assert popen.call_args.args[0] == [str(executable), "literal;not-a-shell-command"]
    assert popen.call_args.kwargs["shell"] is False


def test_profile_file_rejects_extra_fields_and_validates_selectors(tmp_path):
    import json

    from victus.adapters.uia.applications import load_profiles

    path = tmp_path / "profiles.json"
    record = {
        "name": "test",
        "executable": str(tmp_path / "test.exe"),
        "window": {"control_type": "Window", "name": "Test"},
        "controls": {"editor": {"control_type": "Edit", "automation_id": "editor"}},
    }
    path.write_text(json.dumps([record]))
    assert load_profiles(path)[0].controls["editor"].automation_id == "editor"
    record["shell"] = True
    path.write_text(json.dumps([record]))
    with pytest.raises(ValueError):
        load_profiles(path)


def test_exact_class_selector_never_uses_title_alone(actor):
    actor.editor.element_info.class_name = "RichEditD2DPT"
    actor.worker._applications[actor.application.ref].profile = replace(
        actor.profile,
        controls={"editor": ControlSelector("Edit", class_name="RichEditD2DPT")},
    )
    ref = actor.resolver.resolve(actor.application, "editor")
    actor.editor.element_info.class_name = "OtherEditor"
    with pytest.raises(UIABlocked, match="MISSING"):
        actor.actions.set_text(ref, "expected")
    actor.backend.set_value.assert_not_called()


@pytest.mark.parametrize("current", ["existing", None])
def test_required_empty_value_pattern_blocks_before_write(actor, current):
    actor.backend.read_value.return_value = current
    ref = actor.resolver.resolve(actor.application, "editor")
    with pytest.raises(UIABlocked, match="EMPTY_EDITOR"):
        actor.actions.set_text(ref, "expected", require_empty=True)
    actor.backend.set_value.assert_not_called()
    actor.backend.send_unicode.assert_not_called()


def test_required_empty_read_failure_blocks_before_write(actor):
    actor.backend.read_value.side_effect = PatternUnavailable
    actor.backend.read_text.side_effect = RuntimeError("private")
    ref = actor.resolver.resolve(actor.application, "editor")
    with pytest.raises(UIABlocked, match="EMPTY_EDITOR"):
        actor.actions.set_text(ref, "expected", require_empty=True)
    actor.backend.set_value.assert_not_called()


def test_required_empty_rechecked_immediately_before_value_write(actor):
    actor.backend.read_value.side_effect = ["", "expected"]
    ref = actor.resolver.resolve(actor.application, "editor")
    assert actor.actions.set_text(ref, "expected", require_empty=True).status == "verified"
    assert actor.backend.read_value.call_count == 2


def test_newline_normalization_is_explicit_and_preserves_other_changes(actor):
    from victus.adapters.uia.actions import editor_text

    assert editor_text("a\rb\r", actor.profile) == "a\rb\r"
    profile = replace(actor.profile, editor_newlines="crlf")
    assert editor_text("a\rb\r\n", profile) == "a\r\nb\r\n"
    actor.worker._applications[actor.application.ref].profile = profile
    ref = actor.resolver.resolve(actor.application, "editor")
    actor.backend.read_value.return_value = "a\rb\r"
    assert actor.actions.set_text(ref, "a\r\nb\r\n").status == "verified"
    actor.backend.read_value.return_value = "a\rc\r"
    assert actor.actions.set_text(ref, "a\r\nb\r\n").status == "unverified"


def test_nested_dialog_under_disabled_main_reacquires_exact_root(actor):
    dialog = control(21, "Window", "dialog", "Save as", (1, 7))
    dialog.descendants.return_value = [actor.button]
    actor.window.is_enabled.return_value = False
    actor.window.descendants.return_value = [dialog]
    actor.worker._applications[actor.application.ref].profile = replace(
        actor.profile,
        windows={"dialog": ControlSelector("Window", automation_id="dialog")},
        controls={"save": ControlSelector("Button", automation_id="save", root_window="dialog")},
    )
    ref = actor.resolver.resolve(actor.application, "save")
    assert actor.actions.invoke(ref).method == "invoke_pattern"
    other = control(21, "Window", "dialog", "Save as", (1, 8))
    actor.window.descendants.return_value = [dialog, other]
    with pytest.raises(UIABlocked, match="AMBIGUOUS"):
        actor.actions.invoke(ref)
    assert actor.backend.invoke.call_count == 1


@pytest.mark.parametrize("field,value", [("launch_mode", "guessed"), ("editor_newlines", "guess")])
def test_unknown_profile_modes_rejected(actor, field, value):
    with pytest.raises(ValueError):
        replace(actor.profile, **{field: value})


def test_owned_child_profile_requires_pinned_executable(actor):
    with pytest.raises(ValueError, match="pinned"):
        replace(actor.profile, launch_mode="owned_child")


def child_worker(actor):
    import hashlib

    profile = replace(
        actor.profile,
        launch_mode="owned_child",
        executable_sha256=hashlib.sha256(actor.profile.executable.read_bytes()).hexdigest(),
    )
    child = ProcessIdentity(22, 100, str(profile.executable))
    parent = ProcessIdentity(21, 99, str(profile.executable))
    backend = Mock()
    backend.launch.return_value = actor.process
    backend.identity.side_effect = lambda pid: parent if pid == 21 else child
    backend.owned_children.return_value = [child]
    lease = backend.track_owned_child.return_value
    lease.poll.return_value = None
    window = control(22, "Window", "main", "Qualified", (22, 1))
    backend.connect.return_value.windows.return_value = [window]
    return UIAWorker((profile,), _backend=backend), backend, child, lease


def test_child_lease_survives_launcher_exit_but_rejects_child_exit(actor):
    worker, backend, child, lease = child_worker(actor)
    with worker:
        app = worker.launch("qualified")
        backend.connect.assert_called_once_with(child.pid)
        actor.process.poll.return_value = 0
        assert worker._resolve_app(app).identity == child
        lease.poll.return_value = 0
        with pytest.raises(UIABlocked, match="REACQUIRE"):
            worker._resolve_app(app)
        lease.close.assert_called_once()
    backend.terminate_owned.assert_not_called()


def test_ambiguous_owned_children_block_without_connecting(actor):
    worker, backend, child, lease = child_worker(actor)
    backend.owned_children.return_value = [child, replace(child, pid=23)]
    with worker, pytest.raises(UIABlocked, match="OWNED_CHILD_AMBIGUOUS"):
        worker.launch("qualified")
    backend.connect.assert_not_called()
    backend.track_owned_child.assert_not_called()
    backend.terminate_owned.assert_called_once_with(actor.process)


def test_owned_children_reject_foreign_image_and_older_identity(actor):
    worker, backend, child, lease = child_worker(actor)
    backend.owned_children.return_value = [
        child,
        replace(child, executable="C:/foreign.exe"),
        replace(child, created=98),
    ]
    with worker:
        assert worker._owned_children(
            ProcessIdentity(21, 99, str(actor.profile.executable)), actor.profile.executable
        ) == [child]


def test_child_lease_closed_on_bind_failure(actor):
    worker, backend, child, lease = child_worker(actor)
    backend.connect.side_effect = RuntimeError("private")
    with worker, pytest.raises(UIABlocked, match="APPLICATION_BIND_FAILED"):
        worker.launch("qualified")
    lease.close.assert_called_once()
    backend.terminate_owned.assert_called_once_with(actor.process)


def test_native_child_handle_read_only_poll_and_idempotent_close():
    from victus.adapters.uia.native import OwnedChildHandle

    kernel = Mock()
    kernel.WaitForSingleObject.side_effect = [258, 0, 0xFFFFFFFF]
    lease = OwnedChildHandle(kernel, 1234, 22)
    assert lease.poll() is None
    assert lease.poll() == 0
    with pytest.raises(UIABlocked, match="LEASE_UNAVAILABLE"):
        lease.poll()
    lease.close()
    lease.close()
    kernel.CloseHandle.assert_called_once_with(1234)
    kernel.TerminateProcess.assert_not_called()


def test_installed_candidate_profile_remains_keyboard_disabled(tmp_path):
    from pathlib import Path

    from victus.adapters.uia.applications import load_profiles

    path = (
        Path(__file__).resolve().parents[2] / "config/applications/notepad-win11-11.2607.14.0.json"
    )
    # Inspect Windows path syntax without claiming the app is installed on Linux.
    import json
    from pathlib import PureWindowsPath

    document = json.loads(path.read_text())
    assert PureWindowsPath(document[0]["executable"]).is_absolute()
    document[0]["executable"] = str(tmp_path / "candidate.exe")
    portable = tmp_path / "candidate.json"
    portable.write_text(json.dumps(document))
    (profile,) = load_profiles(portable)
    assert profile.launch_mode == "owned_child"
    assert profile.executable_sha256 and profile.editor_newlines == "crlf"
    assert profile.window.class_name == "Notepad"
    assert profile.controls["filename"].automation_id == "FileNameControlHost"
    assert not profile.allow_keyboard_fallback


def test_launch_observations_never_adopt_observed_process(actor):
    worker, backend, child, lease = child_worker(actor)
    evidence = Mock()
    worker._diagnostics = evidence
    backend.launch_observations.return_value = [
        {"owned_pid": 999, "process_created": 1, "window_handle": 123},
    ]
    with worker:
        reference = worker.launch("qualified")
        assert worker._resolve_app(reference).identity == child
    backend.connect.assert_called_once_with(child.pid)
    assert backend.launch_observations.call_count == 3
    assert evidence.record.call_count == 4


def test_missing_diagnostics_cannot_weaken_owned_child_requirement(actor, monkeypatch):
    worker, backend, _, _ = child_worker(actor)
    worker._diagnostics = Mock()
    backend.launch_observations.side_effect = RuntimeError("PRIVATE")
    backend.owned_children.return_value = []
    ticks = iter([0, 10])
    monkeypatch.setattr("victus.adapters.uia.applications.time.monotonic", lambda: next(ticks))
    with worker, pytest.raises(UIABlocked, match="OWNED_CHILD_UNAVAILABLE"):
        worker.launch("qualified")
    backend.connect.assert_not_called()
    backend.terminate_owned.assert_called_once_with(actor.process)
    assert "PRIVATE" not in str(worker._diagnostics.record.call_args_list)


def tab_actor(actor):
    worker, backend, child, lease = child_worker(actor)
    profile = worker._profiles["qualified"]
    worker._profiles["qualified"] = replace(
        profile,
        controls={**profile.controls, "new_tab": ControlSelector("Button", automation_id="new")},
        new_editor_control="new_tab",
        tab_container=ControlSelector("List", automation_id="tabs"),
    )
    button = control(child.pid, "Button", "new", "Add New Tab", (22, 2))
    window = backend.connect.return_value.windows.return_value[0]
    window.descendants.return_value = [button]
    old, new = Mock(), Mock()
    old.is_selected.return_value = False
    new.is_selected.return_value = True
    inventory = [{(22, 3): old}]
    worker._editor_tabs = lambda _: ((22, 1), inventory[0])
    backend.invoke.side_effect = lambda _: inventory.__setitem__(0, {(22, 3): old, (22, 4): new})
    return worker, backend, lease, old, new, inventory


def test_new_editor_lease_preserves_old_tabs_and_rejects_changed_selection(actor):
    worker, backend, lease, old, new, inventory = tab_actor(actor)
    with worker:
        reference = worker.launch("qualified")
        assert worker._resolve_app(reference).editor_tab_identity == (22, 4)
        old.is_selected.return_value, new.is_selected.return_value = True, False
        with pytest.raises(UIABlocked, match="EDITOR_LEASE_CHANGED"):
            worker._resolve_app(reference)
    backend.terminate_owned.assert_not_called()
    backend.set_value.assert_not_called()


def test_new_editor_cannot_replace_or_remove_an_existing_tab(actor):
    worker, backend, lease, old, new, inventory = tab_actor(actor)
    backend.invoke.side_effect = lambda _: inventory.__setitem__(0, {(22, 4): new})
    with worker, pytest.raises(UIABlocked, match="NEW_EDITOR_IDENTITY_UNPROVED"):
        worker.launch("qualified")
    backend.set_value.assert_not_called()
    backend.terminate_owned.assert_not_called()
    lease.close.assert_called_once()


def test_stop_guard_prevents_owned_launch_before_native_effect(actor):
    worker, backend, _, _ = child_worker(actor)

    def stopped():
        raise PermissionError("Stopped")

    with worker:
        worker.set_operation_guard(stopped)
        with pytest.raises(PermissionError):
            worker.launch("qualified")
    backend.launch.assert_not_called()
    backend.set_value.assert_not_called()


def test_stop_after_add_tab_preserves_documents_and_releases_lease(actor):
    import threading

    worker, backend, lease, _, _, inventory = tab_actor(actor)
    stopped = threading.Event()
    add_tab = backend.invoke.side_effect

    def invoke(control):
        add_tab(control)
        stopped.set()

    def guard():
        if stopped.is_set():
            raise PermissionError("Stopped after new tab")

    backend.invoke.side_effect = invoke
    with worker:
        worker.set_operation_guard(guard)
        with pytest.raises(PermissionError):
            worker.launch("qualified")
    assert len(inventory[0]) == 2
    backend.set_value.assert_not_called()
    backend.terminate_owned.assert_not_called()
    lease.close.assert_called_once()
