"""The only action invocation: the existing shared dispatcher."""


async def run(state, services):
    try:
        action, context = await services.execution(state)
    except (PermissionError, ValueError):
        store = services.approvals(state)
        record = store.get(state["approval_ref"])
        if record is not None:
            store.invalidate(record.approval_id)
            ledger = services.context_factory(state).ledger
            attempt = ledger.get(record.action_id)
            if attempt is not None and attempt.status == "prepared":
                ledger.mark_failed(record.action_id, error_code="APPROVAL_OR_TARGET_STALE")
        return {
            "status": "blocked",
            "execution_status": "blocked",
            "error_code": "APPROVAL_OR_TARGET_STALE",
            "next_node": "finalize",
        }
    outcome = await services.dispatcher.dispatch_step(action, context)
    references = [*state["action_ledger_refs"]]
    if outcome.action_id:
        references.append(outcome.action_id)
    status = {"blocked": "blocked", "cancelled": "cancelled", "unknown": "unknown"}.get(
        outcome.status, state["status"]
    )
    next_node = "verify" if outcome.action_id else "failed"
    if outcome.status in {"blocked", "cancelled"}:
        next_node = "finalize"
    return {
        "status": status,
        "action_ledger_refs": references,
        "execution_status": outcome.status,
        "error_code": outcome.error_code,
        "remaining": {**state["remaining"], "actions": state["remaining"]["actions"] - 1},
        "next_node": next_node,
    }
