"""Protected durable clarification and idempotent handoff to the existing task queue."""

import re
import sqlite3
import time
from uuid import uuid4

from victus.agent.commands import (
    COMMAND_TOOL,
    CommandFields,
    CommandReference,
    CommandResponse,
    CommandSubmission,
    action_for,
    interpret,
)
from victus.storage.secure_json import decode, encode
from victus.tools.contracts import ToolRequest
from victus.workflows.common import new_destination


class CommandService:
    def __init__(self, tasks, model_pin=None):
        self.tasks, self.model_pin = tasks, model_pin

    def model_ready(self):
        from victus.models.ollama import installed_pin_available

        return installed_pin_available(self.model_pin)

    def response(self, row):
        mapping = self.tasks.queue.get_by_client_request_id("command_" + row["command_id"])
        if mapping or row["task_id"]:
            return CommandResponse(
                command_id=row["command_id"],
                state="submitted",
                task_id=mapping or row["task_id"],
                message="Task submitted. Review its verified result.",
            )
        if (
            row["expires_at"] <= time.time()
            or row["payload"] is None
            or row["state"] == "invalidated"
        ):
            return CommandResponse(
                command_id=row["command_id"],
                state="expired",
                message="Clarification expired; submit a new command.",
            )
        if self.tasks.stopped.is_set():
            return CommandResponse(
                command_id=row["command_id"],
                state="stopped",
                message="Service stopped; no command admitted.",
            )
        saved = decode(row["payload"])
        submission = CommandSubmission.model_validate(saved.get("submission", saved))
        fields, missing = interpret(submission)
        if not missing:
            try:
                action_for(fields, self.tasks)
                if submission.reasoning and not self.model_ready():
                    raise PermissionError("Pinned local reasoning model unavailable")
            except PermissionError as error:
                return CommandResponse(
                    command_id=row["command_id"], state="unavailable", message=str(error)
                )
        return CommandResponse(
            command_id=row["command_id"],
            state="clarification",
            missing=missing,
            message="Provide the missing values before any action."
            if missing
            else "Ready; explicitly resume to submit.",
        )

    def get_row(self, command_id):
        with self.tasks.database.connect() as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT * FROM command_intakes WHERE command_id=?", (command_id,)
            ).fetchone()
        if row is None:
            raise KeyError(command_id)
        return dict(row)

    def get(self, command_id):
        return self.response(self.get_row(command_id))

    def submit(self, submission, request_id, *, origin="typed", review_corrected=None):
        if origin not in {"typed", "voice"}:
            raise ValueError("Unknown command origin")
        if request_id.startswith("voice-") != (origin == "voice"):
            raise ValueError("Voice request identity is server-owned")
        if review_corrected is not None and (
            origin != "voice" or type(review_corrected) is not bool
        ):
            raise ValueError("Correction metadata is server-owned voice provenance")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id):
            raise ValueError("Invalid request identity")
        with self.tasks.queue._admission_lock:
            with self.tasks.database.connect() as db:
                row = db.execute(
                    "SELECT command_id FROM command_intakes WHERE request_id=?", (request_id,)
                ).fetchone()
                if row:
                    return self.get(row[0])
                if (
                    db.execute(
                        "SELECT count(*) FROM command_intakes WHERE expires_at>? AND task_id IS NULL",
                        (time.time(),),
                    ).fetchone()[0]
                    >= 128
                ):
                    raise ValueError("Command clarification capacity reached")
                interpret(submission)
                command_id = uuid4().hex
                db.execute(
                    "INSERT INTO command_intakes VALUES(?,?,?,?,?,?)",
                    (
                        command_id,
                        request_id,
                        encode(
                            {
                                "submission": submission.model_dump(),
                                "origin": origin,
                                "review_corrected": review_corrected,
                            }
                        ),
                        "waiting",
                        None,
                        time.time() + 300,
                    ),
                )
            return self.complete(command_id, CommandFields())

    def complete(self, command_id, answers):
        with self.tasks.queue._admission_lock:
            row = self.get_row(command_id)
            existing = self.response(row)
            if existing.state in {"submitted", "expired"}:
                return existing
            if self.tasks.stopped.is_set():
                return CommandResponse(
                    command_id=command_id,
                    state="stopped",
                    message="Service stopped; no command admitted.",
                )
            saved = decode(row["payload"])
            corrected = saved.get("review_corrected")
            if saved.get("origin") == "voice" and answers.model_dump(exclude_none=True):
                corrected = True
            submission = CommandSubmission.model_validate(saved.get("submission", saved))
            if row["state"] == "waiting":
                fields, _ = interpret(submission)
                for key, value in answers.model_dump(exclude_none=True).items():
                    previous = getattr(fields, key)
                    if previous is not None and previous != value:
                        raise ValueError("Clarification cannot replace an already specified value")
                    setattr(fields, key, value)
                submission = submission.model_copy(
                    update={"fields": CommandFields.model_validate(fields.model_dump())}
                )
                fields, missing = interpret(submission)
                if not missing:
                    # Reject bad answers before making previously missing values immutable.
                    try:
                        action_for(fields, self.tasks)
                    except PermissionError:
                        pass  # Confirmed but unavailable capabilities remain explicitly gated.
                    new_destination(self.tasks.workspace, fields.filename)
                with self.tasks.database.connect() as db:
                    db.execute(
                        "UPDATE command_intakes SET payload=?,state=? WHERE command_id=?",
                        (
                            encode(
                                {
                                    "submission": submission.model_dump(),
                                    "origin": saved.get("origin", "typed"),
                                    "review_corrected": corrected,
                                }
                            ),
                            "waiting" if missing else "ready",
                            command_id,
                        ),
                    )
                if missing:
                    return self.get(command_id)
            else:
                fields, missing = interpret(submission)
            try:
                action = action_for(fields, self.tasks)
                if submission.reasoning and not self.model_ready():
                    raise PermissionError("Pinned local reasoning model unavailable")
            except PermissionError as error:
                return CommandResponse(
                    command_id=command_id, state="unavailable", message=str(error)
                )
            new_destination(self.tasks.workspace, fields.filename)
            # The canonical action is server-derived and protected; never accept model/tool data here.
            payload = {
                "origin": saved.get("origin", "typed"),
                "review_corrected": corrected,
                "submission": submission.model_dump(),
                "action": action.model_dump(),
                "model_pin": self.model_pin.model_dump() if self.model_pin else None,
            }
            with self.tasks.database.connect() as db:
                db.execute(
                    "UPDATE command_intakes SET payload=?,state=? WHERE command_id=?",
                    (encode(payload), "ready", command_id),
                )
            from victus.agent.command_execution import command_spec

            internal_tool = COMMAND_TOOL + "." + command_id
            if internal_tool not in self.tasks.registry.names():
                if sum(not spec.public for spec in self.tasks.registry.tools()) >= 128:
                    raise ValueError("Command session capacity reached")
                self.tasks.registry.register(
                    command_spec(
                        internal_tool, self.tasks.registry.get(action.tool), action, self.model_pin
                    )
                )
            task_id, _ = self.tasks.queue.submit(
                ToolRequest(
                    tool=internal_tool,
                    arguments=CommandReference(command_id=command_id).model_dump(),
                ),
                "command_" + command_id,
            )
            with self.tasks.database.connect() as db:
                db.execute(
                    "UPDATE command_intakes SET task_id=?,state=? WHERE command_id=?",
                    (task_id, "submitted", command_id),
                )
            return CommandResponse(
                command_id=command_id,
                state="submitted",
                task_id=task_id,
                message="Task submitted. Review its verified result.",
            )
