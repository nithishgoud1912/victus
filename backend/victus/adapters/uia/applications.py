"""Allowlisted application profiles and single-thread COM/process ownership."""

from __future__ import annotations

import hashlib
import os
import threading
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

    def __post_init__(self):
        if not self.control_type or (self.automation_id is None and self.name is None):
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

    def __post_init__(self):
        if not self.name or not self.executable.is_absolute() or not self.controls:
            raise ValueError("Profiles require an absolute executable and named controls")
        if self.executable.suffix.lower() != ".exe":
            raise ValueError("Only allowlisted Windows executables can be launched")
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


class UIAWorker:
    """Construct/use in one supervised worker. No live objects leave this actor."""

    def __init__(self, profiles: tuple[ApplicationProfile, ...], *, _backend=None):
        self._profiles = {profile.name: profile for profile in profiles}
        if len(self._profiles) != len(profiles):
            raise ValueError("Duplicate application profiles")
        self._backend = _backend
        self._owner = None
        self._started = False
        self._applications = {}
        self._controls = {}

    def __getstate__(self):
        raise TypeError("UIA worker and handles cannot cross process boundaries")

    def _check_owner(self):
        if not self._started or self._owner != (os.getpid(), threading.get_ident()):
            raise UIABlocked("UIA_WORKER_NOT_STARTED_OR_FOREIGN")

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
        self._check_owner()
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
        try:
            process = self._backend.launch(resolved, profile.arguments)
        except Exception:
            raise UIABlocked("APPLICATION_LAUNCH_FAILED") from None
        try:
            identity = self._backend.identity(process.pid)
            if os.path.normcase(identity.executable) != os.path.normcase(str(resolved)):
                raise UIABlocked("PROCESS_IMAGE_MISMATCH")
            connection = self._backend.connect(identity.pid)
        except BaseException:
            # This Popen handle owns only the process just launched, never a guessed PID.
            self._backend.terminate_owned(process)
            raise UIABlocked("APPLICATION_BIND_FAILED") from None
        ref = uuid4().hex
        self._applications[ref] = _Application(profile, identity, process, connection)
        return ApplicationReference(ref)

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
        except Exception:
            self._applications.pop(reference.ref, None)
            raise UIABlocked("APPLICATION_RESTARTED_REACQUIRE") from None
        return app

    def close(self):
        if not self._started:
            return
        self._check_owner()
        self._controls.clear()
        self._applications.clear()
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
        )
        for config in configs
    )
