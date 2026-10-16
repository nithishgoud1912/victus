"""Opaque, durable single-use permits bound to an approved action.

Consume immediately before dispatch under the mutation/stop barrier, rechecking
live target, observation and policy first. A consumed permit never authorizes a
retry or proves success; uncertain effects still belong in the action ledger.
"""

import hashlib
import secrets

from victus.safety.approvals import ApprovalBinding, ApprovalRecord, ApprovalStore


def _token_hash(token: str) -> str:
    if not isinstance(token, str) or len(token) != 43:
        raise PermissionError("Invalid permit")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class PermitStore:
    def __init__(self, approvals: ApprovalStore):
        self.approvals = approvals

    def issue(self, approval_id: str, binding: ApprovalBinding) -> str:
        binding = ApprovalBinding.model_validate(binding)
        token = secrets.token_urlsafe(32)
        issued = False
        with self.approvals.connect() as db:
            now = self.approvals.now()
            self.approvals._expire(db, now)
            row = db.execute(
                "SELECT * FROM approvals WHERE approval_id=?", (approval_id,)
            ).fetchone()
            if row and row["state"] == "approved":
                record = ApprovalRecord.model_validate(dict(row))
                if record.binding() != binding:
                    db.execute(
                        "UPDATE approvals SET state='invalidated',updated_at=? WHERE approval_id=?",
                        (now, approval_id),
                    )
                else:
                    issued = (
                        db.execute(
                            "INSERT OR IGNORE INTO approval_permits VALUES (?,?,?)",
                            (_token_hash(token), approval_id, record.expires_at),
                        ).rowcount
                        == 1
                    )
        if not issued:
            raise PermissionError("Approval unavailable or permit already issued")
        return token

    def consume(self, token: str, binding: ApprovalBinding, *, _cancelled=None) -> ApprovalRecord:
        binding = ApprovalBinding.model_validate(binding)
        token_hash = _token_hash(token)
        consumed = None
        with self.approvals.connect() as db:
            now = self.approvals.now()
            self.approvals._expire(db, now)
            row = db.execute(
                "SELECT a.* FROM approvals a JOIN approval_permits p "
                "ON p.approval_id=a.approval_id WHERE p.token_hash=? "
                "AND p.expires_at>? AND a.state='approved'",
                (token_hash, now),
            ).fetchone()
            if row:
                record = ApprovalRecord.model_validate(dict(row))
                matches = record.binding() == binding and not (_cancelled and _cancelled())
                db.execute(
                    "UPDATE approvals SET state=?,updated_at=? WHERE approval_id=?",
                    ("consumed" if matches else "invalidated", now, record.approval_id),
                )
                db.execute("DELETE FROM approval_permits WHERE token_hash=?", (token_hash,))
                if matches:
                    consumed = record.model_copy(update={"state": "consumed", "updated_at": now})
        if consumed is None:
            raise PermissionError("Permit unavailable or binding changed")
        return consumed

    def issue_permit(self, approval_id: str, binding: ApprovalBinding) -> str:
        return self.issue(approval_id, binding)

    def validate_binding(self, approval_id: str, binding: ApprovalBinding) -> ApprovalRecord:
        record = self.approvals.get(approval_id)
        if record is None or record.state != "approved":
            raise PermissionError("Approval is not approved or has expired/been consumed")
        if record.binding() != ApprovalBinding.model_validate(binding):
            self.approvals.invalidate(approval_id)
            raise PermissionError("Target changed; obtain a new observation and approval")
        return record

    def consume_permit(self, token: str, binding: ApprovalBinding, *, cancelled) -> ApprovalRecord:
        # Caller holds the dispatch barrier. No await between this check and consume.
        if cancelled():
            raise PermissionError("Dispatch cancelled")
        return self.consume(token, binding, _cancelled=cancelled)


def issue_permit(store: PermitStore, approval_id: str, binding: ApprovalBinding) -> str:
    return store.issue_permit(approval_id, binding)


def validate_binding(
    store: PermitStore, approval_id: str, binding: ApprovalBinding
) -> ApprovalRecord:
    return store.validate_binding(approval_id, binding)


def consume_permit(store: PermitStore, token: str, binding: ApprovalBinding, *, cancelled):
    return store.consume_permit(token, binding, cancelled=cancelled)
