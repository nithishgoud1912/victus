from victus.agent.output_parser import FinishDecision


async def run(state, services):
    if not await services.validate(state):
        return {"error_code": "PROPOSAL_INVALID", "next_node": "failed"}
    decision = services.decision(state)
    if isinstance(decision, FinishDecision):
        if decision.status == "blocked":
            return {
                "status": "blocked",
                "error_code": "MODEL_FINISH_BLOCKED",
                "next_node": "finalize",
            }
        return {"next_node": "verify"}
    return {"next_node": "authorize"}
