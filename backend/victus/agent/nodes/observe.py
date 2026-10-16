async def run(state, services):
    reference = await services.observe(state)
    return {
        "observation_refs": [*state["observation_refs"], reference],
        "next_node": "propose",
        "remaining": {**state["remaining"], "observations": state["remaining"]["observations"] - 1},
    }
