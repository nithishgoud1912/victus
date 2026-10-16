async def run(state, services):
    route = await services.route(state)
    return (
        {"route_name": route, "next_node": "observe"}
        if isinstance(route, str) and route
        else {"status": "blocked", "error_code": "NO_SUPPORTED_ROUTE", "next_node": "finalize"}
    )
