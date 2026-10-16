"""Checkpointable references and finite task budgets, never live adapter objects."""

from __future__ import annotations

import time
from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from victus.agent.budgets import Budgets, BudgetState
from victus.agent.progress import ProgressState

Status = Literal[
    "queued",
    "running",
    "awaiting_approval",
    "succeeded",
    "blocked",
    "failed",
    "cancelled",
    "unknown",
    "partial",
]
Node = Literal[
    "intake",
    "route",
    "observe",
    "propose",
    "validate",
    "authorize",
    "review",
    "execute",
    "verify",
    "failed",
    "recover",
    "finalize",
    "end",
]


class ProposalReference(TypedDict):
    payload_ref: str
    kind: Literal["action", "finish"]


class AgentState(TypedDict):
    task_id: str
    goal_payload_ref: str
    status: Status
    observation_refs: list[str]
    action_ledger_refs: list[str]
    current_proposal: ProposalReference | None
    approval_ref: str | None
    evidence_refs: list[str]
    error_history: list[dict[str, str]]
    error_code: str | None
    remaining: BudgetState
    cancellation_requested: bool
    sequence: int
    next_node: Node
    route_name: str | None
    route_ref: str | None
    execution_status: str | None
    completion_verified: bool
    progress: dict


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class Proposal(_Strict):
    payload_ref: str = Field(pattern=r"^[a-f0-9]{32}$")
    kind: Literal["action", "finish"]


class Snapshot(_Strict):
    task_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    goal_payload_ref: str = Field(pattern=r"^[a-f0-9]{32}$")
    status: Status
    observation_refs: list[str] = Field(max_length=64)
    action_ledger_refs: list[str] = Field(max_length=32)
    current_proposal: Proposal | None
    approval_ref: str | None
    evidence_refs: list[str] = Field(max_length=64)
    error_history: list[dict[str, str]] = Field(max_length=16)
    error_code: str | None
    remaining: Budgets
    cancellation_requested: bool
    sequence: int = Field(ge=0, le=512)
    next_node: Node
    route_name: str | None
    route_ref: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    execution_status: str | None
    completion_verified: bool
    progress: ProgressState = Field(default_factory=ProgressState)


def initial_state(
    task_id: str, goal_payload_ref: str, budgets: Budgets | None = None
) -> AgentState:
    if (
        budgets is not None
        and budgets.deadline_epoch is not None
        and budgets.deadline_epoch > time.time() + 600
    ):
        raise ValueError("Task deadline exceeds ten minutes")
    return Snapshot(
        task_id=task_id,
        goal_payload_ref=goal_payload_ref,
        status="queued",
        observation_refs=[],
        action_ledger_refs=[],
        current_proposal=None,
        approval_ref=None,
        evidence_refs=[],
        error_history=[],
        error_code=None,
        remaining=budgets or Budgets(),
        cancellation_requested=False,
        sequence=0,
        next_node="intake",
        route_name=None,
        execution_status=None,
        completion_verified=False,
    ).model_dump()
