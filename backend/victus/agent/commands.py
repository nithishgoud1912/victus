"""Narrow intent intake. Text supplies data, never executable/tool authority."""

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import Field

from victus.tools.contracts import NoteArguments, ToolRequest
from victus.workflows.common import Arguments
from victus.workflows.contracts import (
    BROWSER_RESEARCH_TOOL,
    NOTEPAD_CHECKLIST_TOOL,
    BrowserResearchSubmission,
    NotepadChecklistSubmission,
)

COMMAND_TOOL = "internal.command"


class CommandFields(Arguments):
    intent: Literal["note", "checklist", "research"] | None = None
    filename: str | None = Field(default=None, max_length=70)
    content: str | None = Field(default=None, max_length=8192)
    items: list[str] | None = Field(default=None, max_length=50)
    source_ids: list[str] | None = Field(default=None, max_length=10)
    required_sources: int | None = Field(default=None, ge=1, le=10)


class CommandSubmission(Arguments):
    text: str = Field(min_length=1, max_length=4096)
    fields: CommandFields = Field(default_factory=CommandFields)
    reasoning: bool = False


class CommandReference(Arguments):
    command_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class CommandResponse(Arguments):
    command_id: str
    state: Literal["clarification", "submitted", "unavailable", "expired", "stopped"]
    task_id: str | None = None
    missing: list[str] = Field(default_factory=list)
    message: str


def interpret(submission):
    fields = submission.fields.model_dump(exclude_none=True)
    text = submission.text.strip()
    # Existing explicit note grammar, plus bounded workflow templates. Full matches only.
    match = re.fullmatch(
        r'(?:create|write) (?:a )?(?:note|file) ([A-Za-z0-9_-]+\.txt) (?:containing|with text) ("(?:[^"\\]|\\.)*")\.?',
        text,
        re.I,
    )
    if match:
        fields = {"intent": "note", "filename": match[1], "content": json.loads(match[2]), **fields}
    match = re.fullmatch(
        r"create (?:a )?(?:notepad )?checklist ([A-Za-z0-9_-]+\.txt) with items (\[.*\])",
        text,
        re.I,
    )
    if match:
        fields = {
            "intent": "checklist",
            "filename": match[1],
            "items": json.loads(match[2]),
            **fields,
        }
    match = re.fullmatch(
        r"research sources ([A-Za-z0-9_, -]+) (?:into|as) ([A-Za-z0-9_-]+\.json)", text, re.I
    )
    if match:
        ids = [value.strip() for value in match[1].split(",")]
        fields = {
            "intent": "research",
            "filename": match[2],
            "source_ids": ids,
            "required_sources": len(set(ids)),
            **fields,
        }
    if "intent" not in fields:
        candidates = []
        for kind, pattern in [
            ("note", r"\b(note|file)\b"),
            ("checklist", r"\b(notepad|checklist)\b"),
            ("research", r"\b(research|sources|browser|web)\b"),
        ]:
            if re.search(pattern, text, re.I):
                candidates.append(kind)
        if len(candidates) == 1:
            fields["intent"] = candidates[0]
    fields = CommandFields.model_validate(fields, strict=True)
    required = {
        "note": ["filename", "content"],
        "checklist": ["filename", "items"],
        "research": ["filename", "source_ids", "required_sources"],
    }
    missing = (
        ["intent"]
        if fields.intent is None
        else [name for name in required[fields.intent] if getattr(fields, name) is None]
    )
    return fields, missing


def action_for(fields, tasks):
    if fields.intent == "note":
        args = NoteArguments(filename=fields.filename, text=fields.content)
        return ToolRequest(tool="fs.create_note", arguments=args.model_dump())
    if fields.intent == "checklist":
        profiles = sorted(tasks.qualified_notepad_profiles & tasks.reviewed_notepad_profiles)
        if not profiles or NOTEPAD_CHECKLIST_TOOL not in tasks.registry.names():
            raise PermissionError("Native checklist qualification is required")
        args = NotepadChecklistSubmission(
            profile=profiles[0], filename=fields.filename, items=fields.items
        )
        return ToolRequest(tool=NOTEPAD_CHECKLIST_TOOL, arguments=args.model_dump())
    if fields.intent == "research":
        if tasks.research is None or BROWSER_RESEARCH_TOOL not in tasks.registry.names():
            raise PermissionError("Qualified fixture research is unavailable")
        if not Path(tasks.research.browser_executable).is_file():
            raise PermissionError("Qualified fixture browser is not installed")
        args = BrowserResearchSubmission(
            filename=fields.filename,
            source_ids=fields.source_ids,
            required_sources=fields.required_sources,
        )
        return ToolRequest(tool=BROWSER_RESEARCH_TOOL, arguments=args.model_dump())
    raise ValueError("A supported intent is required")
