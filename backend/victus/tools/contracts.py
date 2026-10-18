from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ActionStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class NoteArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    filename: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.txt$")
    text: str = Field(min_length=1, max_length=8192)


class ToolRequest(BaseModel):
    """Untrusted transport data; identity, approval and verifier are never inputs."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)
    tool: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$")
    arguments: dict[str, Any]


class ActionProposal(ToolRequest):
    target_ref: str | None = Field(default=None, min_length=1, max_length=128)
    observation_id: str | None = Field(default=None, min_length=1, max_length=128)


class ActionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action_id: str
    status: ActionStatus
    side_effect: str
    evidence_refs: list[str]
    error_code: str | None = None


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    tool: Literal["fs.create_note"]
    arguments: NoteArguments


class TaskResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    task_id: str
    tool: str
    action_id: str | None = None
    status: Literal["queued", "prepared", "running", "waiting_for_review", "succeeded", "failed", "cancelled", "unknown"]
    approval_id: str | None = None
    verified: bool = False
    error_code: str | None = None
    output_name: str | None = None
    sha256: str | None = None


class TaskQueuedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    task_id: str
    status: Literal["queued", "cancelled"] = "queued"
