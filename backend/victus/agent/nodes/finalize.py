async def run(state, services):
    status = state["status"]
    if status == "succeeded" and (not state["completion_verified"] or not state["evidence_refs"]):
        status = "blocked"
    if status in {"running", "queued", "awaiting_approval"}:
        status = "failed"
    return {"status": status, "next_node": "end", "approval_ref": None}
