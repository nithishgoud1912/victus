from victus.agent.router import RoutePlan


async def run(state, services):
    route = await services.route(state)
    if isinstance(route, RoutePlan):
        if route.mode == "blocked":
            return {
                "status": "blocked",
                "error_code": route.reason or "NO_SUPPORTED_ROUTE",
                "next_node": "finalize",
            }
        reference = services.store.put_payload(state["task_id"], "route", route.model_dump())
        return {"route_name": route.name, "route_ref": reference, "next_node": "observe"}
    return (
        {"route_name": route, "next_node": "observe"}
        if isinstance(route, str) and route
        else {"status": "blocked", "error_code": "NO_SUPPORTED_ROUTE", "next_node": "finalize"}
    )
