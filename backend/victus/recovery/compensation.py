"""Only explicitly registered reversals, executed through the normal dispatcher."""

import json
from dataclasses import dataclass
from typing import Callable

from victus.storage.action_ledger import _canonical_hash
from victus.storage.payloads import _now_iso
from victus.tools.contracts import ActionProposal


@dataclass(frozen=True)
class CompensationSpec:
    forward_tool: str
    forward_version: str
    reverse_tool: str
    reverse_version: str
    build_arguments: Callable


class CompensationManager:
    def __init__(self, reconciler, registry):
        self.reconciler, self.registry = reconciler, registry
        self._supported = {}

    def register(self, spec: CompensationSpec):
        reverse = self.registry.get(spec.reverse_tool)
        if reverse.version != spec.reverse_version:
            raise ValueError("Reverse tool version mismatch")
        key = spec.forward_tool, spec.forward_version
        if key in self._supported:
            raise ValueError("Duplicate compensation")
        self._supported[key] = spec

    def offer(self, action_id: str) -> ActionProposal:
        record = self.reconciler.ledger.get(action_id)
        proof = self.reconciler.latest(action_id)
        spec = self._supported.get((record.tool_name, record.tool_version)) if record else None
        if (
            spec is None
            or proof is None
            or proof.verdict != "present"
            or proof.evidence_ref is None
        ):
            raise PermissionError("No supported, independently verified reversal")
        payload = self.reconciler.payloads.get(proof.evidence_ref)
        if (
            payload is None
            or payload.action_id != action_id
            or payload.expires_at is None
            or payload.expires_at <= _now_iso()
        ):
            raise PermissionError("Reversal evidence unavailable")
        arguments = self.reconciler._arguments(record)
        if _canonical_hash(arguments) != record.canonical_args_hash:
            raise PermissionError("Action binding changed")
        reverse = self.registry.get(spec.reverse_tool)
        if reverse.version != spec.reverse_version:
            raise PermissionError("Reverse tool changed")
        value = spec.build_arguments(arguments, json.loads(payload.data_json))
        validated = reverse.argument_model.model_validate(value, strict=True)
        return ActionProposal(tool=reverse.name, arguments=validated.model_dump())

    async def dispatch(self, action_id, proposal, dispatcher, context):
        expected = self.offer(action_id)
        if proposal != expected or context.permits is None or context.prepared_action_id is None:
            raise PermissionError("Reversal needs its own normal policy and approval")
        return await dispatcher.dispatch_step(proposal, context)
