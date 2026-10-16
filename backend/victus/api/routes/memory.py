"""Explicit memory maintenance and reviewable diagnostics; no inferred remember calls."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from victus.memory.models import MemoryEntry, MemoryInput
from victus.runtime.maintenance import MaintenanceBusy


class DiagnosticPreview(BaseModel):
    preview_id: str
    sha256: str
    contents: str
    expires_at: float


class DiagnosticExportResult(BaseModel):
    contents: str
    sha256: str


class DiagnosticExport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    preview_id: str
    sha256: str
    confirmation: Literal["explicit_user_review"]


def create_memory_router(auth_dependency):
    router = APIRouter(dependencies=[Depends(auth_dependency)])

    @router.get("/api/memory", response_model=list[MemoryEntry])
    def recall(request: Request):
        return request.app.state.services.memory.recall()

    @router.post("/api/memory", response_model=MemoryEntry)
    def remember(body: MemoryInput, request: Request):
        try:
            return request.app.state.services.memory.remember(body)
        except ValueError:
            raise HTTPException(422, "Memory expiry or content is invalid") from None

    @router.get("/api/memory/export")
    def export_memory(request: Request):
        return request.app.state.services.memory.export()

    @router.post("/api/memory/{memory_id}", response_model=MemoryEntry)
    def edit(memory_id: str, body: MemoryInput, request: Request):
        try:
            return request.app.state.services.memory.edit(memory_id, body)
        except KeyError:
            raise HTTPException(404, "Memory entry not found") from None
        except (MaintenanceBusy, RuntimeError):
            raise HTTPException(409, "Finish active work before editing memory") from None
        except ValueError:
            raise HTTPException(422, "Memory content is invalid") from None

    @router.delete("/api/memory/{memory_id}")
    def forget(memory_id: str, request: Request):
        try:
            return {"forgotten": request.app.state.services.memory.forget(memory_id)}
        except (MaintenanceBusy, RuntimeError):
            raise HTTPException(409, "Finish active work before forgetting memory") from None

    @router.post("/api/retention/cleanup")
    def cleanup(request: Request):
        try:
            return request.app.state.services.retention.cleanup()
        except (MaintenanceBusy, RuntimeError):
            raise HTTPException(409, "Finish active work before retention cleanup") from None

    @router.get("/api/resources")
    def resources_status(request: Request):
        return request.app.state.services.resources.snapshot()

    @router.get("/api/diagnostics/preview", response_model=DiagnosticPreview)
    def preview(request: Request):
        try:
            return request.app.state.services.diagnostics.preview()
        except ValueError:
            raise HTTPException(429, "Too many diagnostic previews") from None

    @router.post("/api/diagnostics/export", response_model=DiagnosticExportResult)
    def diagnostic_export(body: DiagnosticExport, request: Request):
        try:
            return request.app.state.services.diagnostics.export(body.preview_id, body.sha256)
        except ValueError:
            raise HTTPException(
                409, "Diagnostic preview changed or expired; review again"
            ) from None

    return router
