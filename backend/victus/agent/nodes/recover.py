from victus.agent.budgets import stopped_status


async def run(state, services):
    progress = state["progress"]
    choice = "observe" if progress["recovery_pending"] else await services.recover(state)
    if choice not in {"observe", "propose"} or state["status"] == "unknown":
        return {
            "status": stopped_status(state, partial=True)
            if progress["recovery_pending"]
            else "unknown"
            if state["status"] == "unknown"
            else "failed",
            "next_node": "finalize",
        }
    return {
        "status": "running",
        "current_proposal": None,
        "approval_ref": None,
        "execution_status": None,
        "completion_verified": False,
        "next_node": choice,
        "progress": {**progress, "recovery_pending": False},
        "remaining": {**state["remaining"], "recoveries": state["remaining"]["recoveries"] - 1},
    }
