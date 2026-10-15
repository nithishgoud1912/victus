import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from victus.safety.policy import validate_action
from victus.tools.contracts import ActionRequest
from victus.tools.registry import ToolRegistry


@dataclass(frozen=True)
class DispatchOutcome:
    """The observable result of a single action attempt."""

    status: str
    verified: bool = False
    error_code: str | None = None
    output_name: str | None = None
    sha256: str | None = None


class Dispatcher:
    """Owns validation, policy, adapter call, and verification for one action attempt.

    The caller (TaskService) is responsible for task identity, persistence, and
    the stop/cancellation latch.  The Dispatcher is stateless across calls and
    never touches the database.
    """

    def __init__(self, workspace: Path, registry: ToolRegistry) -> None:
        self.workspace = workspace
        self.registry = registry

    def dispatch(self, action: ActionRequest, cancelled: Any = None) -> DispatchOutcome:
        """Execute *action* inside the workspace and return an outcome.

        All exceptions that represent known failure modes are caught and mapped
        to an appropriate ``DispatchOutcome``.  Unknown exceptions propagate so
        the caller can decide on a fallback status.
        """
        dispatched = False
        try:
            tool = self.registry.get(action.tool)
            validated = tool.argument_model.model_validate(action.arguments.model_dump())
            validate_action(action, self.workspace)
            if cancelled is not None and cancelled.is_set():
                return DispatchOutcome(status="cancelled", error_code="SERVICE_STOPPED")
            dispatched = True
            if tool.execute_cancellable is not None and cancelled is not None:
                output = tool.execute_cancellable(self.workspace, validated, cancelled)
            else:
                output = tool.execute(self.workspace, validated)
            if cancelled is not None and cancelled.is_set():
                return DispatchOutcome(status="unknown", error_code="STOPPED_DURING_ACTION")
            if tool.verify(output, validated):
                return DispatchOutcome(
                    status="succeeded",
                    verified=True,
                    output_name=output.name,
                    sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                )
            return DispatchOutcome(
                status="unknown",
                error_code="POSTCONDITION_FAILED",
                output_name=output.name,
            )
        except FileExistsError:
            return DispatchOutcome(status="failed", error_code="TARGET_EXISTS")
        except PermissionError:
            return DispatchOutcome(
                status="unknown" if dispatched else "failed",
                error_code="ACCESS_DENIED" if dispatched else "POLICY_DENIED",
            )
        except ValueError:
            return DispatchOutcome(
                status="unknown" if dispatched else "failed",
                error_code="INVALID_ACTION",
            )
        except OSError:
            return DispatchOutcome(
                status="unknown" if dispatched else "failed",
                error_code="IO_ERROR",
            )
