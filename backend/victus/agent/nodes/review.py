"""Replayable review boundary: no writes or tool calls before interrupt."""

import time

from langgraph.types import interrupt

from victus.agent.budgets import resume_approval, seconds_left, stopped_status


async def run(state, services):
    # Resume data is a wake-up signal only. It cannot grant approval or change
    # the saved action; the authenticated resolution route owns the decision.
    interrupt({"approval_id": state["approval_ref"], "task_id": state["task_id"]})
    left, valid = resume_approval(state["remaining"])
    cancelled = services.store.cancelled(state["task_id"]) or (
        services.cancelled is not None and services.cancelled.is_set()
    )
    record = services.approvals(state).get(state["approval_ref"])
    code = None
    if cancelled:
        code = "AGENT_CANCELLED"
    elif not valid or record is None or record.expires_at <= time.time():
        code = "APPROVAL_WAIT_EXPIRED"
    elif seconds_left(left) <= 0:
        code = "AGENT_BUDGET_EXHAUSTED"
    elif record.state != "approved":
        code = "APPROVAL_" + record.state.upper()
    if code:
        if record is not None:
            services.approvals(state).invalidate(record.approval_id)
        return {
            "status": "cancelled" if cancelled else stopped_status(state),
            "error_code": code,
            "next_node": "finalize",
            "sequence": state["sequence"] + 1,
            "cancellation_requested": cancelled,
        }
    return {
        "status": "running",
        "next_node": "execute",
        "sequence": state["sequence"] + 1,
        "remaining": {**left, "approval_started_epoch": None, "approval_expires_epoch": None},
    }
