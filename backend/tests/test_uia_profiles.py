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
