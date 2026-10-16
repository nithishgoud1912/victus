"""Task-wide inference budget, deadline, cancellation and one repair per decision."""

from __future__ import annotations

import asyncio
import json
import math
import threading
import time
from typing import Protocol
from uuid import uuid4

from victus.agent.output_parser import OutputParser
from victus.models.contracts import (
    ErrorCode,
    ModelError,
    ModelPin,
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
)


class Provider(Protocol):
    async def complete(self, request: ProviderRequest) -> ProviderResponse: ...


class RequestBudget:
    """Share across task branches; atomic reservations are never refunded.

    Failed/cancelled calls still consume requests and worst-case output tokens.
    One repair per decision additionally consumes a shared request reservation.
    """

    def __init__(
        self, *, max_requests=8, max_output_tokens=4096, timeout_seconds=180, repairs_remaining=1
    ):
        if (
            type(repairs_remaining) is not int
            or not 0 <= repairs_remaining <= 1
            or type(max_requests) is not int
            or not 1 <= max_requests <= 32
            or type(max_output_tokens) is not int
            or not 1 <= max_output_tokens <= 65536
            or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 600
        ):
            raise ValueError("Invalid model budget")
        self._max_repairs = repairs_remaining
        self._max_requests = max_requests
        self._max_tokens = max_output_tokens
        self.deadline = time.monotonic() + timeout_seconds
        self._requests = self._tokens = self._repairs = 0
        self._decision_repairs = {}
        self._lock = threading.Lock()

    def reserve(self, tokens, *, repair=False, decision_id=None):
        with self._lock:
            if time.monotonic() >= self.deadline:
                raise ModelError(ErrorCode.TIMEOUT)
            if (
                self._requests >= self._max_requests
                or self._tokens + tokens > self._max_tokens
                or (repair and self._decision_repairs.get(decision_id, 0) >= self._max_repairs)
            ):
                raise ModelError(ErrorCode.BUDGET)
            self._requests += 1
            self._tokens += tokens
            self._repairs += int(repair)
            if repair:
                self._decision_repairs[decision_id] = self._decision_repairs.get(decision_id, 0) + 1

    def snapshot(self):
        with self._lock:
            return {
                "requests": self._requests,
                "reserved_output_tokens": self._tokens,
                "schema_repairs": self._repairs,
            }


class ModelGateway:
    def __init__(
        self, provider: Provider, budget: RequestBudget, *, cancelled=None, timeout_seconds=30
    ):
        if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 120:
            raise ValueError("Invalid model request timeout")
        self.provider, self.budget, self.cancelled = provider, budget, cancelled
        self.timeout_seconds = timeout_seconds
        self.usage = []

    def _check_cancelled(self):
        if self.cancelled is not None and self.cancelled.is_set():
            raise ModelError(ErrorCode.CANCELLED)

    async def request(
        self, request: ProviderRequest, *, repair=False, decision_id=None
    ) -> ProviderResponse:
        self._check_cancelled()
        try:
            request = ProviderRequest.model_validate(request.model_dump(warnings="error"))
            if len(json.dumps(request.model_dump(), allow_nan=False).encode("utf-8")) > 96000:
                raise ValueError("Request bound")
        except Exception:
            raise ModelError(ErrorCode.PROTOCOL) from None
        self.budget.reserve(request.max_output_tokens, repair=repair, decision_id=decision_id)
        self._check_cancelled()
        deadline = min(self.budget.deadline, time.monotonic() + self.timeout_seconds)
        pending = asyncio.create_task(self.provider.complete(request))
        try:
            while not pending.done():
                self._check_cancelled()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ModelError(ErrorCode.TIMEOUT)
                await asyncio.wait({pending}, timeout=min(0.02, remaining))
            self._check_cancelled()
            if time.monotonic() >= deadline:
                raise ModelError(ErrorCode.TIMEOUT)
            response = ProviderResponse.model_validate(
                pending.result().model_dump(warnings="error")
            )
            if response.pin != request.pin or response.structured_path != request.structured_path:
                raise ModelError(ErrorCode.PIN)
            if response.usage.output_tokens > request.max_output_tokens:
                raise ModelError(ErrorCode.PROTOCOL)
            self.usage.append(response.usage)
            return response
        except asyncio.CancelledError:
            raise
        except ModelError:
            raise
        except Exception:
            raise ModelError(ErrorCode.PROTOCOL) from None
        finally:
            if not pending.done():
                pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)

    async def decide(
        self,
        pin: ModelPin,
        messages: list[ProviderMessage],
        parser: OutputParser,
        *,
        max_output_tokens=512,
    ):
        schema = parser.schema()
        instructions = ProviderMessage(
            role="system",
            content=(
                "Return exactly one JSON object matching this schema. Propose only catalog tools, "
                "or explicitly finish. Do not output code, markdown, or extra text. "
                "A finish decision is not verification of task completion. Schema: "
                + json.dumps(schema, separators=(",", ":"))
            ),
        )
        request = ProviderRequest(
            pin=pin,
            messages=[instructions, *messages],
            output_schema=schema,
            max_output_tokens=max_output_tokens,
        )
        decision_id = uuid4().hex
        response = await self.request(request, decision_id=decision_id)
        try:
            return parser.parse(response.content)
        except ModelError as error:
            if error.error.code != ErrorCode.OUTPUT:
                raise
        # Never echo malformed output into higher-trust repair instructions.
        repaired = request.model_copy(
            update={
                "messages": [
                    *request.messages,
                    ProviderMessage(
                        role="user",
                        content="Your previous response failed validation. Return one valid "
                        "decision using the exact schema and original request. No code or extra text.",
                    ),
                ]
            }
        )
        response = await self.request(repaired, repair=True, decision_id=decision_id)
        return parser.parse(response.content)
