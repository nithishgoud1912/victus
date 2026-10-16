"""Ephemeral voice contracts. Raw audio/transcripts never enter the audit log."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from victus.tools.contracts import ActionRequest


class VoiceState(StrEnum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    REVIEWING = "reviewing"
    SUBMITTED = "submitted"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass(frozen=True)
class AudioFrame:
    sequence: int
    captured_at: float  # monotonic, not wall time
    sample_rate: int
    channels: int
    sample_format: Literal["pcm_s16le"]
    pcm: bytes


class Transcript(BaseModel):
    text: str = Field(max_length=8192)
    language: str = "en"
    # STT likelihoods are deliberately not represented as permission.


class VoiceSnapshot(BaseModel):
    enabled: bool
    state: VoiceState
    session_id: str | None = None
    revision: int = 0
    transcript: Transcript | None = None
    proposal: ActionRequest | None = None
    clarification: str | None = None
    error_code: str | None = None
    task_id: str | None = None
    summary: str | None = None
    speech_pending: bool = False
    muted: bool = False
    wake_suppressed: bool = False
    wake_available: bool = False
    wake_listening: bool = False
    wake_error: str | None = None


class SessionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: str
    revision: int = Field(ge=0)


class ReviewedSubmission(SessionCommand):
    confirmation: Literal["explicit_user_review"]
    action: ActionRequest


class MuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    muted: bool
