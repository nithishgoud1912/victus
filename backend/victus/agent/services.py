"""Trusted domain boundaries. No browser/UIA implementation is imported here."""

from __future__ import annotations

import inspect
import json
import time
from dataclasses import dataclass
from typing import Any, Callable

from victus.agent.output_parser import ActionDecision, FinishDecision, OutputParser
from victus.models.contracts import ModelPin, ProviderMessage
from victus.models.gateway import ModelGateway, RequestBudget
from victus.storage.action_ledger import _canonical_hash
from victus.tools.dispatcher import Dispatcher


async def call(function, *args):
    result = function(*args)
    return await result if inspect.isawaitable(result) else result


@dataclass(frozen=True)
class PlanningResult:
    decision: ActionDecision | FinishDecision
    requests: int
    output_tokens: int
    repairs: int = 0


class GatewayPlanner:
    """Restore bounded M3-7A allowances from the persisted task state each turn."""

    def __init__(self, provider, pin: ModelPin, parser: OutputParser, cancelled=None):
        self.provider, self.pin, self.parser, self.cancelled = provider, pin, parser, cancelled

    async def __call__(self, goal, observations, state):
        left = state["remaining"]
        budget = RequestBudget(
            max_requests=min(2, left["model_requests"]),
            max_output_tokens=left["output_tokens"],
            timeout_seconds=min(120, left["deadline_epoch"] - time.time()),
            repairs_remaining=left["schema_repairs"],
        )
        gateway = ModelGateway(self.provider, budget, cancelled=self.cancelled)
        prompt = json.dumps(
            {"goal": goal, "observations": observations, "errors": state["error_history"]},
            allow_nan=False,
        )
        decision = await gateway.decide(
            self.pin,
            [ProviderMessage(role="user", content=prompt)],
            self.parser,
            max_output_tokens=min(512, left["output_tokens"]),
        )
        used = budget.snapshot()
        return PlanningResult(
            decision, used["requests"], used["reserved_output_tokens"], used["schema_repairs"]
        )


class _Cancellation:
    def __init__(self, original, store, task_id):
        self.original, self.store, self.task_id = original, store, task_id

    def is_set(self):
        return self.store.cancelled(self.task_id) or (
            self.original is not None and self.original.is_set()
        )


@dataclass
class AgentServices:
    store: Any
    dispatcher: Dispatcher
    parser: OutputParser
    context_factory: Callable
    planner: Callable
    router: Callable
    observer: Callable
    validator: Callable
    authorizer: Callable
    goal_verifier: Callable
    recovery: Callable | None = None
    cancelled: Any = None

    def goal(self, state):
        return self.store.payload(state["task_id"], "goal", state["goal_payload_ref"])

    def decision(self, state):
        value = self.store.payload(
            state["task_id"], "proposal", state["current_proposal"]["payload_ref"]
        )
        return self.parser.parse(json.dumps(value, allow_nan=False))

    async def intake(self, state):
        self.goal(state)
        return True

    async def route(self, state):
        return await call(self.router, self.goal(state))

    async def observe(self, state):
        observation = await call(self.observer, state["route_name"], self.goal(state))
        return self.store.put_payload(state["task_id"], "observation", observation)

    async def propose(self, state):
        observations = [
            self.store.payload(state["task_id"], "observation", ref)
            for ref in state["observation_refs"][-4:]
        ]
        result = await call(self.planner, self.goal(state), observations, state)
        if not isinstance(result, PlanningResult):
            raise ValueError("Typed planning result required")
        left = state["remaining"]
        if (
            type(result.requests) is not int
            or not 1 <= result.requests <= min(2, left["model_requests"])
            or type(result.output_tokens) is not int
            or not 1 <= result.output_tokens <= left["output_tokens"]
            or type(result.repairs) is not int
            or not 0 <= result.repairs <= left["schema_repairs"]
        ):
            raise ValueError("Planning budget mismatch")
        decision = self.parser.parse(result.decision.model_dump_json())
        ref = self.store.put_payload(state["task_id"], "proposal", decision.model_dump())
        return {"payload_ref": ref, "kind": decision.decision}, result

    async def validate(self, state):
        decision = self.decision(state)
        if isinstance(decision, FinishDecision):
            return True
        action = decision.action
        self.dispatcher.registry.get(action.tool).argument_model.model_validate(
            action.arguments, strict=True
        )
        if action.observation_id is not None:
            observed = [
                self.store.payload(state["task_id"], "observation", ref)
                for ref in state["observation_refs"]
            ]
            if not any(value.get("observation_id") == action.observation_id for value in observed):
                return False
        return await call(self.validator, state, action) is True

    async def authorize(self, state):
        decision = self.decision(state)
        if not isinstance(decision, ActionDecision):
            raise ValueError("Only actions require approval")
        result = await call(self.authorizer, state, decision.action)
        if result is not True:
            return ("pending" if result is None else "denied"), None
        ref = self.store.put_payload(
            state["task_id"],
            "approval",
            {"proposal_ref": state["current_proposal"]["payload_ref"], "expires": time.time() + 60},
        )
        return "approved", ref

    async def execution(self, state):
        """Prepare dispatcher inputs; recheck live validation and exact approval binding."""
        approval = self.store.payload(state["task_id"], "approval", state["approval_ref"])
        if (
            approval["proposal_ref"] != state["current_proposal"]["payload_ref"]
            or approval["expires"] <= time.time()
            or not await self.validate(state)
        ):
            raise PermissionError("Approval or target stale")
        action = self.decision(state).action
        if await call(self.authorizer, state, action) is not True:
            raise PermissionError("Approval withdrawn")
        context = self.context_factory(state)
        if context.task_id != state["task_id"]:
            raise PermissionError("Wrong execution context")
        original = context.authorize
        context.authorize = lambda tool, args: (
            tool.name == action.tool
            and args.model_dump()
            == self.dispatcher.registry.get(action.tool)
            .argument_model.model_validate(action.arguments)
            .model_dump()
            and original(tool, args) is True
        )
        context.cancelled = _Cancellation(context.cancelled, self.store, state["task_id"])
        context.deadline = min(
            context.deadline,
            time.monotonic() + max(0, state["remaining"]["deadline_epoch"] - time.time()),
        )
        return action, context

    def reconcile_interrupted(self, state):
        context = self.context_factory(state)
        references = list(state["action_ledger_refs"])
        for record in context.ledger.list_for_task(state["task_id"]):
            if record.action_id not in references:
                references.append(record.action_id)
            if record.status == "prepared":
                context.ledger.mark_cancelled(record.action_id)
            elif record.status in {"dispatching", "applied"}:
                context.ledger.mark_unknown(record.action_id, error_code="GRAPH_NODE_INTERRUPTED")
        return references[-32:]

    async def verify(self, state):
        """Only ledger-backed evidence and a trusted independent goal verifier count."""
        if state["execution_status"] == "unknown":
            return "unknown", False, None
        receipts = []
        for action_id in state["action_ledger_refs"]:
            context = self.context_factory(state)
            record = context.ledger.get(action_id)
            if record is None or record.expected_effect_ref != f"task:{state['task_id']}":
                return "unknown", False, None
            if record.status != "verified":
                return "unknown", False, None
            outputs = context.payloads.get_by_action(action_id, "output")
            receipts.append(
                {
                    "action_id": action_id,
                    "tool": record.tool_name,
                    "output_refs": [value.payload_id for value in outputs],
                }
            )
        if state["execution_status"] == "succeeded":
            decision = self.decision(state)
            context = self.context_factory(state)
            record = context.ledger.get(state["action_ledger_refs"][-1])
            if (
                not isinstance(decision, ActionDecision)
                or record.tool_name != decision.action.tool
                or record.canonical_args_hash
                != _canonical_hash(
                    self.dispatcher.registry.get(decision.action.tool)
                    .argument_model.model_validate(decision.action.arguments)
                    .model_dump()
                )
            ):
                return "unknown", False, None
        complete = await call(self.goal_verifier, self.goal(state), receipts) is True
        finish = self.decision(state) if state["current_proposal"] else None
        verdict = "verified" if complete or not isinstance(finish, FinishDecision) else "failed"
        ref = self.store.put_payload(
            state["task_id"],
            "evidence",
            {
                "source": "independent_goal_verifier",
                "action_receipts": receipts,
                "goal_complete": complete,
            },
        )
        return verdict, complete, ref

    async def recover(self, state):
        if state["execution_status"] == "unknown":
            return "stop"
        return await call(self.recovery, state) if self.recovery else "stop"
