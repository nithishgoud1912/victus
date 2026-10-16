"""Provider-neutral data only; model output never grants execution authority."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class ModelPin(StrictModel):
    name: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9][A-Za-z0-9_./:-]*$")
    digest: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")


class ProviderMessage(StrictModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(max_length=32768)


class ProviderRequest(StrictModel):
    pin: ModelPin
    messages: list[ProviderMessage] = Field(min_length=1, max_length=32)
    output_schema: dict[str, Any]
    max_output_tokens: int = Field(default=512, ge=1, le=2048)
    context_tokens: int = Field(default=4096, ge=512, le=8192)
    structured_path: Literal["json_schema"] = "json_schema"


class ProviderUsage(StrictModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


class ProviderResponse(StrictModel):
    pin: ModelPin
    content: str = Field(max_length=65536)
    usage: ProviderUsage
    finish_reason: Literal["stop"] = "stop"
    structured_path: Literal["json_schema"] = "json_schema"


class ErrorCode(StrEnum):
    CANCELLED = "MODEL_CANCELLED"
    TIMEOUT = "MODEL_TIMEOUT"
    BUDGET = "MODEL_BUDGET_EXHAUSTED"
    UNAVAILABLE = "MODEL_UNAVAILABLE"
    HTTP = "MODEL_HTTP_ERROR"
    PROTOCOL = "MODEL_PROTOCOL_ERROR"
    PIN = "MODEL_PIN_MISMATCH"
    OUTPUT = "MODEL_OUTPUT_INVALID"


class ProviderError(StrictModel):
    code: ErrorCode
    retryable: Literal[False] = False


class ModelError(RuntimeError):
    """Safe error: never includes provider bodies, prompts, or private output."""

    def __init__(self, code: ErrorCode):
        self.error = ProviderError(code=code)
        super().__init__(code.value)
