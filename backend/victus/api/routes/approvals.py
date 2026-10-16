"""Authenticated explicit review. The URL chooses the immutable saved record."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from victus.safety.approvals import ApprovalRecord


class Resolution(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    decision: Literal["approved", "denied"]
    confirmation: Literal["explicit_user_review"]


def create_approvals_router(authorized):
    router = APIRouter(prefix="/api/approvals", dependencies=[Depends(authorized)])

    @router.get("/{approval_id}", response_model=ApprovalRecord)
    def get_approval(approval_id: str, request: Request):
        record = request.app.state.services.approvals.get(approval_id)
        if record is None:
            raise HTTPException(404, "Approval not found")
        return record

    @router.get("/{approval_id}/preview", response_model=dict)
    def get_preview(approval_id: str, request: Request):
        store = request.app.state.services.approvals
        record = store.get(approval_id)
        if record is None:
            raise HTTPException(404, "Approval not found")
        try:
            return store.preview(approval_id, task_id=record.task_id)
        except PermissionError:
            raise HTTPException(409, f"Approval is {record.state}; preview unavailable") from None

    @router.post("/{approval_id}/resolve", response_model=ApprovalRecord)
    def resolve(approval_id: str, body: Resolution, request: Request):
        services = request.app.state.services
        store = services.approvals
        record = store.get(approval_id)
        if record is None:
            raise HTTPException(404, "Approval not found")
        if services.tasks.stopped.is_set():
            store.invalidate(approval_id)
            raise HTTPException(409, "Service stopped; approval invalidated")
        if record.state != "pending":
            raise HTTPException(409, f"Approval is {record.state}; a new review is required")
        # No caller-supplied action ID, arguments, version or target is accepted.
        # Voice transcription has no entry point here and is not a confirmation.
        try:
            return store.decide(approval_id, record.binding(), approved=body.decision == "approved")
        except PermissionError:
            current = store.get(approval_id)
            raise HTTPException(409, f"Approval is {current.state}; resolution conflicts") from None

    return router
