"""The only action invocation: the existing shared dispatcher."""


async def run(state, services):
    action, context = await services.execution(state)
    outcome = await services.dispatcher.dispatch_step(action, context)
    references = [*state["action_ledger_refs"]]
    if outcome.action_id:
        references.append(outcome.action_id)
    return {
        "action_ledger_refs": references,
        "execution_status": outcome.status,
        "error_code": outcome.error_code,
        "remaining": {**state["remaining"], "actions": state["remaining"]["actions"] - 1},
        "next_node": "verify" if outcome.action_id else "failed",
    }
