"""Filesystem tool specifications.

Each public function returns a fully populated ``ToolSpec`` ready for
registration.  Adapter and verifier callables are imported lazily so that
this module stays a lightweight metadata declaration.
"""

from __future__ import annotations

from victus.adapters.filesystem.operations import create_note
from victus.tools.contracts import NoteArguments
from victus.tools.registry import RetryClass, RiskLevel, ToolSpec
from victus.tools.verifiers.filesystem import verify_note


def fs_create_note() -> ToolSpec:
    """Create a plain-text note inside the workspace."""
    return ToolSpec(
        name="fs.create_note",
        version="1.0.0",
        description="Create a plain-text .txt file inside the workspace directory.",
        argument_model=NoteArguments,
        risk_floor=RiskLevel.LOW,
        required_scope="fs:write",
        timeout_seconds=5.0,
        resource_name="workspace_fs",
        retry_class=RetryClass.NONE,
        execute=create_note,
        verify=verify_note,
    )


FILESYSTEM_TOOLS: list[ToolSpec] = [
    fs_create_note(),
]
