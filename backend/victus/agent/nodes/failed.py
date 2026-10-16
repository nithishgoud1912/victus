async def run(state, services):
    error = {"code": state["error_code"] or "OPERATION_FAILED", "sequence": str(state["sequence"])}
    return {"error_history": [*state["error_history"], error][-16:], "next_node": "recover"}
