"""Durable bounded retry reservations, never a direct executor or approval bypass."""

import json
from dataclasses import dataclass

from victus.agent.budgets import Budgets, seconds_left
from victus.tools.registry import RetryClass


@dataclass(frozen=True)
class RetryReservation:
    action_id: str
    retry_number: int
    remaining: dict


class RetryManager:
    def __init__(self, ledger, *, max_retries=1):
        if type(max_retries) is not int or not 0 <= max_retries <= 2:
            raise ValueError("At most two recovery retries")
        self.ledger, self.max_retries = ledger, max_retries

    def reserve(self, action_id, tool, remaining, *, automatic=True, cancelled):
        """Reserve one attempt from shared counters before fresh policy/approval.

        The returned remaining budget already charges the action attempt. A caller
        must persist it and must not charge the same reservation a second time.
        Model planning/repairs still use the ordinary shared request budget.
        """
        left = Budgets.model_validate(remaining).model_dump()
        record = self.ledger.get(action_id)
        if (
            record is None
            or record.tool_name != tool.name
            or record.tool_version != tool.version
            or record.status not in {"failed", "unknown"}
            or tool.retry_class not in {RetryClass.SAFE, RetryClass.IDEMPOTENT}
            or (tool.external_write and automatic)
            or cancelled()
        ):
            raise PermissionError("Retry is not classified safe or requires explicit review")
        with self.ledger._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if cancelled():
                raise PermissionError("Retry cancelled")
            prior = db.execute(
                "SELECT retry_number,budget_json FROM recovery_retries WHERE action_id=? "
                "ORDER BY retry_number DESC LIMIT 1",
                (action_id,),
            ).fetchone()
            number = prior[0] + 1 if prior else 1
            if prior:
                saved = json.loads(prior[1])
                for key in (
                    "actions",
                    "model_requests",
                    "output_tokens",
                    "recoveries",
                    "active_seconds",
                    "nodes",
                    "observations",
                ):
                    left[key] = min(left[key], saved[key])
                left["repairs_used"] = max(left["repairs_used"], saved["repairs_used"])
            if (
                number > self.max_retries
                or left["actions"] <= 0
                or left["recoveries"] <= 0
                or seconds_left(left) <= 0
            ):
                raise PermissionError("Retry budget exhausted")
            # A missing or uncertain external effect never justifies a replay.
            if tool.external_write:
                proof = db.execute(
                    "SELECT verdict FROM recovery_reconciliations WHERE action_id=? "
                    "AND tool_version=? AND canonical_args_hash=? "
                    "AND created_at>strftime('%Y-%m-%dT%H:%M:%fZ','now','-60 seconds') "
                    "ORDER BY rowid DESC LIMIT 1",
                    (action_id, tool.version, record.canonical_args_hash),
                ).fetchone()
                if proof is None or proof[0] != "absent":
                    raise PermissionError("Reconcile the effect before requesting a new write")
            left["actions"] -= 1
            left["recoveries"] -= 1
            db.execute(
                "INSERT INTO recovery_retries VALUES (?,?,?)", (action_id, number, json.dumps(left))
            )
            self.ledger._emit_event(
                db, action_id, "recovery.retry_reserved", {"retry_number": number}
            )
        return RetryReservation(action_id, number, left)
