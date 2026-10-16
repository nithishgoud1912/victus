"""Parse the entire JSON answer. No substring, code fence or executable extraction."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from victus.models._json import strict_json
from victus.models.contracts import ErrorCode, ModelError, StrictModel
from victus.tools.contracts import ActionProposal


class StrictActionProposal(ActionProposal):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    tool: str = Field(min_length=1, max_length=100)
    target_ref: str | None = Field(default=None, min_length=1, max_length=128)
    observation_id: str | None = Field(default=None, min_length=1, max_length=128)


class ActionDecision(StrictModel):
    decision: Literal["action"]
    action: StrictActionProposal


class FinishDecision(StrictModel):
    decision: Literal["finish"]
    status: Literal["completed", "blocked"]
    reason: str = Field(min_length=1, max_length=2000)


class OutputParser:
    """An explicit tool catalog narrows schema and validates tool-specific arguments.

    This catalog is not policy approval. Finish is a model decision, not evidence
    of task completion. The dispatcher/verifier remain the execution boundary.
    """

    def __init__(self, tools: dict[str, type[BaseModel]]):
        if len(tools) > 32:
            raise ValueError("A bounded explicit tool catalog is required")
        self.tools = dict(tools)

    def schema(self):
        variants = []
        for name, arguments in self.tools.items():
            # Keep definitions local to this branch so different tools may reuse type names.
            argument_schema = arguments.model_json_schema()
            definitions = argument_schema.pop("$defs", {})

            def inline(node, depth=0):
                if depth > 32:
                    raise ValueError("Recursive tool schema is unsupported")
                if isinstance(node, list):
                    return [inline(value, depth + 1) for value in node]
                if not isinstance(node, dict):
                    return node
                if "$ref" in node:
                    return inline(definitions[node["$ref"].removeprefix("#/$defs/")], depth + 1)
                return {key: inline(value, depth + 1) for key, value in node.items()}

            variants.append(
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "tool": {"const": name, "type": "string"},
                        "arguments": inline(argument_schema),
                        "target_ref": {
                            "type": ["string", "null"],
                            "minLength": 1,
                            "maxLength": 128,
                        },
                        "observation_id": {
                            "type": ["string", "null"],
                            "minLength": 1,
                            "maxLength": 128,
                        },
                    },
                    "required": ["tool", "arguments"],
                }
            )
        if not variants:
            return FinishDecision.model_json_schema()
        return {
            "oneOf": [
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "decision": {"const": "action", "type": "string"},
                        "action": {"oneOf": variants},
                    },
                    "required": ["decision", "action"],
                },
                FinishDecision.model_json_schema(),
            ]
        }

    def parse(self, text: str) -> ActionDecision | FinishDecision:
        try:
            if not isinstance(text, str) or len(text.encode("utf-8")) > 65536:
                raise ValueError("Output bound")
            value = strict_json(text)
            if not isinstance(value, dict):
                raise ValueError("Decision must be an object")
            if value.get("decision") == "finish":
                return FinishDecision.model_validate(value)
            decision = ActionDecision.model_validate(value)
            proposal = decision.action
            if (proposal.target_ref is None) != (proposal.observation_id is None):
                raise ValueError("Target and observation must be paired")
            arguments = self.tools[proposal.tool].model_validate(proposal.arguments, strict=True)
            # Explicit extra rejection even if a registered model defaults to ignoring extras.
            if set(proposal.arguments) - set(type(arguments).model_fields):
                raise ValueError("Unknown tool arguments")
            return decision
        except (ValueError, TypeError, KeyError, RecursionError, ValidationError):
            raise ModelError(ErrorCode.OUTPUT) from None
