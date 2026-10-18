"""Narrow workflow transport; authority and native selectors stay server-side."""

from pydantic import Field, model_validator

from victus.workflows.common import Arguments
from victus.workflows.create_notepad_checklist import ChecklistRequest

NOTEPAD_CHECKLIST_TOOL = "workflow.notepad_checklist"


class NotepadChecklistSubmission(Arguments):
    profile: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
    items: list[str] = Field(min_length=1, max_length=50)
    filename: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.txt$")

    @model_validator(mode="after")
    def bounded_checklist(self):
        ChecklistRequest(**self.model_dump()).editor_text()
        return self


class WorkflowUnavailable(ValueError):
    """A native workflow cannot be admitted before qualification and review wiring."""


BROWSER_RESEARCH_TOOL = "workflow.browser_research"


class BrowserResearchSubmission(Arguments):
    source_ids: list[str] = Field(min_length=1, max_length=10)
    required_sources: int = Field(ge=1, le=10)
    filename: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.json$")

    @model_validator(mode="after")
    def known_fixture_sources(self):
        if any(source not in {"source-a", "source-b", "redirect-a"} for source in self.source_ids):
            raise ValueError("Only server-reviewed fixture source IDs are supported")
        return self
