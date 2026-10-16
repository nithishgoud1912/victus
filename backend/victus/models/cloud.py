"""Opt-in OpenRouter provider for ModelGateway; no automatic fallback or retry.

The pin identifies the configured remote model, not independently verified weights.
An upstream provider must be selected explicitly and is included in the consent.
"""

import json

import httpx

from victus.models.contracts import (
    ErrorCode,
    ModelError,
    ProviderResponse,
    ProviderUsage,
)
from victus.models.transfer_policy import ConsentRequired, encode_transfer


class CloudProvider:
    endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, pin, upstream, policy, credentials, *, transport=None):
        if not upstream or len(upstream) > 100 or not upstream.isprintable():
            raise ValueError("Select one upstream provider")
        self.pin, self.upstream = pin, upstream
        self.policy, self.credentials = policy, credentials
        self.transport = transport
        self.consent_id = None
        self.dependency_state = "consent_required"

    @property
    def recipient(self):
        return f"OpenRouter / {self.upstream} / {self.pin.name}"

    def body(self, request):
        if request.pin != self.pin:
            raise ModelError(ErrorCode.PIN)
        return {
            "model": self.pin.name,
            "messages": [m.model_dump() for m in request.messages],
            "max_tokens": request.max_output_tokens,
            "temperature": 0,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "victus_response", "strict": True, "schema": request.output_schema,
            }},
            "provider": {"order": [self.upstream], "allow_fallbacks": False,
                         "require_parameters": True, "data_collection": "deny"},
        }

    def preview(self, request):
        return self.policy.preview(self.recipient, self.body(request))

    async def complete(self, request):
        body = self.body(request)
        consent, self.consent_id = self.consent_id, None
        try:
            self.policy.consume(consent, self.recipient, body)
        except ConsentRequired:
            self.dependency_state = "consent_required"
            raise ModelError(ErrorCode.CONSENT) from None
        try:
            key = self.credentials.read()
            raw = encode_transfer(body)
            if key.encode() in raw:
                raise ValueError()
        except Exception:
            self.dependency_state = "credential_unavailable"
            raise ModelError(ErrorCode.UNAVAILABLE) from None
        try:
            async with httpx.AsyncClient(
                timeout=20, trust_env=False, follow_redirects=False, transport=self.transport,
            ) as client:
                async with client.stream("POST", self.endpoint, content=raw, headers={
                    "Authorization": "Bearer " + key, "Content-Type": "application/json",
                }) as response:
                    if response.status_code == 429:
                        self.dependency_state = "quota_exhausted"
                        raise ModelError(ErrorCode.QUOTA)
                    if response.status_code != 200:
                        self.dependency_state = "unavailable"
                        raise ModelError(ErrorCode.HTTP)
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > 200000:
                            raise ValueError()
            if key.encode() in data:
                raise ValueError()
            value = json.loads(data)
            if value["model"] != self.pin.name or len(value["choices"]) != 1:
                raise ValueError()
            choice = value["choices"][0]
            message = choice["message"]
            if (choice["finish_reason"] != "stop" or message.get("role") != "assistant"
                    or message.get("tool_calls") or message.get("function_call")
                    or not isinstance(message["content"], str)):
                raise ValueError()
            usage = value["usage"]
            result = ProviderResponse(
                pin=self.pin, content=message["content"],
                usage=ProviderUsage(input_tokens=usage["prompt_tokens"],
                                    output_tokens=usage["completion_tokens"]),
            )
            if result.usage.output_tokens > request.max_output_tokens:
                raise ValueError()
            self.dependency_state = "ready"
            return result
        except ModelError:
            raise
        except httpx.TimeoutException:
            self.dependency_state = "timeout"
            raise ModelError(ErrorCode.TIMEOUT) from None
        except httpx.HTTPError:
            self.dependency_state = "unavailable"
            raise ModelError(ErrorCode.UNAVAILABLE) from None
        except Exception:
            self.dependency_state = "invalid_output"
            raise ModelError(ErrorCode.PROTOCOL) from None
