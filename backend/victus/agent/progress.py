"""Semantic loop fingerprints; fresh observation IDs alone are not progress."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field

_VOLATILE = {"observation_id", "snapshot_id", "timestamp", "observed_at", "captured_at"}


class Entry(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    recovery_used: bool = False


class ProgressState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    entries: list[Entry] = Field(default_factory=list, max_length=64)
    recovery_pending: bool = False


def fingerprint(proposal: dict, observation: dict) -> str:
    if proposal.get("decision") == "finish":
        proposal = {key: value for key, value in proposal.items() if key != "reason"}
    observed = {key: value for key, value in observation.items() if key not in _VOLATILE}
    targets = {}
    if isinstance(observed.get("targets"), (list, tuple)):
        clean = []
        for index, target in enumerate(observed["targets"]):
            value = {k: v for k, v in target.items() if k not in {"ref", "target_ref"}}
            identity = {"index": index, **value}
            for key in ("ref", "target_ref"):
                if key in target:
                    targets[target[key]] = identity
            clean.append(value)
        observed["targets"] = clean

    def action_value(value):
        if isinstance(value, dict):
            return {
                key: (
                    targets.get(item, item)
                    if key == "target_ref" and isinstance(item, str)
                    else action_value(item)
                )
                for key, item in value.items()
                if key != "observation_id"
            }
        if isinstance(value, (list, tuple)):
            return [action_value(item) for item in value]
        return value

    data = json.dumps(
        [action_value(proposal), observed], sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def assess(progress: dict, proposal: dict, observation: dict) -> tuple[dict, str]:
    updated = ProgressState.model_validate(progress).model_dump()
    signature = fingerprint(proposal, observation)
    entry = next((item for item in updated["entries"] if item["fingerprint"] == signature), None)
    if entry is None:
        updated["entries"] = [
            *updated["entries"],
            {"fingerprint": signature, "recovery_used": False},
        ][-64:]
        updated["recovery_pending"] = False
        return updated, "continue"
    if entry["recovery_used"]:
        return updated, "stop"
    entry["recovery_used"] = True
    updated["recovery_pending"] = True
    return updated, "recover"
