"""Read-only, version-qualified effect probes with separately persisted evidence."""

from __future__ import annotations

import asyncio
import inspect
import json
import math
from dataclasses import dataclass, field
from typing import Callable, Literal
from uuid import uuid4

from langgraph.errors import GraphInterrupt

from victus.storage.action_ledger import ActionLedger, _canonical_hash
from victus.storage.payloads import PayloadStore, _now_iso


@dataclass(frozen=True)
class EffectProof:
    verdict: Literal["present", "absent", "unknown"]
    evidence: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Reconciliation:
    reconciliation_id: str
    action_id: str
    verdict: str
    evidence_ref: str | None


class Reconciler:
    def __init__(self, ledger: ActionLedger, payloads: PayloadStore, *, timeout_seconds=5):
        if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 30:
            raise ValueError("Invalid reconciliation deadline")
        self.ledger, self.payloads = ledger, payloads
        self.timeout_seconds = timeout_seconds
        self._verifiers: dict[tuple[str, str], Callable] = {}

    def register(self, tool_name: str, tool_version: str, verifier: Callable):
        """Trusted async, read-only verifier. Blocked native probes need a supervisor."""
        if not inspect.iscoroutinefunction(verifier):
            raise TypeError("Recovery probes must be asynchronous read-only verifiers")
        key = tool_name, tool_version
        if key in self._verifiers:
            raise ValueError("Duplicate reconciliation verifier")
        self._verifiers[key] = verifier

    def _arguments(self, record):
        rows = self.payloads.get_by_action(record.action_id, "arguments")
        rows = [row for row in rows if row.expires_at is not None and row.expires_at > _now_iso()]
        if not rows:
            raise ValueError("Retained arguments unavailable")
        arguments = json.loads(rows[-1].data_json)
        if (
            not isinstance(arguments, dict)
            or _canonical_hash(arguments) != record.canonical_args_hash
        ):
            raise ValueError("Arguments do not match the action")
        return arguments

    async def reconcile(self, action_id: str, *, quiesced: bool) -> Reconciliation:
        if quiesced is not True:
            raise PermissionError("Stop and join the owned worker before reconciliation")
        record = self.ledger.get(action_id)
        if record is None:
            raise KeyError("Unknown action")
        if record.status not in {"prepared", "dispatching", "applied", "unknown"}:
            raise ValueError("Action does not need reconciliation")
        # Preserve uncertain dispatch history even if a receipt is later found.
        if record.status in {"dispatching", "applied"}:
            self.ledger.mark_unknown(action_id, error_code="RECOVERY_REQUIRES_REVIEW")
            record = self.ledger.get(action_id)
        elif record.status == "prepared":
            self.ledger.mark_cancelled(action_id)
        proof = EffectProof("unknown")
        verifier = self._verifiers.get((record.tool_name, record.tool_version))
        if verifier is not None:
            try:
                arguments = self._arguments(record)
                async with asyncio.timeout(self.timeout_seconds):
                    candidate = await verifier(record, arguments)
                if type(candidate) is not EffectProof or candidate.verdict not in {
                    "present",
                    "absent",
                    "unknown",
                }:
                    raise ValueError("Invalid effect proof")
                if not isinstance(candidate.evidence, dict):
                    raise ValueError("Invalid evidence")
                encoded = json.dumps(candidate.evidence, allow_nan=False)
                if len(encoded.encode("utf-8")) > 128000:
                    raise ValueError("Evidence exceeds retention limit")
                if candidate.verdict != "unknown" and not candidate.evidence:
                    raise ValueError("A conclusive probe requires independent evidence")
                proof = candidate
            except asyncio.CancelledError:
                raise
            except GraphInterrupt:
                raise
            except Exception:
                # No exception messages, argument bodies or credentials in audit rows.
                proof = EffectProof("unknown")
        evidence_ref = None
        if proof.evidence:
            evidence_ref = self.payloads.store(
                action_id, "output", proof.evidence, retention_hours=24
            )
        result = Reconciliation(uuid4().hex, action_id, proof.verdict, evidence_ref)
        with self.ledger._connect() as db:
            db.execute(
                "INSERT INTO recovery_reconciliations "
                "(reconciliation_id,action_id,tool_version,canonical_args_hash,verdict,evidence_ref) "
                "VALUES (?,?,?,?,?,?)",
                (
                    result.reconciliation_id,
                    action_id,
                    record.tool_version,
                    record.canonical_args_hash,
                    result.verdict,
                    evidence_ref,
                ),
            )
            self.ledger._emit_event(
                db,
                action_id,
                "recovery.reconciled",
                {
                    "verdict": result.verdict,
                    "evidence_ref": evidence_ref,
                },
            )
        return result

    async def unfinished(self, *, quiesced: bool):
        with self.ledger._connect() as db:
            ids = [
                row[0]
                for row in db.execute(
                    "SELECT action_id FROM action_attempts WHERE status IN "
                    "('prepared','dispatching','applied','unknown') ORDER BY rowid"
                )
            ]
        return [await self.reconcile(action_id, quiesced=quiesced) for action_id in ids]

    def latest(self, action_id: str) -> Reconciliation | None:
        record = self.ledger.get(action_id)
        if record is None:
            return None
        with self.ledger._connect() as db:
            row = db.execute(
                "SELECT reconciliation_id,action_id,verdict,evidence_ref FROM recovery_reconciliations "
                "WHERE action_id=? AND tool_version=? AND canonical_args_hash=? ORDER BY rowid DESC LIMIT 1",
                (action_id, record.tool_version, record.canonical_args_hash),
            ).fetchone()
        return Reconciliation(*row) if row else None
