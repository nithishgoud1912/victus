async def run(state, services):
    status, reference = await services.authorize(state)
    if status == "approved":
        return {"approval_ref": reference, "next_node": "execute"}
    if status == "pending":
        return {"status": "awaiting_approval", "next_node": "end"}
    return {"status": "blocked", "error_code": "APPROVAL_DENIED", "next_node": "finalize"}
