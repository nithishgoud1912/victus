"""Durable action ledger backed by SQLite.

Each method maps to a single state transition in the action_attempts table
and emits a corresponding event row for the audit log.  All writes go through
``_transition()`` which enforces valid status progressions.

The ledger never stores raw argument payloads; those belong in
``storage/payloads.py`` with restricted retention.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _canonical_hash(arguments: dict[str, Any]) -> str:
    """Deterministic SHA-256 of the argument dict for deduplication."""
    canonical = json.dumps(arguments, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ── valid status transitions ─────────────────────────────────────────────
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "prepared":     {"dispatching", "cancelled", "failed"},
    "dispatching":  {"applied", "unknown", "failed", "cancelled"},
    "applied":      {"verified", "unknown", "failed"},
    "verified":     set(),      # terminal
    "unknown":      set(),      # terminal — operator must intervene
    "failed":       set(),      # terminal
    "cancelled":    set(),      # terminal
}


@dataclass(frozen=True)
class ActionRecord:
    """Read-only snapshot of an action_attempt row."""

    action_id: str
    tool_name: str
    tool_version: str
    canonical_args_hash: str
    expected_effect_ref: str | None
    status: str
    error_code: str | None
    output_name: str | None
    sha256: str | None
    created_at: str
    dispatched_at: str | None
    applied_at: str | None
    verified_at: str | None
    finished_at: str | None


class ActionLedger:
    """Durable, append-oriented ledger for action lifecycle tracking.

    All public methods are synchronous and safe to call from thread-pool
    workers in FastAPI.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _emit_event(
        self,
        conn: sqlite3.Connection,
        action_id: str,
        event_type: str,
        event_data: dict[str, Any] | None = None,
    ) -> None:
        conn.execute(
            "INSERT INTO events (action_id, event_type, event_data) VALUES (?, ?, ?)",
            (action_id, event_type, json.dumps(event_data or {})),
        )

    def _transition(
        self,
        conn: sqlite3.Connection,
        action_id: str,
        to_status: str,
        *,
        extra_columns: dict[str, Any] | None = None,
        event_data: dict[str, Any] | None = None,
    ) -> None:
        """Move *action_id* to *to_status*, enforcing the state machine."""
        row = conn.execute(
            "SELECT status FROM action_attempts WHERE action_id = ?", (action_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Action {action_id} does not exist")
        current = row["status"]
        if to_status not in _VALID_TRANSITIONS.get(current, set()):
            raise ValueError(
                f"Invalid transition {current!r} → {to_status!r} for action {action_id}"
            )
        now = _now_iso()
        sets = ["status = ?"]
        params: list[Any] = [to_status]
        # Set the appropriate timestamp column.
        ts_column = {
            "dispatching": "dispatched_at",
            "applied":     "applied_at",
            "verified":    "verified_at",
        }.get(to_status)
        if ts_column:
            sets.append(f"{ts_column} = ?")
            params.append(now)
        # Terminal states stamp finished_at.
        if to_status in {"verified", "unknown", "failed", "cancelled"}:
            sets.append("finished_at = ?")
            params.append(now)
        if extra_columns:
            for col, val in extra_columns.items():
                sets.append(f"{col} = ?")
                params.append(val)
        params.append(action_id)
        conn.execute(
            f"UPDATE action_attempts SET {', '.join(sets)} WHERE action_id = ?",
            params,
        )
        self._emit_event(conn, action_id, f"status:{to_status}", event_data)

    # ── public API ────────────────────────────────────────────────────────

    def prepare_action(
        self,
        tool_name: str,
        tool_version: str,
        arguments: dict[str, Any],
        *,
        expected_effect_ref: str | None = None,
    ) -> str:
        """Create a new action_attempt in ``prepared`` status.  Returns the action_id."""
        action_id = uuid4().hex
        args_hash = _canonical_hash(arguments)
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO action_attempts
                   (action_id, tool_name, tool_version, canonical_args_hash,
                    expected_effect_ref, status)
                   VALUES (?, ?, ?, ?, ?, 'prepared')""",
                (action_id, tool_name, tool_version, args_hash, expected_effect_ref),
            )
            self._emit_event(conn, action_id, "status:prepared", {
                "tool_name": tool_name,
                "tool_version": tool_version,
                "canonical_args_hash": args_hash,
            })
        return action_id

    def mark_dispatching(self, action_id: str) -> None:
        """Transition to ``dispatching`` — the adapter is about to be invoked."""
        with self._connect() as conn:
            self._transition(conn, action_id, "dispatching")

    def mark_applied(
        self,
        action_id: str,
        *,
        output_name: str | None = None,
    ) -> None:
        """Transition to ``applied`` — the adapter completed without exception."""
        with self._connect() as conn:
            self._transition(
                conn, action_id, "applied",
                extra_columns={"output_name": output_name} if output_name else None,
                event_data={"output_name": output_name},
            )

    def mark_verified(
        self,
        action_id: str,
        *,
        sha256: str | None = None,
    ) -> None:
        """Transition to ``verified`` — the verifier confirmed the postcondition."""
        with self._connect() as conn:
            self._transition(
                conn, action_id, "verified",
                extra_columns={"sha256": sha256} if sha256 else None,
                event_data={"sha256": sha256},
            )

    def mark_unknown(
        self,
        action_id: str,
        *,
        error_code: str | None = None,
    ) -> None:
        """Transition to ``unknown`` — the outcome could not be determined."""
        with self._connect() as conn:
            self._transition(
                conn, action_id, "unknown",
                extra_columns={"error_code": error_code} if error_code else None,
                event_data={"error_code": error_code},
            )

    def mark_failed(
        self,
        action_id: str,
        *,
        error_code: str | None = None,
    ) -> None:
        """Transition to ``failed`` — the action was rejected or errored before dispatch."""
        with self._connect() as conn:
            self._transition(
                conn, action_id, "failed",
                extra_columns={"error_code": error_code} if error_code else None,
                event_data={"error_code": error_code},
            )

    def mark_cancelled(self, action_id: str) -> None:
        """Transition to ``cancelled`` — the service was stopped before dispatch."""
        with self._connect() as conn:
            self._transition(conn, action_id, "cancelled")

    def get(self, action_id: str) -> ActionRecord | None:
        """Return a single action record, or ``None`` if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM action_attempts WHERE action_id = ?", (action_id,)
            ).fetchone()
        return _row_to_record(row) if row else None

    def list_unfinished(self) -> list[ActionRecord]:
        """Return all actions that have not reached a terminal status."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM action_attempts WHERE status IN ('prepared', 'dispatching', 'applied')"
                " ORDER BY created_at"
            ).fetchall()
        return [_row_to_record(r) for r in rows]


def _row_to_record(row: sqlite3.Row) -> ActionRecord:
    return ActionRecord(
        action_id=row["action_id"],
        tool_name=row["tool_name"],
        tool_version=row["tool_version"],
        canonical_args_hash=row["canonical_args_hash"],
        expected_effect_ref=row["expected_effect_ref"],
        status=row["status"],
        error_code=row["error_code"],
        output_name=row["output_name"],
        sha256=row["sha256"],
        created_at=row["created_at"],
        dispatched_at=row["dispatched_at"],
        applied_at=row["applied_at"],
        verified_at=row["verified_at"],
        finished_at=row["finished_at"],
    )
