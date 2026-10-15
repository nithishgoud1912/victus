import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from starlette.middleware.trustedhost import TrustedHostMiddleware

from victus.api.routes.events import create_events_router
from victus.bootstrap import build_services
from victus.settings import Settings
from victus.tasks.queue import QueueFullError
from victus.tools.contracts import ActionRequest, TaskQueuedResponse, TaskResult


def create_app(settings: Settings | None = None) -> FastAPI:
    configured = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.services = build_services(configured)
        try:
            yield
        finally:
            app.state.services.close()

    app = FastAPI(
        title="VICTUS Foundation",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    def authorized(request: Request, authorization: str | None = Header(default=None)) -> None:
        # No browser clients in this milestone; reject cross-origin requests entirely.
        if request.headers.get("origin") is not None:
            raise HTTPException(status_code=403, detail="Browser origin not enabled")
        expected = "Bearer " + configured.api_token
        if authorization is None or not secrets.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="Unauthorized")

    app.include_router(create_events_router(authorized))

    @app.get("/api/health", dependencies=[Depends(authorized)])
    def health(request: Request):
        return {
            "status": "ok",
            "mode": "foundation",
            "stopped": request.app.state.services.tasks.stopped.is_set(),
            "emergency_hotkey": (
                request.app.state.services.hotkey.status
                if request.app.state.services.hotkey is not None
                else "disabled"
            ),
            "tools": request.app.state.services.tasks.registry.names(),
        }

    @app.post(
        "/api/tasks",
        status_code=status.HTTP_202_ACCEPTED,
        response_model=TaskQueuedResponse,
        dependencies=[Depends(authorized)],
    )
    def create_task(
        action: ActionRequest,
        request: Request,
        x_client_request_id: str | None = Header(default=None, alias="X-Client-Request-ID"),
        x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
        client_request_id: str | None = Query(default=None),
    ):
        req_id = x_client_request_id or x_request_id or client_request_id
        tasks = request.app.state.services.tasks
        try:
            task_id, _ = tasks.enqueue(action, client_request_id=req_id)
        except QueueFullError as e:
            raise HTTPException(status_code=429, detail=str(e))

        saved = tasks.database.get(task_id)
        task_status = (
            saved.status if saved and saved.status in ("queued", "cancelled") else "queued"
        )
        return TaskQueuedResponse(task_id=task_id, status=task_status)

    @app.get("/api/tasks/{task_id}", response_model=TaskResult, dependencies=[Depends(authorized)])
    def get_task(task_id: str, request: Request):
        task = request.app.state.services.tasks.database.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @app.post("/api/stop", dependencies=[Depends(authorized)])
    def stop(request: Request):
        request.app.state.services.tasks.stop()
        return {"stopped": True, "reset": "restart_required"}

    return app
