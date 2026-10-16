async def run(state, services):
    choice = await services.recover(state)
    if choice not in {"observe", "propose"} or state["status"] == "unknown":
        return {
            "status": "unknown" if state["status"] == "unknown" else "failed",
            "next_node": "finalize",
        }
    return {
        "status": "running",
        "current_proposal": None,
        "approval_ref": None,
        "execution_status": None,
        "completion_verified": False,
        "next_node": choice,
        "remaining": {**state["remaining"], "recoveries": state["remaining"]["recoveries"] - 1},
    }
