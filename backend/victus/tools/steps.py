"""Trusted worker-local context for non-file workflow steps."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from victus.storage.action_ledger import ActionLedger
from victus.storage.payloads import PayloadStore
from victus.tasks.events import EventManager
from victus.tools.registry import ToolSpec


@dataclass(frozen=True)
class StepOutcome:
    status: str
    action_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None

    @property
    def verified(self):
        return self.status == "succeeded"


@dataclass
class StepContext:
    task_id: str
    scopes: frozenset[str]
    authorize: Callable[[ToolSpec, BaseModel], bool]
    ledger: ActionLedger
    payloads: PayloadStore
    events: EventManager
    cancelled: Any
    remaining_steps: int = 64
    deadline: float = field(default_factory=lambda: time.monotonic() + 180)
    trace: list[dict] = field(default_factory=list)
    prepared_action_id: str | None = None
    permits: Any = None
    permit_token: str | None = None
    approval_binding: Any = None
    revalidate_binding: Any = None

    def stopped(self):
        return self.cancelled is not None and self.cancelled.is_set()
