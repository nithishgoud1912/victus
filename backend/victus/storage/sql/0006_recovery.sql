BEGIN IMMEDIATE;
CREATE TABLE recovery_reconciliations (
    reconciliation_id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL REFERENCES action_attempts(action_id),
    tool_version TEXT NOT NULL,
    canonical_args_hash TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK(verdict IN ('present','absent','unknown')),
    evidence_ref TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX idx_recovery_action ON recovery_reconciliations(action_id);
CREATE TABLE recovery_retries (
    action_id TEXT NOT NULL REFERENCES action_attempts(action_id),
    retry_number INTEGER NOT NULL CHECK(retry_number BETWEEN 1 AND 2),
    budget_json TEXT NOT NULL,
    PRIMARY KEY(action_id, retry_number)
);
