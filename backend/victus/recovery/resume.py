"""Crash recovery invalidates authority and never dispatches an external write."""

from victus.safety.approvals import ApprovalStore


class ResumeManager:
    def __init__(self, ledger, approvals: ApprovalStore):
        self.ledger, self.approvals = ledger, approvals

    def invalidate(self, task_id: str | None = None) -> int:
        with self.approvals.connect() as db:
            now = self.approvals.now()
            self.approvals._expire(db, now)
            sql = "UPDATE approvals SET state='invalidated',updated_at=? WHERE state IN ('pending','approved')"
            params = [now]
            if task_id is not None:
                sql += " AND task_id=?"
                params.append(task_id)
            count = db.execute(sql, params).rowcount
            db.execute(
                "DELETE FROM approval_permits WHERE approval_id IN "
                "(SELECT approval_id FROM approvals WHERE state IN ('invalidated','expired'))"
            )
            return count

    def recover(self, *, quiesced: bool, task_id: str | None = None):
        if quiesced is not True:
            raise PermissionError("Owned workers must be stopped before crash recovery")
        self.invalidate(task_id)
        if task_id is not None:
            records = self.ledger.list_for_task(task_id)
        else:
            with self.ledger._connect() as db:
                ids = [
                    row[0]
                    for row in db.execute(
                        "SELECT action_id FROM action_attempts WHERE status IN "
                        "('prepared','dispatching','applied','unknown') ORDER BY rowid"
                    )
                ]
            records = [self.ledger.get(action_id) for action_id in ids]
        for record in records:
            if record.status == "prepared":
                self.ledger.mark_cancelled(record.action_id)
            elif record.status in {"dispatching", "applied"}:
                self.ledger.mark_unknown(record.action_id, error_code="RESTART_REQUIRES_REVIEW")
        return [record.action_id for record in records]

    async def resume(self, reconciler, *, quiesced: bool, task_id: str | None = None):
        references = self.recover(quiesced=quiesced, task_id=task_id)
        proofs = []
        for action_id in references:
            record = self.ledger.get(action_id)
            if record.status == "unknown":
                proofs.append(await reconciler.reconcile(action_id, quiesced=quiesced))
        return proofs
