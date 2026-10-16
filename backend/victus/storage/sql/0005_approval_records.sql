-- The migration runner commits the schema version in this same transaction.
BEGIN IMMEDIATE;
ALTER TABLE approvals RENAME TO approvals_legacy;

CREATE TABLE approvals (
    approval_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_version TEXT NOT NULL,
    canonical_args_hash TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    target_identity TEXT NOT NULL,
    observation_identity TEXT NOT NULL,
    preview_ref TEXT NOT NULL,
    expires_at REAL NOT NULL,
    state TEXT NOT NULL CHECK(state IN
        ('pending','approved','denied','expired','invalidated','consumed')),
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX idx_approvals_task ON approvals(task_id, state);
-- Legacy decisions cannot establish any of the new bindings. Preserve the
-- original audit rows, but never import them as executable approvals.
INSERT INTO approvals SELECT approval_id, 'legacy:unbound', action_id,
    'legacy:unbound', 'legacy:unbound', printf('%064d', 0), 'legacy:unbound',
    'legacy:unbound', 'legacy:unbound', 'legacy:unavailable', 0, 'invalidated', 0, 0
    FROM approvals_legacy;

CREATE TABLE approval_previews (
    preview_ref TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    protected_payload BLOB,
    expires_at REAL NOT NULL
);
CREATE TABLE approval_permits (
    token_hash TEXT PRIMARY KEY,
    approval_id TEXT NOT NULL UNIQUE REFERENCES approvals(approval_id),
    expires_at REAL NOT NULL
);
