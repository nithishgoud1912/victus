"""Ollama's local HTTP wire schema, isolated from request governance."""

from __future__ import annotations

import asyncio
from typing import Literal
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from victus.models._json import strict_json
from victus.models.contracts import (
    ErrorCode,
    ModelError,
    ModelPin,
    ProviderRequest,
    ProviderResponse,
    ProviderUsage,
)


class WireModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")


class OllamaMessage(WireModel):
    role: Literal["assistant"]
    content: str = Field(max_length=65536)
    tool_calls: list = Field(default_factory=list, max_length=0)
    # Thinking is deliberately not returned for action parsing.


class OllamaResponse(WireModel):
    model: str
    message: OllamaMessage
    done: bool
    done_reason: Literal["stop"]
    prompt_eval_count: int = Field(ge=0)
    eval_count: int = Field(ge=0)

    @field_validator("done")
    @classmethod
    def require_done(cls, value):
        if value is not True:
            raise ValueError("Incomplete response")
        return value


class OllamaTag(WireModel):
    name: str
    digest: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")


class OllamaTags(WireModel):
    models: list[OllamaTag] = Field(max_length=256)


class OllamaClient:
    def __init__(self, base_url="http://127.0.0.1:11434", *, transport=None):
        parts = urlsplit(base_url)
        if (
            parts.scheme != "http"
            or parts.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parts.username
            or parts.password
            or parts.path not in {"", "/"}
            or parts.query
            or parts.fragment
        ):
            raise ValueError("Ollama requires a local-only HTTP origin")
        host = "[::1]" if parts.hostname == "::1" else "127.0.0.1"
        self._client = httpx.AsyncClient(
            base_url=f"http://{host}:{parts.port or 11434}",
            trust_env=False,
            follow_redirects=False,
            timeout=None,
            transport=transport,
        )

    async def _json(self, method, path, payload=None):
        try:
            async with self._client.stream(method, path, json=payload) as response:
                if response.status_code != 200:
                    raise ModelError(ErrorCode.HTTP)
                data = bytearray()
                async for part in response.aiter_bytes():
                    data.extend(part)
                    if len(data) > 200000:
                        raise ModelError(ErrorCode.PROTOCOL)
            return strict_json(data.decode("utf-8"))
        except ModelError:
            raise
        except httpx.TransportError:
            raise ModelError(ErrorCode.UNAVAILABLE) from None
        except (ValueError, UnicodeError, RecursionError):
            raise ModelError(ErrorCode.PROTOCOL) from None

    async def list_models(self) -> list[ModelPin]:
        try:
            async with asyncio.timeout(3):
                tags = OllamaTags.model_validate(await self._json("GET", "/api/tags"))
            return [ModelPin(name=tag.name, digest=tag.digest) for tag in tags.models]
        except TimeoutError:
            raise ModelError(ErrorCode.TIMEOUT) from None
        except ValidationError:
            raise ModelError(ErrorCode.PROTOCOL) from None

    async def health(self):
        return {"available_models": len(await self.list_models())}

    async def _check_pin(self, pin):
        matches = [model for model in await self.list_models() if model.name == pin.name]
        if matches != [pin]:
            raise ModelError(ErrorCode.PIN)

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        await self._check_pin(request.pin)
        payload = {
            "model": request.pin.name,
            "messages": [message.model_dump() for message in request.messages],
            "stream": False,
            "format": request.output_schema,
            "think": False,
            "options": {
                "temperature": 0,
                "num_ctx": request.context_tokens,
                "num_predict": request.max_output_tokens,
            },
        }
        try:
            result = OllamaResponse.model_validate(await self._json("POST", "/api/chat", payload))
            if result.model != request.pin.name:
                raise ModelError(ErrorCode.PIN)
            await self._check_pin(request.pin)
            return ProviderResponse(
                pin=request.pin,
                content=result.message.content,
                usage=ProviderUsage(
                    input_tokens=result.prompt_eval_count, output_tokens=result.eval_count
                ),
            )
        except ValidationError:
            raise ModelError(ErrorCode.PROTOCOL) from None

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
