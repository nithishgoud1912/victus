import re
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

from victus.api.auth import BrowserSessions, create_auth
from victus.api.routes.approvals import create_approvals_router
from victus.api.routes.events import create_events_router
from victus.api.routes.session import create_session_router
from victus.bootstrap import build_services
from victus.settings import Settings
from victus.tasks.queue import QueueFullError
from victus.tools.contracts import ActionRequest, TaskQueuedResponse, TaskResult


class HealthResponse(BaseModel):
    status: str
    mode: str
    stopped: bool
    emergency_hotkey: str
    tools: list[str]


class StopResponse(BaseModel):
    stopped: bool
    reset: str


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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[configured.dashboard_dev_origin] if configured.dashboard_dev_origin else [],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Client-Request-ID",
            "X-Request-ID",
            "Last-Event-ID",
        ],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    sessions = BrowserSessions()
    app.state.browser_sessions = sessions
    authorized, require_bearer = create_auth(configured, sessions)

    @app.middleware("http")
    async def request_metadata(request, call_next):
        supplied = request.headers.get("x-request-id", "")
        request_id = supplied if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", supplied) else uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    app.include_router(create_events_router(authorized))
    app.include_router(create_approvals_router(authorized))
    app.include_router(create_session_router(authorized, require_bearer, sessions))

    @app.get("/api/health", response_model=HealthResponse, dependencies=[Depends(authorized)])
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

    @app.post("/api/stop", response_model=StopResponse, dependencies=[Depends(authorized)])
    def stop(request: Request):
        request.app.state.services.tasks.stop()
        return {"stopped": True, "reset": "restart_required"}

    dashboard = (
        configured.dashboard_dir or Path(__file__).resolve().parents[3] / "dashboard" / "dist"
    )
    if (dashboard / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dashboard / "assets"), name="dashboard-assets")

    @app.get("/", include_in_schema=False)
    def dashboard_index():
        index = dashboard / "index.html"
        if not index.is_file() or index.is_symlink():
            raise HTTPException(404, "Dashboard build not installed")
        return FileResponse(
            index,
            headers={
                "Cache-Control": "no-store",
                "X-Frame-Options": "DENY",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            },
        )

    return app
