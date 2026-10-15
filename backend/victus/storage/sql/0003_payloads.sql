-- 0003_payloads.sql
-- Payload store for raw typed text and large argument bodies.
-- Separated from the action_attempts metadata table so that
-- retention policies can purge payload data independently.

CREATE TABLE IF NOT EXISTS payloads (
    payload_id  TEXT    PRIMARY KEY,
    action_id   TEXT    NOT NULL,
    kind        TEXT    NOT NULL CHECK (kind IN ('arguments', 'typed_text', 'output')),
    data_json   TEXT    NOT NULL,
    byte_length INTEGER NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    expires_at  TEXT,
    purged      INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (action_id) REFERENCES action_attempts (action_id)
);

CREATE INDEX IF NOT EXISTS idx_payloads_action
    ON payloads (action_id);

CREATE INDEX IF NOT EXISTS idx_payloads_retention
    ON payloads (expires_at)
    WHERE purged = 0 AND expires_at IS NOT NULL;
