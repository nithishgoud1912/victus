import asyncio
import threading

import pytest

from victus.agent.output_parser import OutputParser
from victus.models.contracts import (
    ErrorCode,
    ModelError,
    ModelPin,
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
    ProviderUsage,
)
from victus.models.gateway import ModelGateway, RequestBudget
from victus.tools.contracts import NoteArguments

PIN = ModelPin(name="qwen3:4b", digest="sha256:" + "a" * 64)
VALID = '{"decision":"finish","status":"blocked","reason":"No approved target"}'


class Fake:
    def __init__(self, outputs=(VALID,), delay=0):
        self.outputs = list(outputs)
        self.delay = delay
        self.requests = []
        self.cancelled = False

    async def complete(self, request):
        self.requests.append(request)
        try:
            await asyncio.sleep(self.delay)
            output = self.outputs.pop(0)
            if isinstance(output, Exception):
                raise output
            return ProviderResponse(
                pin=PIN, content=output, usage=ProviderUsage(input_tokens=30, output_tokens=10)
            )
        except asyncio.CancelledError:
            self.cancelled = True
            raise


def request():
    return ProviderRequest(
        pin=PIN,
        messages=[ProviderMessage(role="user", content="hello")],
        output_schema={"type": "object"},
        max_output_tokens=32,
    )


def decide(gateway):
    return gateway.decide(
        PIN,
        [ProviderMessage(role="user", content="No approved target")],
        OutputParser({"fs.create_note": NoteArguments}),
        max_output_tokens=32,
    )


def test_success_usage_and_one_bounded_schema_repair():
    provider = Fake(["PRIVATE malformed", VALID])
    budget = RequestBudget(max_requests=2, max_output_tokens=64)
    gateway = ModelGateway(provider, budget)
    result = asyncio.run(decide(gateway))
    assert result.status == "blocked"
    assert budget.snapshot() == dict(requests=2, reserved_output_tokens=64, schema_repairs=1)
    assert len(gateway.usage) == 2
    assert "PRIVATE malformed" not in repr(provider.requests[1])
    assert provider.requests[0].output_schema == provider.requests[1].output_schema


def test_second_invalid_answer_stops_without_third_request():
    provider = Fake(["bad", "still bad", VALID])
    gateway = ModelGateway(provider, RequestBudget())
    with pytest.raises(ModelError) as error:
        asyncio.run(decide(gateway))
    assert error.value.error.code == ErrorCode.OUTPUT
    assert len(provider.requests) == 2


@pytest.mark.parametrize("limit", ["requests", "tokens"])
def test_repair_cannot_escape_global_request_or_token_budget(limit):
    provider = Fake(["bad", VALID])
    budget = RequestBudget(
        max_requests=1 if limit == "requests" else 4,
        max_output_tokens=32 if limit == "tokens" else 128,
    )
    with pytest.raises(ModelError) as error:
        asyncio.run(decide(ModelGateway(provider, budget)))
    assert error.value.error.code == ErrorCode.BUDGET
    assert len(provider.requests) == 1


def test_repair_allowance_is_shared_across_gateways():
    budget = RequestBudget()
    first = ModelGateway(Fake(["bad", VALID]), budget)
    second_provider = Fake(["bad", VALID])
    asyncio.run(decide(first))
    with pytest.raises(ModelError) as error:
        asyncio.run(decide(ModelGateway(second_provider, budget)))
    assert error.value.error.code == ErrorCode.BUDGET
    assert budget.snapshot()["schema_repairs"] == 1
    assert len(second_provider.requests) == 1


def test_concurrent_gateways_share_atomic_reservations():
    budget = RequestBudget(max_requests=2)
    provider = Fake([VALID, VALID], delay=0.01)

    async def run():
        return await asyncio.gather(
            *(ModelGateway(provider, budget).request(request()) for _ in range(5)),
            return_exceptions=True,
        )

    results = asyncio.run(run())
    assert sum(isinstance(value, ProviderResponse) for value in results) == 2
    assert len(provider.requests) == 2 and budget.snapshot()["requests"] == 2


@pytest.mark.parametrize("mode", ["request-timeout", "global-timeout", "event-stop", "task-cancel"])
def test_inflight_deadline_and_cancellation_clean_up_provider(mode):
    provider = Fake(delay=10)
    stopped = threading.Event()
    budget = RequestBudget(timeout_seconds=0.04 if mode == "global-timeout" else 10)
    gateway = ModelGateway(
        provider,
        budget,
        cancelled=stopped,
        timeout_seconds=0.04 if mode == "request-timeout" else 10,
    )

    async def run():
        pending = asyncio.create_task(gateway.request(request()))
        if mode in {"event-stop", "task-cancel"}:
            await asyncio.sleep(0.01)
            if mode == "event-stop":
                stopped.set()
            else:
                pending.cancel()
        return await pending

    expected = asyncio.CancelledError if mode == "task-cancel" else ModelError
    with pytest.raises(expected) as error:
        asyncio.run(run())
    if isinstance(error.value, ModelError):
        assert error.value.error.code == (
            ErrorCode.CANCELLED if mode == "event-stop" else ErrorCode.TIMEOUT
        )
    assert provider.cancelled and len(provider.requests) == 1
    assert budget.snapshot()["requests"] == 1


def test_stop_before_request_sends_nothing():
    stopped = threading.Event()
    stopped.set()
    provider = Fake()
    budget = RequestBudget()
    with pytest.raises(ModelError):
        asyncio.run(ModelGateway(provider, budget, cancelled=stopped).request(request()))
    assert not provider.requests and budget.snapshot()["requests"] == 0


def test_provider_failure_is_safe_and_never_retried():
    provider = Fake([ModelError(ErrorCode.UNAVAILABLE)])
    with pytest.raises(ModelError) as error:
        asyncio.run(decide(ModelGateway(provider, RequestBudget())))
    assert str(error.value) == "MODEL_UNAVAILABLE" and len(provider.requests) == 1


def test_mutated_request_is_revalidated_without_leaking_private_data():
    value = request()
    value.messages.append({"role": "user", "content": "PRIVATE invalid message"})
    provider = Fake()
    with pytest.raises(ModelError) as error:
        asyncio.run(ModelGateway(provider, RequestBudget()).request(value))
    assert str(error.value) == "MODEL_PROTOCOL_ERROR"
    assert provider.requests == []


def test_expired_global_budget_never_dispatches():
    import time

    budget = RequestBudget()
    budget.deadline = time.monotonic() - 1
    provider = Fake()
    with pytest.raises(ModelError) as error:
        asyncio.run(ModelGateway(provider, budget).request(request()))
    assert error.value.error.code == ErrorCode.TIMEOUT
    assert not provider.requests
