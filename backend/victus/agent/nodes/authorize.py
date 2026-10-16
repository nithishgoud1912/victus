import time

from victus.agent.budgets import pause_for_approval, stopped_status


async def run(state, services):
    status, reference = await services.authorize(state)
    expiry = state["remaining"]["approval_expires_epoch"]
    if expiry is not None and time.time() >= expiry:
        return {
            "status": stopped_status(state),
            "error_code": "APPROVAL_WAIT_EXPIRED",
            "next_node": "finalize",
            "approval_ref": None,
        }
    if status == "approved":
        return {
            "approval_ref": reference,
            "next_node": "execute",
            "remaining": {
                **state["remaining"],
                "approval_started_epoch": None,
                "approval_expires_epoch": None,
            },
        }
    if status == "pending":
        return {
            "status": "awaiting_approval",
            "approval_ref": reference,
            "next_node": "review",
            "remaining": pause_for_approval(state["remaining"]),
        }
    return {"status": "blocked", "error_code": "APPROVAL_DENIED", "next_node": "finalize"}
