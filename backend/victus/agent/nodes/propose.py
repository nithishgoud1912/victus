async def run(state, services):
    proposal, used = await services.propose(state)
    left = state["remaining"]
    return {
        "current_proposal": proposal,
        "approval_ref": None,
        "completion_verified": False,
        "execution_status": None,
        "error_code": None,
        "next_node": "validate",
        "remaining": {
            **left,
            "model_requests": left["model_requests"] - used.requests,
            "output_tokens": left["output_tokens"] - used.output_tokens,
            "schema_repairs": left["schema_repairs"] - used.repairs,
        },
    }
