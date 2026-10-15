"""Browser tool specifications.

Stubs for browser-automation tools that will be backed by Playwright adapters
in a later milestone.  Each function returns a ``ToolSpec`` whose execute and
verify callables raise ``NotImplementedError`` until the adapters are wired.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from victus.tools.registry import RetryClass, RiskLevel, ToolSpec


# ── argument models ──────────────────────────────────────────────────────

class NavigateArguments(BaseModel):
    """Arguments for opening a URL in a managed browser context."""

    model_config = ConfigDict(extra="forbid", strict=True)
    url: str = Field(min_length=1, max_length=2048)
    wait_until: str = Field(default="domcontentloaded", pattern=r"^(load|domcontentloaded|networkidle)$")


class ScreenshotArguments(BaseModel):
    """Arguments for capturing a visible-area screenshot."""

    model_config = ConfigDict(extra="forbid", strict=True)
    filename: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.(png|jpg)$")
    full_page: bool = False


# ── stub callables ───────────────────────────────────────────────────────

def _not_implemented_execute(workspace: Path, arguments: BaseModel) -> Path:
    raise NotImplementedError("Browser adapter not wired")


def _not_implemented_verify(target: Path, arguments: BaseModel) -> bool:
    raise NotImplementedError("Browser verifier not wired")


# ── tool specs ───────────────────────────────────────────────────────────

def browser_navigate() -> ToolSpec:
    """Navigate a managed browser to a URL."""
    return ToolSpec(
        name="browser.navigate",
        version="0.1.0",
        description="Open a URL in the managed Playwright browser context.",
        argument_model=NavigateArguments,
        risk_floor=RiskLevel.MEDIUM,
        required_scope="browser:navigate",
        timeout_seconds=30.0,
        resource_name="browser_context",
        retry_class=RetryClass.IDEMPOTENT,
        execute=_not_implemented_execute,
        verify=_not_implemented_verify,
    )


def browser_screenshot() -> ToolSpec:
    """Capture a screenshot of the current browser viewport."""
    return ToolSpec(
        name="browser.screenshot",
        version="0.1.0",
        description="Capture a PNG or JPG screenshot of the browser viewport.",
        argument_model=ScreenshotArguments,
        risk_floor=RiskLevel.LOW,
        required_scope="browser:read",
        timeout_seconds=10.0,
        resource_name="browser_context",
        retry_class=RetryClass.SAFE,
        execute=_not_implemented_execute,
        verify=_not_implemented_verify,
    )


BROWSER_TOOLS: list[ToolSpec] = [
    browser_navigate(),
    browser_screenshot(),
]
