"""Bounded StateGraph, persistent checkpoints and no automatic effect replay."""

from __future__ import annotations

import asyncio
import importlib
import time
from contextlib import asynccontextmanager

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph

from victus.agent.state import AgentState, Snapshot, initial_state

NODES = (
    "intake",
    "route",
    "observe",
    "propose",
    "validate",
    "authorize",
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
    "authorize": ("execute", "failed", "finalize", "end"),
    "execute": ("verify", "failed", "finalize"),
    "verify": ("observe", "failed", "finalize"),
    "failed": ("recover", "finalize"),
    "recover": ("observe", "propose", "finalize"),
    "finalize": ("end",),
}


def _stop(state, code, status="blocked"):
    return {"status": status, "error_code": code, "next_node": "finalize", "approval_ref": None}


def charge_uncertain(state, name):
    left = state["remaining"].copy()
    left["nodes"] = max(0, left["nodes"] - 1)
    if name == "propose":
        left.update(
            model_requests=max(0, left["model_requests"] - 2),
            output_tokens=max(0, left["output_tokens"] - 1024),
            schema_repairs=0,
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
                "remaining": charge_uncertain(state, name),
            }
            if name == "execute":
                result["action_ledger_refs"] = services.reconcile_interrupted(state)
            if name == "finalize":
                result["next_node"] = "end"
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
            elif name != "finalize" and (
                remaining["nodes"] <= 0 or remaining["deadline_epoch"] <= time.time()
            ):
                result = _stop(
                    state,
                    "AGENT_BUDGET_EXHAUSTED",
                    "unknown" if state["status"] == "unknown" else "blocked",
                )
            elif (
                (name == "execute" and remaining["actions"] <= 0)
                or (name == "observe" and remaining["observations"] <= 0)
                or (
                    name == "propose"
                    and (remaining["model_requests"] <= 0 or remaining["output_tokens"] <= 0)
                )
                or (name == "recover" and remaining["recoveries"] <= 0)
            ):
                result = _stop(
                    state,
                    "AGENT_BUDGET_EXHAUSTED",
                    "unknown" if state["status"] == "unknown" else "blocked",
                )
            else:
                async with asyncio.timeout(
                    max(0.001, min(60, remaining["deadline_epoch"] - time.time()))
                    if name != "finalize"
                    else 5
                ):
                    result = await perform(operation, state, services, name)
                if is_cancelled(services, task) and name != "finalize":
                    result.update(
                        _stop(
                            state,
                            "AGENT_CANCELLED",
                            "unknown" if name == "execute" else "cancelled",
                        )
                    )
                    result["cancellation_requested"] = True
        except _Stopped:
            result = {
                **_stop(state, "AGENT_CANCELLED", "unknown" if name == "execute" else "cancelled"),
                "cancellation_requested": True,
                "remaining": charge_uncertain(state, name),
            }
            if name == "execute":
                result.update(
                    execution_status="unknown",
                    action_ledger_refs=services.reconcile_interrupted(state),
                )
        except asyncio.CancelledError:
            # Leave a running journal record; a restart must not repeat this operation.
            raise
        except Exception:
            result = {"error_code": "NODE_OPERATION_FAILED", "next_node": "failed"}
            result["remaining"] = charge_uncertain(state, name)
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
        result["sequence"] = sequence + 1
        left = result.get("remaining", remaining).copy()
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
        return {"configurable": {"thread_id": task_id}, "recursion_limit": 300}

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
                # Revalidate the exact proposal before requesting current policy approval.
                await self.graph.aupdate_state(
                    config,
                    {
                        "status": "running",
                        "approval_ref": None,
                        "next_node": "validate",
                        "sequence": snapshot.values["sequence"] + 1,
                    },
                    as_node="propose",
                )
            elif not snapshot.next:
                return Snapshot.model_validate(snapshot.values).model_dump()
            result = await self.graph.ainvoke(state, config, durability="sync")
            return Snapshot.model_validate(result).model_dump()
        finally:
            self._active = False

    def cancel(self, task_id):
        self.services.store.cancel(task_id)


@asynccontextmanager
async def agent(services, *, interrupt_after=None):
    async with services.store.saver() as checkpointer:
        yield AgentRunner(
            build_graph(services, checkpointer, interrupt_after=interrupt_after), services
        )
