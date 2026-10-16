from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from victus.adapters.playwright.downloads import read_reviewed_file
from victus.storage.action_ledger import ActionLedger
from victus.storage.database import Database
from victus.storage.payloads import PayloadStore
from victus.tasks.events import EventManager
from victus.tools.contracts import ActionProposal
from victus.tools.registry import RetryClass, RiskLevel, ToolSpec
from victus.tools.steps import StepContext


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


@dataclass(frozen=True)
class WorkflowResult:
    status: str
    output_name: str | None = None
    error_code: str | None = None
    observed_sources: int = 0
    actions: tuple[str, ...] = field(default_factory=tuple)


class StepFailed(RuntimeError):
    def __init__(self, outcome):
        self.outcome = outcome


async def step(dispatcher, context, tool, **arguments):
    outcome = await dispatcher.dispatch_step(
        ActionProposal(tool=tool, arguments=arguments), context
    )
    if not outcome.verified:
        raise StepFailed(outcome)
    return outcome.data


def spec(name, model, execute, verify, scope, *, risk=RiskLevel.MEDIUM, timeout=10):
    return ToolSpec(
        name=name,
        version="0.1.0",
        description=f"Workflow step: {name}",
        argument_model=model,
        execute=execute,
        verify=verify,
        risk_floor=risk,
        required_scope=scope,
        timeout_seconds=timeout,
        resource_name="workflow_owner",
        retry_class=RetryClass.NONE,
    )


def context_for(workspace, task_id, cancelled, scopes, authorize):
    database = Database(workspace.parent)
    return StepContext(
        task_id=task_id,
        scopes=frozenset(scopes),
        authorize=authorize,
        ledger=ActionLedger(database.path),
        payloads=PayloadStore(database.path),
        events=EventManager(database.path),
        cancelled=cancelled,
    )


def new_destination(workspace: Path, filename: str) -> Path:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.(txt|json)", filename) is None:
        raise PermissionError("Unsafe artifact name")
    stem = filename.split(".")[0].upper()
    if stem in {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"{p}{n}" for p in ("COM", "LPT") for n in range(1, 10)),
    }:
        raise PermissionError("Reserved artifact name")
    path = workspace / filename
    if path.parent.resolve() != workspace.resolve() or path.exists() or path.is_symlink():
        raise FileExistsError("Destination is unavailable")
    return path


def write_new(workspace, filename, data):
    target = new_destination(workspace, filename)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target


def bytes_match(path, expected):
    try:
        return read_reviewed_file(path, 128_000) == expected
    except (OSError, ValueError):
        return False


def digest(data):
    return hashlib.sha256(data).hexdigest()
