"""Memory entry contracts; provenance records human review, never an imported role claim."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MemoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    type: Literal["preference", "summary"]
    value: str = Field(min_length=1, max_length=8192)
    provenance: Literal["explicit_user_preference", "user_reviewed_summary"]
    confirmation: Literal["explicit_user_review"]
    task_ids: list[str] = Field(default_factory=list, max_length=16)
    expires_at: float | None = Field(default=None, allow_inf_nan=False)

    @model_validator(mode="after")
    def reviewed_kind(self):
        expected = (
            "explicit_user_preference" if self.type == "preference" else "user_reviewed_summary"
        )
        if self.provenance != expected or not self.value.strip():
            raise ValueError("Memory requires explicit review of the matching type")
        if any(not value or len(value) > 128 for value in self.task_ids):
            raise ValueError("Invalid task reference")
        return self


class MemoryEntry(BaseModel):
    memory_id: str
    type: Literal["preference", "summary"]
    value: str
    provenance: str
    created_at: float
    updated_at: float
    last_confirmed_at: float
    expires_at: float | None = None
    context_only: bool = True
