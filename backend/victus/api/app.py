import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from starlette.middleware.trustedhost import TrustedHostMiddleware

from victus.bootstrap import build_services
from victus.settings import Settings
from victus.tools.contracts import ActionRequest, TaskResult


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

    @app.get("/api/health", dependencies=[Depends(authorized)])
    def health(request: Request):
        return {
            "status": "ok",
            "mode": "foundation",
            "stopped": request.app.state.services.tasks.stopped.is_set(),
            "tools": request.app.state.services.tasks.registry.names(),
        }

    @app.post("/api/tasks", response_model=TaskResult, dependencies=[Depends(authorized)])
    def create_task(action: ActionRequest, request: Request):
        # Synchronous handlers run in a thread pool, keeping the stop endpoint responsive.
        return request.app.state.services.tasks.run(action)

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