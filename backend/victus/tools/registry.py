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

    NONE = "none"  # Never retry — side-effects are unpredictable.
    IDEMPOTENT = "idempotent"  # Safe to retry; repeated calls produce the same result.
    SAFE = "safe"  # Retry is safe but the output may differ across attempts.


@dataclass(frozen=True)
class ToolSpec:
    """Declarative metadata plus execute/verify callables for a single tool.

    ``argument_model`` is the Pydantic model that validates raw arguments before
    they reach ``execute``.  The dispatcher instantiates it so that tools never
    receive unvalidated dicts.

    ``execute`` receives the workspace root and a *validated* argument instance
    (a subclass of ``BaseModel``). Supervised outer tools return an artifact
    ``Path``; worker-local workflow steps return bounded JSON dictionaries.

    ``verify`` receives the output and the same argument instance. It returns
    ``True`` only when an independent read proves the postcondition. Workflow
    execute/verify handlers may be async; UIA handlers stay on their owner thread.
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
    execute: Callable[[Path, Any], Any]
    verify: Callable[[Any, Any], Any]
    # Optional cooperative variant receives a multiprocessing Event. It must
    # check the signal before each effect; the supervisor still enforces time.
    execute_cancellable: Callable[[Path, Any, Any], Path] | None = None
    # Optional trusted policy for supervised qualification/workflow entry points.
    # These are not registered by the public API/bootstrap by default.
    policy: Callable[[Path, BaseModel], None] | None = None
    # Fail closed until a reviewed adapter explicitly declares a read-only tool.
    external_write: bool = True
    # Trusted worker identity is supplied by Dispatcher, never request arguments.
    execute_owned: Callable | None = None
    public: bool = True


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

    def validate(self, request):
        """Revalidate even model_construct/mutated Python objects at the boundary."""
        from victus.tools.contracts import ActionProposal

        if isinstance(request, BaseModel) and set(request.__dict__) - set(
            type(request).model_fields
        ):
            raise ValueError("Unexpected request attributes")
        raw = request.model_dump(warnings="error") if isinstance(request, BaseModel) else request
        if isinstance(raw, dict) and isinstance(raw.get("arguments"), BaseModel):
            raw = {**raw, "arguments": raw["arguments"].model_dump(warnings="error")}
        proposal = ActionProposal.model_validate(raw, strict=True)
        tool = self.get(proposal.tool)
        # Every production argument model is closed; registry additions must be too.
        if tool.argument_model.model_config.get("extra") != "forbid":
            raise ValueError("Tool argument schema must forbid extra fields")
        arguments = tool.argument_model.model_validate(proposal.arguments, strict=True)
        return proposal, tool, arguments

    def names(self) -> list[str]:
        """Return a sorted list of registered tool names."""
        return sorted(self._tools)

    def tools(self) -> list[ToolSpec]:
        """Return all registered specs, sorted by name."""
        return [self._tools[n] for n in sorted(self._tools)]
