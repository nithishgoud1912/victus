"""Authenticated voice controls. Blocking work lives in the voice worker, not ASGI."""

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Request

from victus.runtime.resources import ResourcePressure
from victus.tasks.queue import QueueFullError
from victus.voice.contracts import (
    MuteRequest,
    ReviewedClarification,
    ReviewedSubmission,
    SessionCommand,
    VoiceSnapshot,
)
from victus.voice.service import VoiceConflict


def create_voice_router(auth_dependency: Callable) -> APIRouter:
    router = APIRouter(prefix="/api/voice", tags=["voice"], dependencies=[Depends(auth_dependency)])

    def invoke(request, method, *args):
        try:
            return getattr(request.app.state.services.voice, method)(*args)
        except VoiceConflict as error:
            raise HTTPException(409, str(error)) from None
        except ResourcePressure:
            raise HTTPException(503, "Local resource pressure") from None
        except QueueFullError:
            raise HTTPException(429, "Task queue is full; review and retry") from None
        except (ValueError, PermissionError, FileExistsError):
            raise HTTPException(422, "Invalid reviewed command or clarification") from None

    @router.get("", response_model=VoiceSnapshot)
    def voice_status(request: Request):
        return invoke(request, "snapshot")

    @router.post("/start", response_model=VoiceSnapshot)
    def voice_start(request: Request):
        return invoke(request, "start")

    @router.post("/wake/enable", response_model=VoiceSnapshot)
    def wake_enable(request: Request):
        try:
            request.app.state.services.voice.wake.enable()
        except VoiceConflict as error:
            raise HTTPException(409, str(error)) from None
        return invoke(request, "snapshot")

    @router.post("/wake/disable", response_model=VoiceSnapshot)
    def wake_disable(request: Request):
        try:
            request.app.state.services.voice.wake.disable()
        except VoiceConflict as error:
            raise HTTPException(409, str(error)) from None
        return invoke(request, "snapshot")

    @router.post("/finish", response_model=VoiceSnapshot)
    def voice_finish(body: SessionCommand, request: Request):
        return invoke(request, "finish", body.session_id, body.revision)

    @router.post("/cancel", response_model=VoiceSnapshot)
    def voice_cancel(request: Request):
        return invoke(request, "cancel")

    @router.post("/submit", response_model=VoiceSnapshot)
    def voice_submit(body: ReviewedSubmission, request: Request):
        return invoke(
            request, "submit", body.session_id, body.revision, body.command or body.action
        )

    @router.post("/clarify", response_model=VoiceSnapshot)
    def voice_clarify(body: ReviewedClarification, request: Request):
        return invoke(request, "clarify", body.session_id, body.revision, body.fields)

    @router.post("/displayed", response_model=VoiceSnapshot)
    def voice_displayed(body: SessionCommand, request: Request):
        return invoke(request, "acknowledge", body.session_id, body.revision)

    @router.post("/mute", response_model=VoiceSnapshot)
    def voice_mute(body: MuteRequest, request: Request):
        return invoke(request, "mute", body.muted)

    return router
