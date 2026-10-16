"""Deterministic domain services with the real dispatcher, ledger and filesystem."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from victus.agent.output_parser import OutputParser
from victus.agent.services import AgentServices, PlanningResult
from victus.storage.checkpoints import CheckpointStore
from victus.tools.dispatcher import Dispatcher
from victus.tools.registry import ToolRegistry
from victus.workflows.common import context_for, spec, write_new


class WriteArgs(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    filename: str
    text: str


class Fixture:
    def __init__(self, root: Path, *, decisions=None, crash=None):
        self.root = root
        self.workspace = root / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.store = CheckpointStore(root)
        self.task = "graph-task"
        self.observations = 0
        self.calls = 0
        self.approved = True
        self.valid = True
        self.plan_calls = 0
        self.recovery = "stop"
        self.crash = crash
        self.decisions = decisions if decisions is not None else [self.action("note.txt", "ready")]
        self.parser = OutputParser({"fixture.write": WriteArgs})
        registry = ToolRegistry()
        registry.register(
            spec("fixture.write", WriteArgs, self.execute, self.verify_action, "fixture:write")
        )
        self.dispatcher = Dispatcher(self.workspace, registry)
        self.services = AgentServices(
            store=self.store,
            dispatcher=self.dispatcher,
            parser=self.parser,
            context_factory=self.context,
            planner=self.plan,
            router=lambda goal: "fixture",
            observer=self.observe,
            validator=lambda state, action: self.valid,
            authorizer=lambda state, action: self.approved,
            goal_verifier=self.verify_goal,
            recovery=lambda state: self.recovery,
            target_identity=lambda state, action: self.services.file_target_identity(
                action.arguments["filename"]
            ),
        )

    @staticmethod
    def action(filename, text):
        return {
            "decision": "action",
            "action": {"tool": "fixture.write", "arguments": {"filename": filename, "text": text}},
        }

    def goal(self, expected=None):
        return self.store.put_payload(
            self.task, "goal", {"expected": expected or {"note.txt": "ready"}}
        )

    def resolve_review(self):
        """Explicit trusted review for tests; toggling policy is no longer approval."""
        store = self.services.approvals({"task_id": self.task})
        with store.connect() as db:
            rows = db.execute(
                "SELECT approval_id FROM approvals WHERE task_id=? AND state='pending'",
                (self.task,),
            ).fetchall()
        for row in rows:
            record = store.get(row[0])
            store.decide(record.approval_id, record.binding(), approved=True)

    def context(self, state):
        return context_for(
            self.workspace,
            state["task_id"],
            None,
            {"fixture:write"},
            lambda tool, args: self.approved is True,
        )

    def observe(self, route, goal):
        self.observations += 1
        return {"observation_id": uuid4().hex, "text": "Visible fixture; PRIVATE_OBSERVATION"}

    def plan(self, goal, observations, state):
        self.plan_calls += 1
        decision = self.parser.parse(__import__("json").dumps(self.decisions.pop(0)))
        return PlanningResult(decision, 1, 32)

    def execute(self, workspace, args):
        self.calls += 1
        write_new(workspace, args.filename, args.text.encode())
        if self.crash == "effect":
            import os

            os._exit(71)
        return {"filename": args.filename, "sha256": hashlib.sha256(args.text.encode()).hexdigest()}

    def verify_action(self, data, args):
        return (self.workspace / args.filename).read_bytes() == args.text.encode()

    def verify_goal(self, goal, receipts):
        return all(
            (self.workspace / name).is_file()
            and (self.workspace / name).read_bytes() == text.encode()
            for name, text in goal["expected"].items()
        )
