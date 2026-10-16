"""Bundled narrow stdio server; no shell, browser, network or arbitrary file tools."""

import hashlib
import json
import sys
from pathlib import Path

from victus.adapters.filesystem.operations import create_note
from victus.safety.policy import validate_action
from victus.tools.contracts import ActionRequest, NoteArguments

PROTOCOL = "2025-11-25"


def main():
    if len(sys.argv) != 3 or sys.argv[1] != "--workspace":
        raise SystemExit(2)
    workspace = Path(sys.argv[2]).resolve(strict=True)
    initialized = False
    while True:
        raw = sys.stdin.buffer.readline(32769)
        if not raw:
            return
        if len(raw) > 32768 or not raw.endswith(b"\n"):
            return
        try:
            req = json.loads(raw)
            method = req["method"]
            if method == "notifications/initialized":
                initialized = True
                continue
            if method == "initialize":
                result = {"protocolVersion": PROTOCOL,
                          "serverInfo": {"name": "victus-note", "version": "0.1.0"},
                          "capabilities": {"tools": {"listChanged": False}}}
            elif method == "tools/list" and initialized:
                result = {"tools": [{"name": "create_note",
                                     "description": "Create a workspace note",
                                     "inputSchema": NoteArguments.model_json_schema()}]}
            elif method == "tools/call" and initialized:
                params = req["params"]
                if set(params) != {"name", "arguments"} or params["name"] != "create_note":
                    raise ValueError()
                arguments = NoteArguments.model_validate(params["arguments"])
                validate_action(ActionRequest(tool="fs.create_note", arguments=arguments), workspace)
                target = create_note(workspace, arguments)
                result = {"content": [{"type": "text", "text": json.dumps({
                    "filename": target.name,
                    "sha256": hashlib.sha256(arguments.text.encode()).hexdigest(),
                })}], "isError": False}
            else:
                raise ValueError()
            response = {"jsonrpc": "2.0", "id": req["id"], "result": result}
        except Exception:
            response = {"jsonrpc": "2.0", "id": req.get("id") if isinstance(req, dict) else None,
                        "error": {"code": -32602, "message": "Request rejected"}}
        sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
