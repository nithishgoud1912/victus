"""Desktop (Windows UI Automation) tool specifications.

Stubs for desktop-automation tools that will be backed by pywinauto / UIA
adapters in a later milestone.  Each function returns a ``ToolSpec`` whose
execute and verify callables raise ``NotImplementedError`` until the adapters
are wired.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from victus.tools.registry import RetryClass, RiskLevel, ToolSpec


# ── argument models ──────────────────────────────────────────────────────

class ListWindowsArguments(BaseModel):
    """Arguments for enumerating visible top-level windows."""

    model_config = ConfigDict(extra="forbid", strict=True)
    backend: str = Field(default="uia", pattern=r"^(uia|win32)$")


class ClickElementArguments(BaseModel):
    """Arguments for clicking a desktop UI element by automation ID or name."""

    model_config = ConfigDict(extra="forbid", strict=True)
    window_title: str = Field(min_length=1, max_length=256)
    auto_id: str | None = Field(default=None, max_length=256)
    name: str | None = Field(default=None, max_length=256)
    control_type: str = Field(default="Button", max_length=64)


class TypeTextArguments(BaseModel):
    """Arguments for typing text into a focused desktop control."""

    model_config = ConfigDict(extra="forbid", strict=True)
    window_title: str = Field(min_length=1, max_length=256)
    text: str = Field(min_length=1, max_length=4096)
    auto_id: str | None = Field(default=None, max_length=256)


# ── stub callables ───────────────────────────────────────────────────────

def _not_implemented_execute(workspace: Path, arguments: BaseModel) -> Path:
    raise NotImplementedError("Desktop adapter not wired")


def _not_implemented_verify(target: Path, arguments: BaseModel) -> bool:
    raise NotImplementedError("Desktop verifier not wired")


# ── tool specs ───────────────────────────────────────────────────────────

def desktop_list_windows() -> ToolSpec:
    """List visible top-level windows via UIA or Win32."""
    return ToolSpec(
        name="desktop.list_windows",
        version="0.1.0",
        description="Enumerate visible top-level desktop windows and their process IDs.",
        argument_model=ListWindowsArguments,
        risk_floor=RiskLevel.LOW,
        required_scope="desktop:read",
        timeout_seconds=5.0,
        resource_name="desktop_uia",
        retry_class=RetryClass.SAFE,
        execute=_not_implemented_execute,
        verify=_not_implemented_verify,
    )


def desktop_click_element() -> ToolSpec:
    """Click a desktop UI element by automation ID or name."""
    return ToolSpec(
        name="desktop.click_element",
        version="0.1.0",
        description="Click a UI Automation element identified by window title and auto-ID or name.",
        argument_model=ClickElementArguments,
        risk_floor=RiskLevel.HIGH,
        required_scope="desktop:interact",
        timeout_seconds=10.0,
        resource_name="desktop_uia",
        retry_class=RetryClass.NONE,
        execute=_not_implemented_execute,
        verify=_not_implemented_verify,
    )


def desktop_type_text() -> ToolSpec:
    """Type text into a focused desktop control."""
    return ToolSpec(
        name="desktop.type_text",
        version="0.1.0",
        description="Send keystrokes to a desktop control identified by window title and auto-ID.",
        argument_model=TypeTextArguments,
        risk_floor=RiskLevel.HIGH,
        required_scope="desktop:interact",
        timeout_seconds=10.0,
        resource_name="desktop_uia",
        retry_class=RetryClass.NONE,
        execute=_not_implemented_execute,
        verify=_not_implemented_verify,
    )


DESKTOP_TOOLS: list[ToolSpec] = [
    desktop_list_windows(),
    desktop_click_element(),
    desktop_type_text(),
]
