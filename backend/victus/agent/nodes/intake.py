async def run(state, services):
    await services.intake(state)
    return {"status": "running", "next_node": "route"}
