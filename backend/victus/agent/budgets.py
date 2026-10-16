"""Checkpointable task allowances. Approval waiting is not active work."""

from __future__ import annotations

import time
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field


class BudgetState(TypedDict):
    nodes: int
    actions: int
    observations: int
    model_requests: int
    output_tokens: int
    schema_repairs: int
    recoveries: int
    active_seconds: float
    deadline_epoch: float | None
    recursion_limit: int
    repairs_used: int
    approval_timeout_seconds: float
    approval_started_epoch: float | None
    approval_expires_epoch: float | None


class Budgets(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    nodes: int = Field(default=96, ge=0, le=256)
    actions: int = Field(default=12, ge=0, le=32)
    observations: int = Field(default=16, ge=0, le=64)
    model_requests: int = Field(default=8, ge=0, le=32)
    output_tokens: int = Field(default=4096, ge=0, le=65536)
    # Allowance PER decision, not a task-wide repair pool.
    schema_repairs: int = Field(default=1, ge=0, le=1)
    repairs_used: int = Field(default=0, ge=0, le=32)
    recoveries: int = Field(default=2, ge=0, le=8)
    active_seconds: float = Field(default=180.0, ge=0, le=600, allow_inf_nan=False)
    # Retain the earlier optional deadline input/checkpoints. Pause it on approval.
    deadline_epoch: float | None = Field(default=None, allow_inf_nan=False)
    recursion_limit: int = Field(default=80, ge=1, le=256)
    approval_timeout_seconds: float = Field(default=60.0, gt=0, le=300, allow_inf_nan=False)
    approval_started_epoch: float | None = Field(default=None, allow_inf_nan=False)
    approval_expires_epoch: float | None = Field(default=None, allow_inf_nan=False)


def seconds_left(left: dict, *, now: float | None = None) -> float:
    seconds = left["active_seconds"]
    if left["deadline_epoch"] is not None:
        seconds = min(seconds, left["deadline_epoch"] - (time.time() if now is None else now))
    return max(0.0, seconds)


def charge_time(left: dict, elapsed: float) -> dict:
    return {**left, "active_seconds": max(0.0, left["active_seconds"] - max(0.0, elapsed))}


def charge_planning(left: dict, requests: int, tokens: int, repairs: int) -> dict:
    return {
        **left,
        "model_requests": max(0, left["model_requests"] - requests),
        "output_tokens": max(0, left["output_tokens"] - tokens),
        "repairs_used": left["repairs_used"] + repairs,
    }


def pause_for_approval(left: dict, *, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    # Repeated polling must not renew the original wait's expiry.
    if left["approval_started_epoch"] is not None:
        return dict(left)
    return {
        **left,
        "approval_started_epoch": now,
        "approval_expires_epoch": now + left["approval_timeout_seconds"],
    }


def resume_approval(left: dict, *, now: float | None = None) -> tuple[dict, bool]:
    now = time.time() if now is None else now
    start, expiry = left["approval_started_epoch"], left["approval_expires_epoch"]
    if start is None or expiry is None or now < start or now >= expiry:
        return dict(left), False
    # Keep the original expiry across polling/resume cycles. Only the start of
    # the next waiting interval advances, so a legacy deadline is shifted once.
    updated = {**left, "approval_started_epoch": now}
    if updated["deadline_epoch"] is not None:
        updated["deadline_epoch"] += now - start
    return updated, True


def stopped_status(state: dict, *, partial: bool = False) -> str:
    if state["status"] == "unknown" or state["execution_status"] == "unknown":
        return "unknown"
    return (
        "partial"
        if partial or (state["evidence_refs"] and state["action_ledger_refs"])
        else "blocked"
    )
