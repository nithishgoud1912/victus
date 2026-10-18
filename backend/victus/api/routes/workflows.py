"""Narrow, authenticated workflow admission through the existing task service."""

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel

from victus.runtime.resources import ResourcePressure
from victus.tasks.queue import QueueFullError
from victus.tools.contracts import TaskQueuedResponse
from victus.workflows.contracts import (
    BrowserResearchSubmission,
    NotepadChecklistSubmission,
    WorkflowUnavailable,
)


class ChecklistCapability(BaseModel):
    enabled: bool
    profiles: list[str]
    reason: str | None


class WorkflowCapabilities(BaseModel):
    notepad_checklist: ChecklistCapability
    stopped: bool
    resource_blocked: bool
    browser_research: "ResearchCapability"
    commands: "CommandCapability"


class ResearchCapability(BaseModel):
    enabled: bool
    scope: str = "fixture_only"
    source_ids: list[str]
    reason: str | None


class CommandCapability(BaseModel):
    deterministic: list[str]
    model_name: str | None
    model_digest: str | None
    reasoning_ready: bool
    reason: str | None


def create_workflows_router(authorized):
    router = APIRouter(prefix="/api/workflows", dependencies=[Depends(authorized)])

    @router.get("/capabilities", response_model=WorkflowCapabilities)
    def capabilities(request: Request):
        from victus.runtime.resources import resources
        from victus.workflows.contracts import NOTEPAD_CHECKLIST_TOOL

        tasks = request.app.state.services.tasks
        commands = request.app.state.services.commands
        reasoning_ready = commands.model_ready()
        profiles = sorted(tasks.qualified_notepad_profiles & tasks.reviewed_notepad_profiles)
        enabled = bool(profiles) and NOTEPAD_CHECKLIST_TOOL in tasks.registry.names()
        blocked = False
        try:
            resources().check()
        except ResourcePressure:
            blocked = True
        return WorkflowCapabilities(
            notepad_checklist=ChecklistCapability(
                enabled=enabled,
                profiles=profiles if enabled else [],
                reason=None
                if enabled
                else "Native Notepad qualification and Save review qualification are required.",
            ),
            stopped=tasks.stopped.is_set(),
            resource_blocked=blocked,
            browser_research={
                "enabled": tasks.research is not None,
                "scope": "fixture_only",
                "source_ids": ["source-a", "source-b", "redirect-a"] if tasks.research else [],
                "reason": None
                if tasks.research
                else "Qualified bundled fixture browser is unavailable. Public web is not enabled.",
            },
            commands=CommandCapability(
                deterministic=["note"]
                + (["checklist"] if enabled else [])
                + (["research"] if tasks.research else []),
                model_name=commands.model_pin.name if commands.model_pin else None,
                model_digest=commands.model_pin.digest if commands.model_pin else None,
                reasoning_ready=reasoning_ready,
                reason=None
                if reasoning_ready
                else "An installed exact local reasoning model is required; no automatic cloud fallback.",
            ),
        )

    @router.post("/browser-research", status_code=202, response_model=TaskQueuedResponse)
    def submit_research(
        body: BrowserResearchSubmission,
        request: Request,
        x_client_request_id: str | None = Header(default=None, alias="X-Client-Request-ID"),
    ):
        try:
            tasks = request.app.state.services.tasks
            task_id, _ = tasks.enqueue_research(body, x_client_request_id)
            saved = tasks.database.get(task_id)
            return TaskQueuedResponse(
                task_id=task_id,
                status="cancelled" if saved and saved.status == "cancelled" else "queued",
            )
        except WorkflowUnavailable:
            raise HTTPException(
                503, "Fixture research prerequisite unavailable; public web not enabled"
            ) from None
        except (ValueError, PermissionError, FileExistsError):
            raise HTTPException(422, "Invalid source IDs or new JSON destination") from None
        except ResourcePressure:
            raise HTTPException(503, "Local resource pressure") from None
        except QueueFullError:
            raise HTTPException(429, "Task queue is full") from None

    @router.post("/notepad-checklist", status_code=202, response_model=TaskQueuedResponse)
    def submit_notepad(
        body: NotepadChecklistSubmission,
        request: Request,
        x_client_request_id: str | None = Header(default=None, alias="X-Client-Request-ID"),
        x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
        client_request_id: str | None = Query(default=None),
    ):
        tasks = request.app.state.services.tasks
        try:
            task_id, _ = tasks.enqueue_notepad(
                body, client_request_id=x_client_request_id or x_request_id or client_request_id
            )
        except WorkflowUnavailable:
            raise HTTPException(503, "Notepad workflow is not qualified and enabled") from None
        except (ValueError, PermissionError, FileExistsError):
            raise HTTPException(
                422, "Unsupported profile or invalid new workspace destination"
            ) from None
        except ResourcePressure:
            raise HTTPException(503, "Local resource pressure; no cloud fallback") from None
        except QueueFullError:
            raise HTTPException(429, "Task queue is full") from None
        saved = tasks.database.get(task_id)
        task_status = (
            saved.status if saved and saved.status in {"queued", "cancelled"} else "queued"
        )
        return TaskQueuedResponse(task_id=task_id, status=task_status)

    return router
