"""Sequenced task events with persistent ordering and safe payloads.

Every event has a monotonic integer event_id (from SQLite AUTOINCREMENT),
a task_id, an event_type, an ISO-8601 UTC timestamp, and a sanitized safe_payload.
Raw typed text and sensitive credentials are never stored in the audit log.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


_SENSITIVE_KEYS = {
    "text",
    "password",
    "secret",
    "token",
    "key",
    "authorization",
    "prompt",
    "goal",
    "transcript",
    "content",
    "html",
    "dom",
    "messages",
    "arguments",
}


def sanitize_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Return a safe copy of *payload*, masking sensitive fields."""
    if not payload:
        return {}
    safe: dict[str, Any] = {}
    for key, value in payload.items():
        lower_key = key.lower()
        if lower_key in _SENSITIVE_KEYS:
            if lower_key == "text" and isinstance(value, str):
                safe[key] = f"<{len(value)} chars redacted>"
            else:
                safe[key] = "<redacted>"
        elif isinstance(value, dict):
            safe[key] = sanitize_payload(value)
        elif isinstance(value, (list, tuple)):
            safe[key] = _sanitize_sequence(value)
        else:
            safe[key] = value
    return safe


def _sanitize_sequence(values: list | tuple) -> list:
    return [
        sanitize_payload(value)
        if isinstance(value, dict)
        else _sanitize_sequence(value)
        if isinstance(value, (list, tuple))
        else value
        for value in values
    ]


@dataclass(frozen=True)
class EventRecord:
    """A durable, sequenced event entry."""

    event_id: int
    task_id: str
    event_type: str
    timestamp: str
    safe_payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "safe_payload": self.safe_payload,
        }

    def to_sse(self) -> str:
        """Format as Server-Sent Events (SSE) message."""
        payload_json = json.dumps(self.to_dict())
        return f"id: {self.event_id}\nevent: {self.event_type}\ndata: {payload_json}\n\n"


class EventManager:
    """Persist events; stream readers poll ordered batches from the same log."""

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

    def record_event(
        self,
        task_id: str,
        event_type: str,
        safe_payload: dict[str, Any] | None = None,
    ) -> EventRecord:
        """Insert a sequenced event into the database."""
        allowed = {
            "tool",
            "tool_name",
            "action_id",
            "approval_id",
            "approval_ref",
            "status",
            "verified",
            "error_code",
            "reason",
            "output_name",
            "sha256",
            "policy_version",
            "decision",
            "elapsed_seconds",
            "duration_seconds",
            "step",
            "request_id",
        }
        metadata = {key: value for key, value in (safe_payload or {}).items() if key in allowed}
        sanitized = sanitize_payload(metadata)
        payload_str = json.dumps(sanitized)

        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO task_events (task_id, event_type, safe_payload)
                   VALUES (?, ?, ?)""",
                (task_id, event_type, payload_str),
            )
            event_id = cursor.lastrowid
            row = conn.execute(
                "SELECT created_at FROM task_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            timestamp = row["created_at"] if row else _now_iso()

        event = EventRecord(
            event_id=event_id,
            task_id=task_id,
            event_type=event_type,
            timestamp=timestamp,
            safe_payload=sanitized,
        )

        return event

    def get_events(
        self,
        after_cursor: int | None = None,
        task_id: str | None = None,
        limit: int | None = None,
        through_cursor: int | None = None,
    ) -> list[EventRecord]:
        """Fetch past events from SQLite ordered strictly by event_id."""
        query = "SELECT event_id, task_id, event_type, safe_payload, created_at FROM task_events WHERE 1=1"
        params: list[Any] = []

        if after_cursor is not None:
            query += " AND event_id > ?"
            params.append(after_cursor)

        if task_id is not None:
            query += " AND task_id = ?"
            params.append(task_id)

        if through_cursor is not None:
            query += " AND event_id <= ?"
            params.append(through_cursor)

        query += " ORDER BY event_id ASC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        events: list[EventRecord] = []
        for row in rows:
            try:
                payload = json.loads(row["safe_payload"])
            except Exception:
                payload = {}
            events.append(
                EventRecord(
                    event_id=row["event_id"],
                    task_id=row["task_id"],
                    event_type=row["event_type"],
                    timestamp=row["created_at"],
                    safe_payload=payload,
                )
            )
        return events

    def get_latest_event_id(self) -> int:
        """Return the highest event_id, or 0 if none."""
        with self._connect() as conn:
            row = conn.execute("SELECT MAX(event_id) FROM task_events").fetchone()
            return row[0] if row and row[0] is not None else 0
