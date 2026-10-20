"""Allowlisted application profiles and single-thread COM/process ownership."""

from __future__ import annotations

import hashlib
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from uuid import uuid4


class UIABlocked(RuntimeError):
    """Deterministic safe failure; never include private control contents."""


class UIAUncertain(RuntimeError):
    """A native action was attempted; inspect state instead of blindly retrying."""


@dataclass(frozen=True)
class ControlSelector:
    control_type: str
    automation_id: str | None = None
    name: str | None = None
    root_window: str = "main"
    class_name: str | None = None

    def __post_init__(self):
        if not self.control_type or not any((self.automation_id, self.name, self.class_name)):
            raise ValueError("Selectors require control type and an exact ID or name")


@dataclass(frozen=True)
class ApplicationProfile:
    name: str
    executable: Path
    window: ControlSelector
    controls: dict[str, ControlSelector]
    arguments: tuple[str, ...] = ()
    executable_sha256: str | None = None
    allow_keyboard_fallback: bool = False
    windows: dict[str, ControlSelector] = field(default_factory=dict)
    launch_mode: str = "direct"
    editor_newlines: str = "exact"
    focus_before_patterns: bool = False
    new_editor_control: str | None = None
    tab_container: ControlSelector | None = None

    def __post_init__(self):
        if not self.name or not self.executable.is_absolute() or not self.controls:
            raise ValueError("Profiles require an absolute executable and named controls")
        if self.executable.suffix.lower() != ".exe":
            raise ValueError("Only allowlisted Windows executables can be launched")
        if self.launch_mode not in {"direct", "owned_child"}:
            raise ValueError("Unsupported launch mode")
        if self.editor_newlines not in {"exact", "crlf"}:
            raise ValueError("Unsupported editor newline mode")
        if self.launch_mode == "owned_child" and self.executable_sha256 is None:
            raise ValueError("Owned-child routes require a pinned executable hash")
        if bool(self.new_editor_control) != bool(self.tab_container):
            raise ValueError("New editor requires both an explicit control and tab container")
        if self.new_editor_control and (
            self.new_editor_control not in self.controls or self.launch_mode != "owned_child"
        ):
            raise ValueError("New editor requires an owned child and an allowlisted control")
        object.__setattr__(self, "controls", MappingProxyType(dict(self.controls)))
        object.__setattr__(self, "windows", MappingProxyType(dict(self.windows)))
        object.__setattr__(self, "arguments", tuple(self.arguments))


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    created: int
    executable: str


@dataclass(frozen=True)
class ApplicationReference:
    ref: str


@dataclass
class _Application:
    profile: ApplicationProfile
    identity: ProcessIdentity
    process: object
    connection: object
    launcher_identity: ProcessIdentity | None = None
    editor_tab_identity: tuple | None = None
    editor_window_identity: tuple | None = None


class UIAWorker:
    """Construct/use in one supervised worker. No live objects leave this actor."""

    def __init__(
        self, profiles: tuple[ApplicationProfile, ...], *, _backend=None, diagnostics=None
    ):
        self._profiles = {profile.name: profile for profile in profiles}
        if len(self._profiles) != len(profiles):
            raise ValueError("Duplicate application profiles")
        self._backend = _backend
        self._owner = None
        self._started = False
        self._applications = {}
        self._controls = {}
        self._diagnostics = diagnostics
        self._operation_guard = None

    def _observe_launch(self, phase, executable, launcher=None):
        """Private observation only: it cannot supply an application reference."""
        if self._diagnostics is None:
            return
        try:
            if launcher is not None:
                self._diagnostics.record(
                    "ownership.launcher",
                    "returned",
                    metadata={"owned_pid": launcher.pid, "process_created": launcher.created},
                )
            for observation in self._backend.launch_observations(executable):
                self._diagnostics.record(phase, "returned", metadata=observation)
        except Exception:
            # Observation failure never changes the ownership decision or hides its error.
            self._diagnostics.record(phase, "error", error_code="OBSERVATION_UNAVAILABLE")

    def __getstate__(self):
        raise TypeError("UIA worker and handles cannot cross process boundaries")

    def _check_owner(self):
        if not self._started or self._owner != (os.getpid(), threading.get_ident()):
            raise UIABlocked("UIA_WORKER_NOT_STARTED_OR_FOREIGN")

    def set_operation_guard(self, guard):
        """Worker-local Stop/deadline callback; never a transport field."""
        self._check_owner()
        self._operation_guard = guard

    def _check_operation(self):
        self._check_owner()
        if self._operation_guard is not None:
            self._operation_guard()

    def start(self):
        owner = (os.getpid(), threading.get_ident())
        if self._owner is not None and self._owner != owner:
            raise UIABlocked("UIA_WORKER_FOREIGN")
        if self._started:
            return
        if self._backend is None:
            from victus.adapters.uia.native import WindowsBackend

            self._backend = WindowsBackend()
        self._backend.initialize()
        self._owner = owner
        self._started = True

    def launch(self, profile_name: str) -> ApplicationReference:
        self._check_operation()
        if len(self._applications) >= 32:
            raise UIABlocked("APPLICATION_LIMIT")
        profile = self._profiles.get(profile_name)
        if profile is None:
            raise UIABlocked("APPLICATION_NOT_ALLOWLISTED")
        path = profile.executable
        if path.is_symlink() or not path.is_file():
            raise UIABlocked("EXECUTABLE_UNAVAILABLE")
        resolved = path.resolve(strict=True)
        if profile.executable_sha256 is not None:
            if hashlib.sha256(resolved.read_bytes()).hexdigest() != profile.executable_sha256:
                raise UIABlocked("EXECUTABLE_CHANGED")
        self._observe_launch("ownership.before", resolved)
        try:
            self._check_operation()
            process = self._backend.launch(resolved, profile.arguments)
        except Exception:
            raise UIABlocked("APPLICATION_LAUNCH_FAILED") from None
        owned_process = process
        try:
            identity = self._backend.identity(process.pid)
            if os.path.normcase(identity.executable) != os.path.normcase(str(resolved)):
                raise UIABlocked("PROCESS_IMAGE_MISMATCH")
            self._observe_launch("ownership.launched", resolved, identity)
            launcher_identity = None
            if profile.launch_mode == "owned_child":
                launcher_identity = identity
                deadline = time.monotonic() + 5
                while True:
                    self._check_operation()
                    if process.poll() is not None:
                        raise UIABlocked("LAUNCHER_EXITED")
                    children = self._owned_children(launcher_identity, resolved)
                    if len(children) > 1:
                        raise UIABlocked("OWNED_CHILD_AMBIGUOUS")
                    if children:
                        identity = children[0]
                        owned_process = self._backend.track_owned_child(launcher_identity, identity)
                        break
                    if time.monotonic() >= deadline:
                        raise UIABlocked("OWNED_CHILD_UNAVAILABLE")
                    time.sleep(0.05)
            connection = self._backend.connect(identity.pid)
            if profile.launch_mode == "owned_child":
                from victus.adapters.uia.selectors import _matches

                deadline = time.monotonic() + 5
                while True:
                    self._check_operation()
                    windows = [
                        w for w in connection.windows() if _matches(w, profile.window, identity.pid)
                    ]
                    if len(windows) > 1:
                        raise UIABlocked("WINDOW_MISSING_OR_AMBIGUOUS")
                    if len(windows) == 1 and windows[0].is_visible():
                        break
                    if owned_process.poll() is not None or time.monotonic() >= deadline:
                        raise UIABlocked("OWNED_WINDOW_UNAVAILABLE")
                    time.sleep(0.05)
        except BaseException as error:
            self._observe_launch("ownership.blocked", resolved)
            if owned_process is not process:
                owned_process.close()
            # This Popen handle owns only the process just launched, never a guessed PID.
            self._backend.terminate_owned(process)
            if isinstance(error, UIABlocked):
                raise
            raise UIABlocked("APPLICATION_BIND_FAILED") from None
        ref = uuid4().hex
        self._observe_launch("ownership.bound", resolved)
        self._applications[ref] = _Application(
            profile, identity, owned_process, connection, launcher_identity
        )
        reference = ApplicationReference(ref)
        if profile.new_editor_control:
            try:
                self._create_empty_editor(reference)
            except BaseException:
                # Never terminate an editor/process containing restored documents.
                self._applications.pop(ref).process.close()
                raise
        return reference

    def _editor_tabs(self, app):
        from victus.adapters.uia.selectors import _matches

        windows = [
            w for w in app.connection.windows() if _matches(w, app.profile.window, app.identity.pid)
        ]
        if len(windows) != 1:
            raise UIABlocked("EDITOR_WINDOW_AMBIGUOUS")
        root = windows[0]
        containers = [
            c
            for c in root.descendants(control_type=app.profile.tab_container.control_type)
            if _matches(c, app.profile.tab_container, app.identity.pid)
        ]
        if len(containers) != 1:
            raise UIABlocked("EDITOR_TAB_CONTAINER_AMBIGUOUS")
        tabs = containers[0].descendants(control_type="TabItem")
        if any(t.element_info.process_id != app.identity.pid for t in tabs):
            raise UIABlocked("EDITOR_TAB_FOREIGN_PROCESS")
        identities = {tuple(t.element_info.runtime_id): t for t in tabs}
        if (
            len(identities) != len(tabs)
            or len(tabs) > 64
            or any(not identity for identity in identities)
        ):
            raise UIABlocked("EDITOR_TAB_INVENTORY_AMBIGUOUS")
        return tuple(root.element_info.runtime_id), identities

    @staticmethod
    def _tab_selected(tab):
        # The Windows COM binding may expose UIA BOOL as an integer.
        value = tab.is_selected()
        return type(value) in {bool, int} and value == 1

    def _create_empty_editor(self, reference):
        from victus.adapters.uia.actions import UIAActions
        from victus.adapters.uia.selectors import SelectorResolver

        app = self._resolve_app(reference)
        root_id, before = self._editor_tabs(app)
        resolver = SelectorResolver(self)
        control = resolver.resolve(reference, app.profile.new_editor_control)
        self._check_operation()
        UIAActions(resolver).invoke(
            control, allow_keyboard=False, before_invoke=self._check_operation
        )
        deadline = time.monotonic() + 5
        while True:
            self._check_operation()
            if (
                app.process.poll() is not None
                or self._backend.identity(app.identity.pid) != app.identity
            ):
                raise UIABlocked("APPLICATION_RESTARTED_REACQUIRE")
            current_root, after = self._editor_tabs(app)
            new = after.keys() - before.keys()
            if current_root != root_id or not before.keys() <= after.keys() or len(new) > 1:
                raise UIABlocked("NEW_EDITOR_IDENTITY_UNPROVED")
            if len(new) == 1:
                tab_id = next(iter(new))
                selected = [key for key, tab in after.items() if self._tab_selected(tab)]
                if selected != [tab_id]:
                    if time.monotonic() >= deadline:
                        raise UIABlocked("NEW_EDITOR_SELECTION_UNPROVED")
                    time.sleep(0.05)
                    continue
                app.editor_tab_identity, app.editor_window_identity = tab_id, root_id
                # A new tab is still not proof of an empty editor. The next
                # dispatcher-routed inspection must establish that before input.
                self._check_operation()
                return
            if time.monotonic() >= deadline:
                raise UIABlocked("NEW_EDITOR_UNAVAILABLE")
            time.sleep(0.05)

    def _owned_children(self, parent, executable):
        return [
            child
            for child in self._backend.owned_children(parent)
            if child.created >= parent.created
            and os.path.normcase(child.executable) == os.path.normcase(str(executable))
        ]

    def _resolve_app(self, reference: ApplicationReference) -> _Application:
        self._check_owner()
        app = self._applications.get(reference.ref)
        if app is None:
            raise UIABlocked("APPLICATION_REFERENCE_UNKNOWN")
        try:
            if (
                app.process.poll() is not None
                or self._backend.identity(app.identity.pid) != app.identity
            ):
                raise UIABlocked("APPLICATION_RESTARTED_REACQUIRE")
            if app.editor_tab_identity is not None:
                root_id, tabs = self._editor_tabs(app)
                selected = [key for key, tab in tabs.items() if self._tab_selected(tab)]
                if root_id != app.editor_window_identity or selected != [app.editor_tab_identity]:
                    raise UIABlocked("EDITOR_LEASE_CHANGED")
        except UIABlocked as error:
            if str(error) == "EDITOR_LEASE_CHANGED":
                raise
            self._applications.pop(reference.ref, None)
            if app.launcher_identity is not None:
                app.process.close()
            raise UIABlocked("APPLICATION_RESTARTED_REACQUIRE") from None
        except Exception:
            self._applications.pop(reference.ref, None)
            if app.launcher_identity is not None:
                app.process.close()
            raise UIABlocked("APPLICATION_RESTARTED_REACQUIRE") from None
        return app

    def close(self):
        if not self._started:
            return
        self._check_owner()
        self._controls.clear()
        for app in self._applications.values():
            if app.launcher_identity is not None:
                app.process.close()
        self._applications.clear()
        self._operation_guard = None
        self._started = False
        self._backend.uninitialize()
        # Deliberately leave launched applications open; COM shutdown is not permission
        # to terminate applications containing the user's unsaved work.

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.close()


def load_profiles(path: Path) -> tuple[ApplicationProfile, ...]:
    """Read trusted JSON configuration inside the UIA worker, never model output."""
    from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

    class SelectorConfig(BaseModel):
        model_config = ConfigDict(extra="forbid", strict=True)
        control_type: str
        automation_id: str | None = None
        name: str | None = None
        root_window: str = "main"
        class_name: str | None = None

    class ProfileConfig(BaseModel):
        model_config = ConfigDict(extra="forbid", strict=True)
        name: str
        executable: str
        window: SelectorConfig
        controls: dict[str, SelectorConfig]
        arguments: list[str] = Field(default_factory=list)
        executable_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
        allow_keyboard_fallback: bool = False
        windows: dict[str, SelectorConfig] = Field(default_factory=dict)
        launch_mode: str = "direct"
        editor_newlines: str = "exact"
        focus_before_patterns: bool = False
        new_editor_control: str | None = None
        tab_container: SelectorConfig | None = None

    configs = TypeAdapter(list[ProfileConfig]).validate_json(path.read_text(encoding="utf-8"))
    return tuple(
        ApplicationProfile(
            name=config.name,
            executable=Path(config.executable),
            window=ControlSelector(**config.window.model_dump()),
            controls={
                key: ControlSelector(**value.model_dump()) for key, value in config.controls.items()
            },
            arguments=tuple(config.arguments),
            executable_sha256=config.executable_sha256,
            allow_keyboard_fallback=config.allow_keyboard_fallback,
            windows={
                key: ControlSelector(**value.model_dump()) for key, value in config.windows.items()
            },
            launch_mode=config.launch_mode,
            editor_newlines=config.editor_newlines,
            focus_before_patterns=config.focus_before_patterns,
            new_editor_control=config.new_editor_control,
            tab_container=ControlSelector(**config.tab_container.model_dump())
            if config.tab_container
            else None,
        )
        for config in configs
    )
