"""Loopback-only submission service with durable receipts and observable POST count."""

import hashlib
import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field

from victus.agent.output_parser import OutputParser
from victus.agent.services import AgentServices, PlanningResult
from victus.recovery.reconcile import EffectProof, Reconciler
from victus.storage.action_ledger import _canonical_hash
from victus.storage.checkpoints import CheckpointStore
from victus.tools.dispatcher import Dispatcher
from victus.tools.registry import RiskLevel, ToolRegistry
from victus.workflows.common import context_for, spec


@contextmanager
def submission_server(root, *, delay=0):
    path = root / "submission-receipts.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE receipts(operation_id TEXT PRIMARY KEY, receipt_id TEXT NOT NULL,
              recipient TEXT NOT NULL, content_hash TEXT NOT NULL);
            CREATE TABLE posts(id INTEGER PRIMARY KEY AUTOINCREMENT);
        """)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, data):
            encoded = json.dumps(data).encode()
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def do_POST(self):
            if self.path != "/submit":
                return self.reply(404, {})
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            with sqlite3.connect(path) as db:
                db.execute("INSERT INTO posts DEFAULT VALUES")
                db.execute(
                    "INSERT OR IGNORE INTO receipts VALUES (?,?,?,?)",
                    (
                        body["operation_id"],
                        uuid4().hex,
                        body["recipient"],
                        hashlib.sha256(body["content"].encode()).hexdigest(),
                    ),
                )
                row = db.execute(
                    "SELECT * FROM receipts WHERE operation_id=?", (body["operation_id"],)
                ).fetchone()
            time.sleep(delay)  # The receipt is already committed before the lost response.
            self.reply(
                200, dict(zip(("operation_id", "receipt_id", "recipient", "content_hash"), row))
            )

        def do_GET(self):
            operation_id = self.path.removeprefix("/receipts/")
            with sqlite3.connect(path) as db:
                row = db.execute(
                    "SELECT * FROM receipts WHERE operation_id=?", (operation_id,)
                ).fetchone()
            self.reply(
                200 if row else 404,
                dict(zip(("operation_id", "receipt_id", "recipient", "content_hash"), row))
                if row
                else {},
            )

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    server.receipt_path = path
    server.url = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.02), daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class SubmitArguments(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    operation_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    recipient: str = Field(pattern=r"^[a-z]+@fixture\.invalid$")
    content: str = Field(min_length=1, max_length=200)


class SubmissionFixture:
    def __init__(self, root, server):
        self.server = server
        self.workspace = root / "workspace"
        self.workspace.mkdir(exist_ok=True)
        self.store = CheckpointStore(root)
        self.task = "submission-task"
        self.recipient = "reviewer@fixture.invalid"
        self.args = {
            "operation_id": uuid4().hex,
            "recipient": self.recipient,
            "content": "Approved fixture content",
        }
        registry = ToolRegistry()
        registry.register(
            spec(
                "fixture.submit",
                SubmitArguments,
                self.submit,
                self.verify,
                "fixture:submit",
                risk=RiskLevel.HIGH,
                timeout=1,
            )
        )
        self.dispatcher = Dispatcher(self.workspace, registry)
        self.parser = OutputParser({"fixture.submit": SubmitArguments})
        self.reconciler = Reconciler(
            self.context({"task_id": self.task}).ledger,
            self.context({"task_id": self.task}).payloads,
            timeout_seconds=3,
        )
        self.reconciler.register("fixture.submit", "0.1.0", self.probe)
        self.services = AgentServices(
            self.store,
            self.dispatcher,
            self.parser,
            self.context,
            self.plan,
            lambda _: "submission",
            lambda *_: {"observation_id": "observed-recipient"},
            lambda state, action: action.arguments["recipient"] == self.recipient,
            lambda *_: True,
            self.goal_verified,
            target_identity=lambda *_: "recipient:" + self.recipient,
            reconciler=self.reconciler,
        )

    def context(self, state):
        return context_for(
            self.workspace, state["task_id"], None, {"fixture:submit"}, lambda *_: True
        )

    def goal(self):
        return self.store.put_payload(
            self.task, "goal", {"operation_id": self.args["operation_id"]}
        )

    def plan(self, *_):
        decision = self.parser.parse(
            json.dumps(
                {
                    "decision": "action",
                    "action": {
                        "tool": "fixture.submit",
                        "arguments": self.args,
                    },
                }
            )
        )
        return PlanningResult(decision, 1, 64)

    async def submit(self, _, arguments):
        async with httpx.AsyncClient(trust_env=False, timeout=5) as client:
            response = await client.post(self.server.url + "/submit", json=arguments.model_dump())
            response.raise_for_status()
            return response.json()

    async def verify(self, output, args):
        proof = await self.probe(None, args.model_dump())
        return proof.verdict == "present" and proof.evidence["receipt_id"] == output["receipt_id"]

    async def probe(self, record, arguments):
        async with httpx.AsyncClient(trust_env=False, timeout=1) as client:
            response = await client.get(self.server.url + "/receipts/" + arguments["operation_id"])
        if response.status_code == 404:
            return EffectProof(
                "absent",
                {"lookup": "authoritative_not_found", "operation_id": arguments["operation_id"]},
            )
        response.raise_for_status()
        receipt = response.json()
        if (
            receipt["operation_id"] != arguments["operation_id"]
            or receipt["recipient"] != arguments["recipient"]
            or receipt["content_hash"] != hashlib.sha256(arguments["content"].encode()).hexdigest()
        ):
            return EffectProof("unknown")
        return EffectProof(
            "present",
            {
                "receipt_id": receipt["receipt_id"],
                "operation_id": receipt["operation_id"],
                "arguments_hash": _canonical_hash(arguments),
            },
        )

    async def goal_verified(self, goal, receipts):
        return bool(receipts) and (await self.probe(None, self.args)).verdict == "present"

    def counts(self):
        with sqlite3.connect(self.server.receipt_path) as db:
            return (
                db.execute("SELECT count(*) FROM posts").fetchone()[0],
                db.execute("SELECT count(*) FROM receipts").fetchone()[0],
            )
