"""Payload store with restricted retention.

Raw argument bodies and typed text are stored here, **not** in the
action_attempts metadata table.  This separation lets retention policies
purge payload data (PII, large text blobs) independently of the audit log.

Retention rules:

- ``arguments`` payloads: retained until the action reaches a terminal
  status, then eligible for purge after ``retention_hours`` (default 72).
- ``typed_text`` payloads: shorter retention (default 24 h) because
  they may contain sensitive user input.
- ``output`` payloads: follow the same schedule as ``arguments``.

The ``purge_expired()`` method sets ``purged = 1`` and replaces
``data_json`` with a tombstone rather than deleting the row, so the
audit trail preserves the fact that a payload existed.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

PayloadKind = Literal["arguments", "typed_text", "output"]

# Default retention hours per kind.
_DEFAULT_RETENTION: dict[PayloadKind, int] = {
    "arguments": 72,
    "typed_text": 24,
    "output": 72,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _expiry_iso(kind: PayloadKind, retention_hours: int | None = None) -> str:
    hours = retention_hours if retention_hours is not None else _DEFAULT_RETENTION[kind]
    expiry = datetime.now(timezone.utc) + timedelta(hours=hours)
    return expiry.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass(frozen=True)
class PayloadRecord:
    """Read-only snapshot of a payloads row."""

    payload_id: str
    action_id: str
    kind: str
    data_json: str
    byte_length: int
    created_at: str
    expires_at: str | None
    purged: bool


class PayloadStore:
    """Restricted-retention store for raw argument and text payloads."""

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

    def store(
        self,
        action_id: str,
        kind: PayloadKind,
        data: dict[str, Any] | str,
        *,
        retention_hours: int | None = None,
    ) -> str:
        """Persist a payload and return its ``payload_id``."""
        payload_id = uuid4().hex
        data_json = json.dumps(data, ensure_ascii=False, default=str) if not isinstance(data, str) else data
        byte_length = len(data_json.encode("utf-8"))
        expires_at = _expiry_iso(kind, retention_hours)
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO payloads
                   (payload_id, action_id, kind, data_json, byte_length, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (payload_id, action_id, kind, data_json, byte_length, expires_at),
            )
        return payload_id

    def get(self, payload_id: str) -> PayloadRecord | None:
        """Return a single payload record, or ``None`` if not found or purged."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM payloads WHERE payload_id = ? AND purged = 0",
                (payload_id,),
            ).fetchone()
        return _row_to_record(row) if row else None

    def get_by_action(self, action_id: str, kind: PayloadKind | None = None) -> list[PayloadRecord]:
        """Return all non-purged payloads for an action, optionally filtered by kind."""
        with self._connect() as conn:
            if kind:
                rows = conn.execute(
                    "SELECT * FROM payloads WHERE action_id = ? AND kind = ? AND purged = 0"
                    " ORDER BY created_at",
                    (action_id, kind),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM payloads WHERE action_id = ? AND purged = 0"
                    " ORDER BY created_at",
                    (action_id,),
                ).fetchall()
        return [_row_to_record(r) for r in rows]

    def purge_expired(self) -> int:
        """Replace expired payload data with a tombstone.  Returns the count of purged rows."""
        now = _now_iso()
        tombstone = json.dumps({"_purged": True, "_purged_at": now})
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE payloads SET data_json = ?, byte_length = 0, purged = 1"
                " WHERE purged = 0 AND expires_at IS NOT NULL AND expires_at <= ?",
                (tombstone, now),
            )
            return cursor.rowcount

    def purge_by_action(self, action_id: str) -> int:
        """Purge all payloads for a given action.  Returns the count of purged rows."""
        now = _now_iso()
        tombstone = json.dumps({"_purged": True, "_purged_at": now})
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE payloads SET data_json = ?, byte_length = 0, purged = 1"
                " WHERE action_id = ? AND purged = 0",
                (tombstone, action_id),
            )
            return cursor.rowcount


def _row_to_record(row: sqlite3.Row) -> PayloadRecord:
    return PayloadRecord(
        payload_id=row["payload_id"],
        action_id=row["action_id"],
        kind=row["kind"],
        data_json=row["data_json"],
        byte_length=row["byte_length"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        purged=bool(row["purged"]),
    )
