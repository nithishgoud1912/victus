"""Trusted domain boundaries. No browser/UIA implementation is imported here."""

from __future__ import annotations

import inspect
import json
import time
from dataclasses import dataclass
from typing import Any, Callable

from victus.agent.budgets import seconds_left
from victus.agent.context import ContextBuilder
from victus.agent.output_parser import ActionDecision, FinishDecision, OutputParser
from victus.agent.router import RoutePlan
from victus.models.contracts import ModelPin
from victus.models.gateway import ModelGateway, RequestBudget
from victus.safety.approvals import ApprovalBinding, ApprovalStore, argument_hash
from victus.safety.permits import PermitStore
from victus.storage.action_ledger import _canonical_hash
from victus.tools.dispatcher import Dispatcher
from victus.tools.registry import RiskLevel


async def call(function, *args):
    result = function(*args)
    return await result if inspect.isawaitable(result) else result


@dataclass(frozen=True)
class PlanningResult:
    decision: ActionDecision | FinishDecision
    requests: int
    output_tokens: int
    repairs: int = 0


class PlanningFailure(Exception):
    """Carry reservations on failure; attempted requests are never refunded."""

    def __init__(self, usage):
        super().__init__("PLANNING_FAILED")
        self.usage = usage


class GatewayPlanner:
    """Restore bounded M3-7A allowances from the persisted task state each turn."""

    def __init__(self, provider, pin: ModelPin, parser: OutputParser, cancelled=None):
        self.provider, self.pin, self.parser, self.cancelled = provider, pin, parser, cancelled

    async def __call__(self, goal, observations, state):
        left = state["remaining"]
        budget = RequestBudget(
            max_requests=min(2, left["model_requests"]),
            max_output_tokens=left["output_tokens"],
            timeout_seconds=min(120, seconds_left(left)),
            repairs_remaining=left["schema_repairs"],
        )
        gateway = ModelGateway(self.provider, budget, cancelled=self.cancelled)
        try:
            inputs = state.get("planning_inputs", {})
            context = ContextBuilder().build(
                goal,
                observations,
                self.parser.tools,
                relevant_tools=inputs.get("relevant_tools"),
                outcomes=inputs.get("outcomes", state["error_history"][-4:]),
                preferences=inputs.get("preferences", ()),
            )
            decision = await gateway.decide(
                self.pin,
                context.messages,
                context.parser,
                max_output_tokens=min(512, left["output_tokens"]),
            )
        except Exception:
            raise PlanningFailure(budget.snapshot()) from None
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
    preferences: Callable | None = None
    target_identity: Callable | None = None
    policy_version: str = "victus-policy-1"
    reconciler: Any = None

    def approvals(self, state):
        return ApprovalStore(self.context_factory(state).ledger.db_path)

    def file_target_identity(self, filename):
        """Trusted filesystem resolver; UI targets must use their adapter resolver."""
        path = self.dispatcher.workspace / filename
        if path.resolve().parent != self.dispatcher.workspace.resolve() or path.is_symlink():
            raise PermissionError("Unsafe destination")
        parent = path.parent.stat()
        stat = path.stat() if path.exists() else None
        return "file:" + argument_hash(
            {
                "path": str(path.resolve()),
                "parent": [parent.st_dev, parent.st_ino],
                "target": [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns]
                if stat
                else None,
            }
        )

    async def binding(self, state, action_id):
        action = self.decision(state).action
        tool = self.dispatcher.registry.get(action.tool)
        arguments = tool.argument_model.model_validate(action.arguments).model_dump()
        if not await self.validate(state):
            raise PermissionError("New observation and approval required")
        if self.target_identity is not None:
            identity = await call(self.target_identity, state, action)
        elif (
            tool.name.startswith("fs.")
            and "filename" in arguments
            and not (action.target_ref or arguments.get("target_ref"))
        ):
            identity = self.file_target_identity(arguments["filename"])
        else:
            raise PermissionError("Live target identity resolver required")
        observation = action.observation_id or arguments.get("observation_id")
        latest_ref = state["observation_refs"][-1]
        latest = self.store.payload(state["task_id"], "observation", latest_ref)
        latest_identity = latest.get("observation_id", latest_ref)
        if observation is not None and observation != latest_identity:
            raise PermissionError("New observation and approval required")
        observation = latest_identity
        return ApprovalBinding(
            task_id=state["task_id"],
            action_id=action_id,
            tool_name=tool.name,
            tool_version=tool.version,
            canonical_args_hash=argument_hash(arguments),
            policy_version=self.policy_version,
            target_identity=identity,
            observation_identity=observation,
        )

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

    def route_plan(self, state):
        if state.get("route_ref") is None:
            return None
        return RoutePlan.model_validate(
            self.store.payload(state["task_id"], "route", state["route_ref"])
        )

    def is_deterministic(self, state):
        route = self.route_plan(state)
        return route is not None and route.mode == "deterministic"

    async def observe(self, state):
        observation = await call(self.observer, state["route_name"], self.goal(state))
        return self.store.put_payload(state["task_id"], "observation", observation)

    async def propose(self, state):
        observations = [
            self.store.payload(state["task_id"], "observation", ref)
            for ref in state["observation_refs"][-4:]
        ]
        route = self.route_plan(state)
        deterministic = route is not None and route.mode == "deterministic"
        if deterministic:
            index = len(state["action_ledger_refs"])
            decision = (
                ActionDecision(decision="action", action=route.steps[index].model_dump())
                if index < len(route.steps)
                else FinishDecision(
                    decision="finish", status="completed", reason="Workflow exhausted; verify goal"
                )
            )
            result = PlanningResult(decision, 0, 0)
        else:
            outcomes = []
            if state["action_ledger_refs"]:
                ledger = self.context_factory(state).ledger
                for action_id in state["action_ledger_refs"][-4:]:
                    record = ledger.get(action_id)
                    if record is not None:
                        outcomes.append(
                            {
                                "tool": record.tool_name,
                                "status": record.status,
                                "error_code": record.error_code,
                            }
                        )
            preferences = await call(self.preferences, state) if self.preferences else []
            planning_state = {
                **state,
                "planning_inputs": {
                    "relevant_tools": route.tool_names if route else None,
                    "outcomes": outcomes,
                    "preferences": preferences,
                },
            }
            result = await call(self.planner, self.goal(state), observations, planning_state)
        if not isinstance(result, PlanningResult):
            raise ValueError("Typed planning result required")
        left = state["remaining"]
        if (
            type(result.requests) is not int
            or not (0 if deterministic else 1) <= result.requests <= min(2, left["model_requests"])
            or type(result.output_tokens) is not int
            or not (0 if deterministic else 1) <= result.output_tokens <= left["output_tokens"]
            or type(result.repairs) is not int
            or not 0 <= result.repairs <= min(left["schema_repairs"], max(0, result.requests - 1))
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
        route = self.route_plan(state)
        if route is not None and action.tool not in route.tool_names:
            return False
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
        if result is False:
            return "denied", None
        context = self.context_factory(state)
        tool = self.dispatcher.registry.get(decision.action.tool)
        arguments = tool.argument_model.model_validate(decision.action.arguments).model_dump()
        action_id = context.ledger.prepare_action(
            tool.name, tool.version, arguments, expected_effect_ref=f"task:{state['task_id']}"
        )
        binding = await self.binding(state, action_id)
        store = self.approvals(state)
        record = store.request(
            binding,
            {"tool": tool.name, "arguments": arguments, "target": binding.target_identity},
            ttl_seconds=state["remaining"]["approval_timeout_seconds"],
        )
        # Consequential tools always require explicit non-voice human review.
        if result is True and tool.risk_floor not in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            store.decide(record.approval_id, binding, approved=True)
            return "approved", record.approval_id
        return "pending", record.approval_id

    async def execution(self, state):
        """Prepare dispatcher inputs; recheck live validation and exact approval binding."""
        approvals = self.approvals(state)
        approval = approvals.get(state["approval_ref"])
        if approval is None or approval.task_id != state["task_id"]:
            raise PermissionError("Approval unavailable")
        permits = PermitStore(approvals)
        try:
            binding = await self.binding(state, approval.action_id)
            permits.validate_binding(approval.approval_id, binding)
        except (PermissionError, ValueError):
            approvals.invalidate(approval.approval_id)
            raise
        action = self.decision(state).action
        if await call(self.authorizer, state, action) is False:
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
        context.prepared_action_id = approval.action_id
        context.permits = permits
        context.approval_binding = binding
        context.permit_token = permits.issue_permit(approval.approval_id, binding)
        context.revalidate_binding = lambda: self.binding(state, approval.action_id)
        context.deadline = min(
            context.deadline,
            time.monotonic() + seconds_left(state["remaining"]),
        )
        return action, context

    def reconcile_interrupted(self, state):
        from victus.recovery.resume import ResumeManager

        context = self.context_factory(state)
        ResumeManager(context.ledger, self.approvals(state)).invalidate(state["task_id"])
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
            await self.reconcile_effects(state["action_ledger_refs"])
            return "stop"
        return await call(self.recovery, state) if self.recovery else "stop"

    async def reconcile_effects(self, references):
        if self.reconciler is not None:
            for action_id in references:
                record = self.reconciler.ledger.get(action_id)
                if record is not None and record.status in {"dispatching", "applied", "unknown"}:
                    await self.reconciler.reconcile(action_id, quiesced=True)
