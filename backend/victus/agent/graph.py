"""Bounded StateGraph, persistent checkpoints and no automatic effect replay."""

from __future__ import annotations

import asyncio
import importlib
import time
from contextlib import asynccontextmanager

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.errors import GraphInterrupt, GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from victus.agent.budgets import (
    Budgets,
    charge_planning,
    charge_time,
    resume_approval,
    seconds_left,
    stopped_status,
)
from victus.agent.services import PlanningFailure
from victus.agent.state import AgentState, Snapshot, initial_state

NODES = (
    "intake",
    "route",
    "observe",
    "propose",
    "validate",
    "authorize",
    "review",
    "execute",
    "verify",
    "failed",
    "recover",
    "finalize",
)
EDGES = {
    "intake": ("route", "failed", "finalize"),
    "route": ("observe", "failed", "finalize"),
    "observe": ("propose", "failed", "finalize"),
    "propose": ("validate", "failed", "finalize"),
    "validate": ("authorize", "verify", "failed", "finalize"),
    "authorize": ("execute", "review", "failed", "finalize", "end"),
    "review": ("execute", "finalize"),
    "execute": ("verify", "failed", "finalize"),
    "verify": ("observe", "failed", "finalize"),
    "failed": ("recover", "finalize"),
    "recover": ("observe", "propose", "finalize"),
    "finalize": ("end",),
}


def _stop(state, code, status="blocked"):
    return {"status": status, "error_code": code, "next_node": "finalize", "approval_ref": None}


def charge_uncertain(state, name, services=None):
    left = state["remaining"].copy()
    left["nodes"] = max(0, left["nodes"] - 1)
    if name == "propose" and not (services and services.is_deterministic(state)):
        left.update(
            model_requests=max(0, left["model_requests"] - 2),
            output_tokens=max(0, left["output_tokens"] - 1024),
            repairs_used=left["repairs_used"]
            + min(left["schema_repairs"], left["model_requests"] // 2),
        )
    if name == "execute":
        left["actions"] = max(0, left["actions"] - 1)
    if name == "observe":
        left["observations"] = max(0, left["observations"] - 1)
    return left


class _Stopped(Exception):
    pass


def is_cancelled(services, task):
    if services.cancelled is not None and services.cancelled.is_set():
        services.store.cancel(task)
    return services.store.cancelled(task)


async def perform(operation, state, services, name):
    pending = asyncio.create_task(operation(state, services))
    try:
        while not pending.done():
            if name != "finalize" and is_cancelled(services, state["task_id"]):
                raise _Stopped
            await asyncio.wait({pending}, timeout=0.02)
        return pending.result()
    finally:
        if not pending.done():
            pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)


def guarded(name, operation, services):
    async def node(raw):
        started = time.monotonic()
        state = Snapshot.model_validate(raw).model_dump()
        task, sequence = state["task_id"], state["sequence"]
        claimed, cached = services.store.claim(task, sequence, name)
        if claimed == "complete":
            return cached
        if claimed == "interrupted":
            result = {
                **_stop(state, "NODE_INTERRUPTED_REQUIRES_REVIEW", "unknown"),
                "sequence": sequence + 1,
                "execution_status": "unknown",
                "remaining": charge_uncertain(state, name, services),
            }
            if name == "execute":
                result["action_ledger_refs"] = services.reconcile_interrupted(state)
                await services.reconcile_effects(result["action_ledger_refs"])
            if name == "finalize":
                result["next_node"] = "end"
            result["remaining"] = charge_time(result["remaining"], time.monotonic() - started)
            services.store.complete(task, sequence, result)
            return result
        remaining = state["remaining"]
        try:
            stopped = state["cancellation_requested"] or is_cancelled(services, task)
            if name != "finalize" and stopped:
                result = {
                    **_stop(
                        state,
                        "AGENT_CANCELLED",
                        "unknown" if state["execution_status"] == "unknown" else "cancelled",
                    ),
                    "cancellation_requested": True,
                }
            elif (
                name != "finalize"
                and remaining["approval_expires_epoch"] is not None
                and time.time() >= remaining["approval_expires_epoch"]
            ):
                result = _stop(state, "APPROVAL_WAIT_EXPIRED", stopped_status(state))
            elif name != "finalize" and (remaining["nodes"] <= 0 or seconds_left(remaining) <= 0):
                result = _stop(
                    state,
                    "AGENT_BUDGET_EXHAUSTED",
                    stopped_status(state),
                )
            elif (
                (name == "execute" and remaining["actions"] <= 0)
                or (name == "observe" and remaining["observations"] <= 0)
                or (
                    name == "propose"
                    and not services.is_deterministic(state)
                    and (remaining["model_requests"] <= 0 or remaining["output_tokens"] <= 0)
                )
                or (name == "recover" and remaining["recoveries"] <= 0)
            ):
                result = _stop(
                    state,
                    "NO_PROGRESS"
                    if state["progress"]["recovery_pending"]
                    else "AGENT_BUDGET_EXHAUSTED",
                    stopped_status(state, partial=state["progress"]["recovery_pending"]),
                )
            else:
                async with asyncio.timeout(
                    max(0.001, min(60, seconds_left(remaining))) if name != "finalize" else 5
                ):
                    result = await perform(operation, state, services, name)
                if is_cancelled(services, task) and name != "finalize":
                    result.update(
                        _stop(
                            state,
                            "AGENT_CANCELLED",
                            "unknown"
                            if name == "execute"
                            and result.get("execution_status") not in {"blocked", "cancelled"}
                            else "cancelled",
                        )
                    )
                    result["cancellation_requested"] = True
        except _Stopped:
            result = {
                **_stop(state, "AGENT_CANCELLED", "unknown" if name == "execute" else "cancelled"),
                "cancellation_requested": True,
                "remaining": charge_uncertain(state, name, services),
            }
            if name == "execute":
                result.update(
                    execution_status="unknown",
                    action_ledger_refs=services.reconcile_interrupted(state),
                )
        except (asyncio.CancelledError, GraphInterrupt):
            # Leave a running journal record; a restart must not repeat this operation.
            raise
        except Exception as error:
            result = {"error_code": "NODE_OPERATION_FAILED", "next_node": "failed"}
            result["remaining"] = charge_uncertain(state, name, services)
            if isinstance(error, PlanningFailure):
                used = error.usage
                result["remaining"] = charge_planning(
                    remaining,
                    used["requests"],
                    used["reserved_output_tokens"],
                    used["schema_repairs"],
                )
            if name in {"execute", "verify"}:
                result.update(status="unknown", execution_status="unknown")
            if name == "execute":
                result["action_ledger_refs"] = services.reconcile_interrupted(state)
                result["remaining"] = {**remaining, "actions": max(0, remaining["actions"] - 1)}
            if name in {"failed", "recover", "finalize"}:
                result.update(
                    status="unknown" if state["status"] == "unknown" else "failed",
                    next_node="finalize" if name != "finalize" else "end",
                )
            if isinstance(error, TimeoutError) and time.monotonic() - started >= seconds_left(
                remaining
            ):
                result.update(
                    error_code="AGENT_ACTIVE_TIME_EXHAUSTED",
                    next_node="finalize",
                    status="unknown" if name == "execute" else stopped_status(state),
                )
        result["sequence"] = sequence + 1
        left = charge_time(result.get("remaining", remaining), time.monotonic() - started)
        left["nodes"] = max(0, remaining["nodes"] - 1)
        result["remaining"] = left
        Snapshot.model_validate({**state, **result})
        services.store.complete(task, sequence, result)
        return result

    return node


def build_graph(services, checkpointer, *, interrupt_after=None):
    if not isinstance(checkpointer, AsyncSqliteSaver):
        raise TypeError("A persistent SQLite checkpointer is required")
    builder = StateGraph(AgentState)
    for name in NODES:
        operation = importlib.import_module(f"victus.agent.nodes.{name}").run
        if name == "review":
            # LangGraph must own interrupt replay; do not claim a node-journal
            # entry or catch GraphInterrupt at this pure review boundary.
            async def review(state):
                from victus.agent.nodes.review import run

                return await run(state, services)

            builder.add_node(name, review)
        else:
            builder.add_node(name, guarded(name, operation, services))
    builder.add_edge(START, "intake")
    for name, destinations in EDGES.items():
        builder.add_conditional_edges(
            name,
            lambda state: state["next_node"],
            {dest: END if dest == "end" else dest for dest in destinations},
        )
    return builder.compile(checkpointer=checkpointer, interrupt_after=interrupt_after)


class AgentRunner:
    """One active invocation per owner; callers never submit checkpoint state on resume."""

    def __init__(self, graph, services):
        self.graph, self.services = graph, services
        self._active = False

    def config(self, task_id):
        return {
            "configurable": {"thread_id": task_id},
            "recursion_limit": Budgets().recursion_limit,
        }

    async def start(self, task_id, goal_payload_ref, *, budgets=None):
        state = initial_state(task_id, goal_payload_ref, budgets)
        return await self._invoke(task_id, state, new=True)

    async def resume(self, task_id):
        return await self._invoke(task_id, None)

    async def _invoke(self, task_id, state, new=False):
        if self._active:
            raise RuntimeError("Agent runner already active")
        self._active = True
        try:
            config = self.config(task_id)
            snapshot = await self.graph.aget_state(config)
            if new:
                self.services.store.register(task_id)
            elif not snapshot.values:
                raise KeyError("Unknown agent checkpoint")
            elif snapshot.values["status"] == "awaiting_approval":
                saved = Snapshot.model_validate(snapshot.values).model_dump()
                record = self.services.approvals(saved).get(saved["approval_ref"])
                resumed, valid = resume_approval(saved["remaining"])
                cancelled = is_cancelled(self.services, task_id)
                if (
                    record
                    and record.state == "pending"
                    and valid
                    and seconds_left(resumed) > 0
                    and not cancelled
                ):
                    # Polling cannot authorize, renew expiry or replay preparation.
                    return saved
                state = Command(resume=True)
            elif not snapshot.next:
                return Snapshot.model_validate(snapshot.values).model_dump()
            allowance = (
                state["remaining"]
                if new
                else Snapshot.model_validate(snapshot.values).remaining.model_dump()
            )
            config["recursion_limit"] = allowance["recursion_limit"]
            try:
                result = await self.graph.ainvoke(state, config, durability="sync")
            except GraphRecursionError:
                latest = await self.graph.aget_state(config)
                result = Snapshot.model_validate(latest.values).model_dump()
                result.update(_stop(result, "GRAPH_RECURSION_EXHAUSTED", stopped_status(result)))
                result.update(next_node="end", sequence=result["sequence"] + 1)
                await self.graph.aupdate_state(config, result, as_node="finalize")
            latest = await self.graph.aget_state(config)
            return Snapshot.model_validate(latest.values).model_dump()
        finally:
            self._active = False

    def cancel(self, task_id):
        self.services.dispatcher.cancel_task(lambda: self.services.store.cancel(task_id))


@asynccontextmanager
async def agent(services, *, interrupt_after=None):
    async with services.store.saver() as checkpointer:
        yield AgentRunner(
            build_graph(services, checkpointer, interrupt_after=interrupt_after), services
        )
