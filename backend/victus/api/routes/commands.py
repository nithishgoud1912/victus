"""Authenticated narrow text intake and explicit clarification; no caller authority."""

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from victus.agent.commands import CommandFields, CommandResponse, CommandSubmission
from victus.runtime.resources import ResourcePressure
from victus.tasks.queue import QueueFullError


def create_commands_router(authorized):
    router = APIRouter(prefix="/api/commands", dependencies=[Depends(authorized)])

    def execute(function):
        try:
            return function()
        except KeyError:
            raise HTTPException(404, "Command not found") from None
        except (ValueError, PermissionError, FileExistsError):
            raise HTTPException(422, "Invalid command, clarification or new destination") from None
        except ResourcePressure:
            raise HTTPException(503, "Local resource pressure; no cloud fallback") from None
        except QueueFullError:
            raise HTTPException(429, "Task queue is full") from None

    @router.post("", response_model=CommandResponse)
    def submit(
        body: CommandSubmission,
        request: Request,
        x_client_request_id: str = Header(alias="X-Client-Request-ID"),
    ):
        return execute(
            lambda: request.app.state.services.commands.submit(body, x_client_request_id)
        )

    @router.get("/{command_id}", response_model=CommandResponse)
    def snapshot(command_id: str, request: Request):
        return execute(lambda: request.app.state.services.commands.get(command_id))

    @router.post("/{command_id}/clarify", response_model=CommandResponse)
    def clarify(command_id: str, body: CommandFields, request: Request):
        return execute(lambda: request.app.state.services.commands.complete(command_id, body))

    return router
