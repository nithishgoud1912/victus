from pathlib import Path

from victus.tools.contracts import ActionRequest


def validate_step(tool, arguments, context) -> None:
    """A model cannot grant scopes, waive tool risk floors, or choose verifiers."""
    if tool.required_scope not in context.scopes or context.authorize(tool, arguments) is not True:
        raise PermissionError("Workflow step is not approved")


_RESERVED = {"CON", "PRN", "AUX", "NUL", "CLOCK$"}
_RESERVED |= {f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)}


def validate_action(action: ActionRequest, workspace: Path) -> None:
    if action.tool != "fs.create_note":
        raise PermissionError("Tool is not allowed")
    name = action.arguments.filename
    if Path(name).stem.upper() in _RESERVED:
        raise PermissionError("Reserved Windows filename")
    if len(action.arguments.text.encode("utf-8")) > 8192:
        raise PermissionError("Payload exceeds the byte limit")
    target = workspace / name
    if target.resolve().parent != workspace.resolve():
        raise PermissionError("Target escapes the workspace")
    if target.exists() or target.is_symlink():
        raise FileExistsError("Target already exists")
