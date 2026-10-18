"""Existing bounded LangGraph inside the one queued worker; one exact admitted action."""

import hashlib
import time
from dataclasses import dataclass

from victus.agent.budgets import Budgets
from victus.agent.commands import CommandReference, CommandSubmission
from victus.agent.graph import agent
from victus.agent.output_parser import OutputParser
from victus.agent.router import CommandRouter, RoutePlan
from victus.agent.services import AgentServices, GatewayPlanner
from victus.models.ollama import OllamaClient
from victus.storage.checkpoints import CheckpointStore
from victus.storage.database import Database
from victus.storage.secure_json import decode
from victus.tools.contracts import ToolRequest
from victus.tools.dispatcher import Dispatcher
from victus.tools.registry import RetryClass, RiskLevel, ToolRegistry, ToolSpec
from victus.workflows.common import context_for


def saved_intent(workspace, command_id):
    store = Database.attach(workspace.parent)
    with store.connect() as db:
        row = db.execute(
            "SELECT payload,expires_at FROM command_intakes WHERE command_id=?", (command_id,)
        ).fetchone()
    if row is None or row[0] is None or row[1] <= time.time():
        raise PermissionError("Command intent expired")
    return decode(row[0])


@dataclass(frozen=True)
class CommandExecutor:
    tool: ToolSpec
    expected: ToolRequest
    model_pin: object = None

    async def __call__(self, workspace, reference, cancelled, authority):
        payload = saved_intent(workspace, reference.command_id)
        if ToolRequest.model_validate(payload["action"]) != self.expected:
            raise PermissionError("Confirmed command changed")
        submission = CommandSubmission.model_validate(payload["submission"])
        registry = ToolRegistry()
        registry.register(self.tool)
        dispatcher = Dispatcher(workspace, registry)
        store = CheckpointStore(workspace.parent)
        parser = OutputParser({self.tool.name: self.tool.argument_model})
        provider = OllamaClient() if submission.reasoning and self.model_pin is not None else None

        def context(state):
            ctx = context_for(
                workspace, authority.task_id, cancelled, {"fs:write"}, lambda *_: True
            )
            ctx.resource_owned = True
            return ctx

        def validate(state, action):
            return action.tool == self.expected.tool and action.arguments == self.expected.arguments

        async def verify(goal, receipts):
            if not receipts:
                return False
            ledger = context({}).ledger
            attempt = ledger.get(receipts[-1]["action_id"])
            if (
                attempt is None
                or attempt.status != "verified"
                or attempt.tool_name != self.expected.tool
            ):
                return False
            target = workspace / self.expected.arguments["filename"]
            if (
                not target.is_file()
                or target.is_symlink()
                or attempt.sha256 != hashlib.sha256(target.read_bytes()).hexdigest()
            ):
                return False
            args = self.tool.argument_model.model_validate(self.expected.arguments, strict=True)
            return self.tool.verify(target, args) is True

        async def unavailable(*_):
            raise PermissionError("Pinned local model unavailable")

        router = CommandRouter(
            {self.tool.name: self.tool.argument_model},
            workflow_bindings={"selected_workflow": self.tool.name},
        )
        route = (
            (
                lambda goal: RoutePlan(
                    name="bounded_local", mode="agent", tool_names=[self.tool.name]
                )
            )
            if submission.reasoning
            else router
        )
        services = AgentServices(
            store=store,
            dispatcher=dispatcher,
            parser=parser,
            context_factory=context,
            planner=GatewayPlanner(provider, self.model_pin, parser, cancelled)
            if provider
            else unavailable,
            router=route,
            observer=lambda route_name, goal: {
                "observation_id": "confirmed-intent",
                "confirmed_action": self.expected.model_dump(),
            },
            validator=validate,
            authorizer=lambda state, action: validate(state, action),
            goal_verifier=verify,
            cancelled=cancelled,
            target_identity=lambda state, action: services.file_target_identity(
                self.expected.arguments["filename"]
            ),
        )
        goal = {
            "workflow": "selected_workflow",
            "arguments": self.expected.arguments,
            "request": submission.text,
        }
        goal_ref = store.put_payload(authority.task_id, "goal", goal)
        try:
            async with agent(services) as runner:
                result = await runner.start(
                    authority.task_id,
                    goal_ref,
                    budgets=Budgets(
                        nodes=32,
                        actions=1,
                        observations=4,
                        model_requests=2,
                        output_tokens=1024,
                        recoveries=0,
                        active_seconds=60.0,
                        approval_timeout_seconds=30.0,
                    ),
                )
            if (
                result["status"] != "succeeded"
                or not result["completion_verified"]
                or not result["evidence_refs"]
            ):
                raise RuntimeError("Command effects not independently verified")
            return workspace / self.expected.arguments["filename"]
        finally:
            if provider is not None:
                await provider.close()

    def verify(self, path, reference):
        payload = saved_intent(path.parent, reference.command_id)
        if (
            payload["action"] != self.expected.model_dump()
            or path.name != self.expected.arguments["filename"]
        ):
            return False
        return self.tool.verify(
            path, self.tool.argument_model.model_validate(self.expected.arguments)
        )


def reject_unowned(*_):
    raise PermissionError("Queued owner required")


def command_spec(name, tool, action, model_pin=None):
    executor = CommandExecutor(tool, action, model_pin)
    return ToolSpec(
        name=name,
        version="0.1.0",
        description="One confirmed bounded command",
        argument_model=CommandReference,
        risk_floor=RiskLevel.LOW,
        required_scope="fs:write",
        timeout_seconds=120,
        resource_name="workflow_owner",
        retry_class=RetryClass.NONE,
        execute=reject_unowned,
        execute_owned=executor,
        verify=executor.verify,
        public=False,
    )
