"""Conservative routing from explicit user intent to enabled, typed workflows."""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ConfigDict, Field

from victus.tools.contracts import ActionProposal


class RoutePlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str = Field(max_length=80)
    mode: str = Field(pattern=r"^(deterministic|agent|blocked)$")
    tool_names: list[str] = Field(default_factory=list, max_length=8)
    steps: list[ActionProposal] = Field(default_factory=list, max_length=12)
    reason: str | None = Field(default=None, max_length=120)


def request_text(goal) -> str:
    if isinstance(goal, str):
        return goal
    if isinstance(goal, dict):
        for key in ("request", "command"):
            if isinstance(goal.get(key), str):
                return goal[key]
    return ""


class CommandRouter:
    """Catalog and workflow bindings are supplied by trusted application code.

    No desktop/browser workflow is enabled merely because a stub exists. Bind
    reviewed workflow wrapper tools explicitly; all steps still use Dispatcher.
    """

    def __init__(self, tools: dict, *, workflow_bindings: dict[str, str] | None = None):
        self.tools = dict(tools)
        self.bindings = dict(workflow_bindings or {})
        if any(name not in self.tools for name in self.bindings.values()):
            raise ValueError("Workflow binding is absent from enabled catalog")

    def _steps(self, name, actions):
        steps = []
        try:
            for tool, arguments in actions:
                arguments = self.tools[tool].model_validate(arguments, strict=True).model_dump()
                steps.append(ActionProposal(tool=tool, arguments=arguments))
            if not steps or len(steps) > 12:
                raise ValueError("Workflow length")
        except (KeyError, ValueError, TypeError):
            return RoutePlan(name=name, mode="blocked", reason="WORKFLOW_UNAVAILABLE_OR_INVALID")
        return RoutePlan(
            name=name,
            mode="deterministic",
            steps=steps,
            tool_names=list(dict.fromkeys(step.tool for step in steps)),
        )

    def __call__(self, goal):
        if isinstance(goal, dict) and "workflow" in goal:
            name = goal["workflow"]
            args = goal.get("arguments", {})
            if not isinstance(name, str) or not isinstance(args, dict):
                return RoutePlan(name="invalid", mode="blocked", reason="INVALID_WORKFLOW")
            if name == "create_note":
                return self._steps(name, [("fs.create_note", args)])
            if name == "create_notes":
                notes = args.get("notes", []) if isinstance(args, dict) else []
                if not isinstance(notes, list) or len(notes) > 12:
                    return RoutePlan(name="create_notes", mode="blocked", reason="INVALID_NOTES")
                return self._steps(name, [("fs.create_note", note) for note in notes])
            if name in self.bindings:
                return self._steps(name, [(self.bindings[name], args)])
            return RoutePlan(name="unsupported", mode="blocked", reason="WORKFLOW_NOT_ENABLED")
        text = request_text(goal).strip()
        # Full match and a JSON string payload: no guessing destinations or splitting
        # arbitrary natural-language conjunctions into executable commands.
        match = re.fullmatch(
            r"(?:create|write) (?:a )?(?:note|file) ([A-Za-z0-9_-]+\.txt) "
            r'(?:containing|with text) ("(?:[^"\\]|\\.)*")\.?',
            text,
            re.IGNORECASE,
        )
        if match:
            return self._steps(
                "create_note",
                [
                    (
                        "fs.create_note",
                        {
                            "filename": match[1],
                            "text": json.loads(match[2]),
                        },
                    )
                ],
            )
        domains = set()
        if re.search(r"\b(file|files|note|notes|folder|folders)\b", text, re.I):
            domains.add("fs")
        if re.search(r"\b(browser|web|website|page|pages|field|research)\b", text, re.I):
            domains.update({"browser", "research"})
        if re.search(r"\b(notepad|desktop|app|apps|application|explorer)\b", text, re.I):
            domains.update({"desktop", "uia"})
        names = [name for name in sorted(self.tools) if name.split(".")[0] in domains]
        if len(names) > 8:
            return RoutePlan(name="clarify", mode="blocked", reason="NARROW_TASK_REQUIRED")
        return RoutePlan(name="agent", mode="agent", tool_names=names)
