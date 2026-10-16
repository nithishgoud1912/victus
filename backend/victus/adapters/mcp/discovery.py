"""Remote descriptions, annotations and scopes do not grant local capabilities."""

from victus.adapters.mcp.client import MCPError
from victus.tools.contracts import NoteArguments


def discover(client):
    result = client.call("tools/list", {})
    tools = result.get("tools")
    if (set(result) != {"tools"} or not isinstance(tools, list) or len(tools) != 1
            or not isinstance(tools[0], dict)
            or set(tools[0]) - {"name", "description", "inputSchema"}
            or tools[0].get("name") != "create_note"
            or tools[0].get("inputSchema") != NoteArguments.model_json_schema()):
        raise MCPError("MCP_UNCONSTRAINED_CAPABILITY")
    return ["fs.create_note"]
