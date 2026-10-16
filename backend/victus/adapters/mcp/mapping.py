"""Native and MCP notes share the registry contract, policy and local verifier."""

import hashlib
import json
from dataclasses import replace

from victus.adapters.mcp.client import LocalMCPClient, MCPError
from victus.adapters.mcp.discovery import discover
from victus.safety.policy import validate_action
from victus.tools.contracts import ActionRequest
from victus.tools.filesystem import fs_create_note
from victus.tools.verifiers.filesystem import verify_note


def validate_result(result, arguments):
    try:
        if set(result) != {"content", "isError"} or result["isError"] is not False:
            raise ValueError()
        content = result["content"]
        if len(content) != 1 or set(content[0]) != {"type", "text"}:
            raise ValueError()
        if content[0]["type"] != "text" or len(content[0]["text"]) > 1024:
            raise ValueError()
        value = json.loads(content[0]["text"])
        if value != {"filename": arguments.filename,
                     "sha256": hashlib.sha256(arguments.text.encode()).hexdigest()}:
            raise ValueError()
    except Exception:
        raise MCPError("MCP_INVALID_TOOL_OUTPUT") from None


def execute_note(workspace, arguments, cancelled=None):
    validate_action(ActionRequest(tool="fs.create_note", arguments=arguments), workspace)
    with LocalMCPClient(workspace, cancelled=cancelled) as client:
        discover(client)
        result = client.call("tools/call", {"name": "create_note",
                                           "arguments": arguments.model_dump()})
        validate_result(result, arguments)
    target = workspace / arguments.filename  # Never accept a remote path.
    if target.is_symlink() or target.resolve().parent != workspace.resolve():
        raise MCPError("MCP_SCOPE_VIOLATION")
    if not verify_note(target, arguments):
        raise MCPError("MCP_VERIFICATION_FAILED")
    return target


def mcp_create_note():
    return replace(fs_create_note(), execute=execute_note, execute_cancellable=execute_note,
                   timeout_seconds=6.0)
