import asyncio
import json

import httpx
import pytest

from victus.models.contracts import (
    ErrorCode,
    ModelError,
    ModelPin,
    ProviderMessage,
    ProviderRequest,
)
from victus.models.gateway import ModelGateway, RequestBudget
from victus.models.ollama import OllamaClient

PIN = ModelPin(name="qwen3:4b", digest="sha256:" + "a" * 64)


def wire():
    return dict(
        model=PIN.name,
        message=dict(
            role="assistant", content='{"decision":"finish"}', thinking="PRIVATE reasoning"
        ),
        done=True,
        done_reason="stop",
        prompt_eval_count=20,
        eval_count=5,
    )


def request():
    return ProviderRequest(
        pin=PIN,
        messages=[ProviderMessage(role="user", content="hello")],
        output_schema={"type": "object"},
        max_output_tokens=32,
    )


def test_real_chat_schema_pin_checks_and_usage():
    calls = []

    def handler(req):
        calls.append(req)
        if req.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [PIN.model_dump()]})
        payload = json.loads(req.content)
        assert payload["stream"] is False and payload["think"] is False
        assert payload["format"] == {"type": "object"} and "tools" not in payload
        assert payload["options"] == {"temperature": 0, "num_ctx": 4096, "num_predict": 32}
        return httpx.Response(200, json=wire())

    async def run():
        async with OllamaClient(transport=httpx.MockTransport(handler)) as client:
            return await ModelGateway(client, RequestBudget()).request(request())

    result = asyncio.run(run())
    assert result.usage.input_tokens == 20 and result.usage.output_tokens == 5
    assert result.pin == PIN and "PRIVATE" not in repr(result)
    assert [call.url.path for call in calls] == ["/api/tags", "/api/chat", "/api/tags"]


@pytest.mark.parametrize(
    "mode",
    [
        "stream-incomplete",
        "numeric-done",
        "truncated",
        "tool-call",
        "missing-usage",
        "wrong-role",
        "wrong-model",
        "wrong-pin-before",
        "wrong-pin-after",
        "http",
        "redirect",
        "bad-json",
        "oversized",
        "duplicate-json",
        "typed-count",
        "token-overrun",
    ],
)
def test_bad_wire_data_is_rejected_without_retries(mode):
    calls = []

    def handler(req):
        calls.append(req.url.path)
        if req.url.path == "/api/tags":
            pin = PIN.model_dump()
            if mode == "wrong-pin-before" or (mode == "wrong-pin-after" and len(calls) == 3):
                pin["digest"] = "sha256:" + "b" * 64
            return httpx.Response(200, json={"models": [pin]})
        result = wire()
        if mode == "numeric-done":
            result["done"] = 1
        elif mode == "stream-incomplete":
            result["done"] = False
        elif mode == "truncated":
            result["done_reason"] = "length"
        elif mode == "tool-call":
            result["message"]["tool_calls"] = [{"function": {"name": "shell"}}]
        elif mode == "missing-usage":
            del result["eval_count"]
        elif mode == "wrong-role":
            result["message"]["role"] = "user"
        elif mode == "wrong-model":
            result["model"] = "fallback"
        elif mode == "http":
            return httpx.Response(500, text="PRIVATE_ERROR")
        elif mode == "redirect":
            return httpx.Response(307, headers={"location": "http://example.com"})
        elif mode == "bad-json":
            return httpx.Response(200, text="PRIVATE not json")
        elif mode == "oversized":
            return httpx.Response(200, content=b"x" * 200001)
        elif mode == "duplicate-json":
            return httpx.Response(200, text='{"done":true,"done":false}')
        elif mode == "typed-count":
            result["eval_count"] = "5"
        elif mode == "token-overrun":
            result["eval_count"] = 33
        return httpx.Response(200, json=result)

    async def run():
        async with OllamaClient(transport=httpx.MockTransport(handler)) as client:
            return await ModelGateway(client, RequestBudget()).request(request())

    with pytest.raises(ModelError) as error:
        asyncio.run(run())
    assert "PRIVATE" not in str(error.value)
    assert calls.count("/api/chat") <= 1
    if mode.startswith("wrong-pin") or mode == "wrong-model":
        assert error.value.error.code == ErrorCode.PIN


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/a",
        "https://example.com",
        "http://192.168.1.2:11434",
        "http://localhost.evil:11434",
        "http://user:pass@localhost:11434",
        "http://localhost/a",
        "http://localhost?x=1",
        "http://localhost/#x",
    ],
)
def test_provider_rejects_nonlocal_or_ambiguous_origins(url):
    with pytest.raises(ValueError):
        OllamaClient(url)
