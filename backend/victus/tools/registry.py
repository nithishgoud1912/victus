from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class RiskLevel(StrEnum):
    """Minimum risk classification that a tool must declare."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RetryClass(StrEnum):
    """Whether the runtime may safely retry a failed invocation."""

    NONE = "none"            # Never retry — side-effects are unpredictable.
    IDEMPOTENT = "idempotent"  # Safe to retry; repeated calls produce the same result.
    SAFE = "safe"            # Retry is safe but the output may differ across attempts.


@dataclass(frozen=True)
class ToolSpec:
    """Declarative metadata plus execute/verify callables for a single tool.

    ``argument_model`` is the Pydantic model that validates raw arguments before
    they reach ``execute``.  The dispatcher instantiates it so that tools never
    receive unvalidated dicts.

    ``execute`` receives the workspace root and a *validated* argument instance
    (a subclass of ``BaseModel``).  It returns the ``Path`` of the artefact it
    produced.

    ``verify`` receives the output path and the same argument instance.  It
    returns ``True`` only when the artefact satisfies the tool's postcondition.
    """

    # ── identity ──────────────────────────────────────────────────────────
    name: str
    version: str
    description: str

    # ── argument schema ───────────────────────────────────────────────────
    argument_model: type[BaseModel]

    # ── policy & scheduling metadata ──────────────────────────────────────
    risk_floor: RiskLevel
    required_scope: str
    timeout_seconds: float
    resource_name: str
    retry_class: RetryClass

    # ── callables ─────────────────────────────────────────────────────────
    execute: Callable[[Path, Any], Path]
    verify: Callable[[Path, Any], bool]


class ToolRegistry:
    """Thread-safe, append-only registry of ``ToolSpec`` instances."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError("Duplicate tool registration")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise ValueError("Unregistered tool")
        return self._tools[name]

    def names(self) -> list[str]:
        """Return a sorted list of registered tool names."""
        return sorted(self._tools)

    def tools(self) -> list[ToolSpec]:
        """Return all registered specs, sorted by name."""
        return [self._tools[n] for n in sorted(self._tools)]