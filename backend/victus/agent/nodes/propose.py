from victus.agent.budgets import charge_planning, stopped_status
from victus.agent.progress import assess


async def run(state, services):
    proposal, used = await services.propose(state)
    left = state["remaining"]
    decision = services.store.payload(state["task_id"], "proposal", proposal["payload_ref"])
    observation = services.store.payload(
        state["task_id"], "observation", state["observation_refs"][-1]
    )
    progress, verdict = assess(state["progress"], decision, observation)
    result = {
        "current_proposal": proposal,
        "approval_ref": None,
        "completion_verified": False,
        "execution_status": None,
        "error_code": None,
        "next_node": "validate",
        "remaining": charge_planning(left, used.requests, used.output_tokens, used.repairs),
        "progress": progress,
    }
    if verdict == "stop":
        result.update(
            status=stopped_status(state, partial=True),
            error_code="NO_PROGRESS",
            next_node="finalize",
        )
    elif verdict == "recover":
        result.update(error_code="NO_PROGRESS_RECOVERY", next_node="failed")
    return result
