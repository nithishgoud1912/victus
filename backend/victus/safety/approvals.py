"""Durable, payload-bound approvals. Only trusted review code may decide them.

Hashes do not conceal arguments. Preview bodies are stored separately with
retention and Windows current-user DPAPI protection (no model/API exposure).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from victus.safety.previews import protect, unprotect

ApprovalState = Literal["pending", "approved", "denied", "expired", "invalidated", "consumed"]


def argument_hash(arguments: dict) -> str:
    if not isinstance(arguments, dict):
        raise TypeError("Arguments must be a JSON object")
    encoded = json.dumps(
        arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ApprovalBinding(BaseModel):
    """Use trusted resolved identities, not model-supplied display labels."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    task_id: str = Field(min_length=1, max_length=256)
    action_id: str = Field(min_length=1, max_length=256)
    tool_name: str = Field(min_length=1, max_length=256)
    tool_version: str = Field(min_length=1, max_length=256)
    canonical_args_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_version: str = Field(min_length=1, max_length=256)
    target_identity: str = Field(min_length=1, max_length=2048)
    observation_identity: str = Field(min_length=1, max_length=256)


class ApprovalRecord(ApprovalBinding):
    approval_id: str
    preview_ref: str
    expires_at: float
    state: ApprovalState
    created_at: float
    updated_at: float

    def binding(self) -> ApprovalBinding:
        return ApprovalBinding.model_validate(
            {name: getattr(self, name) for name in ApprovalBinding.model_fields}
        )


class ApprovalStore:
    """Requires a migrated service database; no authority comes from model output.

    Every state check occurs under a SQLite write lock. Expiry is evaluated on
    every read/decision/permit use, independent of scheduled cleanup.
    """

    def __init__(self, db_path: Path, *, clock=time.time):
        self.db_path, self.clock = Path(db_path), clock
        if self.db_path.is_symlink() or not self.db_path.is_file():
            raise ValueError("Expected a migrated private database")
        if os.name != "nt":
            self.db_path.chmod(0o600)

    def now(self):
        now = float(self.clock())
        if not math.isfinite(now):
            raise ValueError("Invalid clock")
        return now

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db_path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _expire(self, db, now):
        db.execute(
            "UPDATE approvals SET state='expired', updated_at=? "
            "WHERE state IN ('pending','approved') AND expires_at<=?",
            (now, now),
        )
        db.execute(
            "UPDATE approval_previews SET protected_payload=NULL WHERE expires_at<=?", (now,)
        )

    def request(self, binding: ApprovalBinding, preview: dict, *, ttl_seconds=60) -> ApprovalRecord:
        binding = ApprovalBinding.model_validate(binding)
        if not math.isfinite(ttl_seconds) or not 0 < ttl_seconds <= 300:
            raise ValueError("Approval expiry must be within 300 seconds")
        if not isinstance(preview, dict):
            raise TypeError("Preview must be a JSON object")
        body = json.dumps(preview, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(body) > 128000:
            raise ValueError("Preview exceeds retention payload limit")
        protected = protect(body)
        now = self.now()
        record = ApprovalRecord(
            **binding.model_dump(),
            approval_id=uuid4().hex,
            preview_ref=uuid4().hex,
            expires_at=now + ttl_seconds,
            state="pending",
            created_at=now,
            updated_at=now,
        )
        with self.connect() as db:
            self._expire(db, now)
            db.execute(
                "INSERT INTO approval_previews VALUES (?,?,?,?)",
                (record.preview_ref, record.action_id, protected, record.expires_at),
            )
            values = record.model_dump()
            db.execute(
                f"INSERT INTO approvals ({','.join(values)}) VALUES "
                f"({','.join('?' for _ in values)})",
                tuple(values.values()),
            )
        return record

    def get(self, approval_id: str) -> ApprovalRecord | None:
        with self.connect() as db:
            self._expire(db, self.now())
            row = db.execute(
                "SELECT * FROM approvals WHERE approval_id=?", (approval_id,)
            ).fetchone()
        return ApprovalRecord.model_validate(dict(row)) if row else None

    def preview(self, approval_id: str, *, task_id: str) -> dict:
        """Trusted authenticated reviewer only; knowing a preview ref is insufficient."""
        with self.connect() as db:
            now = self.now()
            self._expire(db, now)
            row = db.execute(
                "SELECT p.protected_payload FROM approval_previews p JOIN approvals a "
                "ON a.preview_ref=p.preview_ref AND a.action_id=p.action_id "
                "WHERE a.approval_id=? AND a.task_id=? AND a.state IN ('pending','approved') "
                "AND a.expires_at>? AND p.expires_at>?",
                (approval_id, task_id, now, now),
            ).fetchone()
        if row is None or row[0] is None:
            raise PermissionError("Preview unavailable")
        return json.loads(unprotect(row[0]))

    def decide(
        self, approval_id: str, binding: ApprovalBinding, *, approved: bool
    ) -> ApprovalRecord:
        if type(approved) is not bool:
            raise TypeError("Explicit review decision required")
        binding = ApprovalBinding.model_validate(binding)
        accepted = False
        with self.connect() as db:
            now = self.now()
            self._expire(db, now)
            row = db.execute(
                "SELECT * FROM approvals WHERE approval_id=?", (approval_id,)
            ).fetchone()
            if row and row["state"] == "pending":
                record = ApprovalRecord.model_validate(dict(row))
                matches = record.binding() == binding
                state = ("approved" if approved else "denied") if matches else "invalidated"
                db.execute(
                    "UPDATE approvals SET state=?,updated_at=? WHERE approval_id=?",
                    (state, now, approval_id),
                )
                accepted = matches
        if not accepted:
            raise PermissionError("Approval unavailable or binding changed")
        return self.get(approval_id)

    def invalidate(self, approval_id: str) -> bool:
        with self.connect() as db:
            now = self.now()
            self._expire(db, now)
            return (
                db.execute(
                    "UPDATE approvals SET state='invalidated',updated_at=? "
                    "WHERE approval_id=? AND state IN ('pending','approved')",
                    (now, approval_id),
                ).rowcount
                == 1
            )

    def purge_expired(self) -> int:
        with self.connect() as db:
            now = self.now()
            count = db.execute(
                "SELECT count(*) FROM approval_previews "
                "WHERE protected_payload IS NOT NULL AND expires_at<=?",
                (now,),
            ).fetchone()[0]
            self._expire(db, now)
            db.execute("DELETE FROM approval_permits WHERE expires_at<=?", (now,))
            return count
