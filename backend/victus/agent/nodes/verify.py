"""Consume independent evidence, never a model's completion claim."""


async def run(state, services):
    verdict, complete, reference = await services.verify(state)
    refs = [*state["evidence_refs"], reference] if reference else state["evidence_refs"]
    if verdict == "verified":
        return {
            "evidence_refs": refs,
            "completion_verified": complete,
            "status": "succeeded" if complete else "running",
            "next_node": "finalize" if complete else "observe",
        }
    return {
        "evidence_refs": refs,
        "completion_verified": False,
        "status": "unknown" if verdict == "unknown" else "running",
        "error_code": "VERIFICATION_UNKNOWN" if verdict == "unknown" else "GOAL_NOT_VERIFIED",
        "next_node": "failed",
    }
