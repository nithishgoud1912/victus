"""Optional cloud preview and review. Responses are data, never tool authority."""

from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from victus.models.contracts import ModelError, ModelPin, ProviderRequest, ProviderResponse
from victus.models.transfer_policy import ConsentRequired, TransferPreview


class IntegrationStatus(BaseModel):
    cloud: str
    cloud_pin: ModelPin | None
    upstream: str | None
    mcp_notes: bool


class TransferResult(BaseModel):
    response: ProviderResponse | None


class TransferDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(min_length=32, max_length=32)
    approve: bool
    confirmation: Literal["explicit_user_review"]


def create_integrations_router(auth_dependency):
    router = APIRouter(prefix="/api/integrations", tags=["integrations"],
                       dependencies=[Depends(auth_dependency)])

    def service(request):
        value = request.app.state.services.cloud
        if value is None:
            raise HTTPException(409, "Cloud is disabled")
        return value

    @router.get("", response_model=IntegrationStatus)
    def status(request: Request):
        cloud = request.app.state.services.cloud
        return {"cloud": cloud.state if cloud else "disabled",
                "cloud_pin": cloud.pin.model_dump() if cloud else None,
                "upstream": cloud.upstream if cloud else None,
                "mcp_notes": request.app.state.services.settings.mcp_notes}

    @router.post("/cloud/preview", response_model=TransferPreview)
    def preview(body: ProviderRequest, request: Request):
        try:
            return asdict(service(request).preview(body))
        except ModelError as error:
            raise HTTPException(409, str(error)) from None
        except ValueError:
            raise HTTPException(409, "Transfer preview unavailable") from None

    @router.post("/cloud/review", response_model=TransferResult)
    async def review(body: TransferDecision, request: Request):
        try:
            result = await service(request).review(body.id, approve=body.approve,
                                                   confirmation=body.confirmation)
            return {"response": result.model_dump() if result else None}
        except ConsentRequired:
            raise HTTPException(409, "Transfer expired or already reviewed") from None
        except ModelError as error:
            raise HTTPException(503, str(error)) from None

    return router
