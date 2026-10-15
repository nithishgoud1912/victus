-- 0002_action_ledger.sql
-- Adds the durable action ledger (action_attempts), the event audit log,
-- and the approval gate table.  The F1 tasks table is preserved as-is;
-- a development-only migration marks it deprecated without dropping it.

-- ── action_attempts ─────────────────────────────────────────────────────
-- One row per dispatch attempt.  The canonical_args_hash lets us detect
-- duplicate requests without storing the full argument payload here.

CREATE TABLE IF NOT EXISTS action_attempts (
    action_id           TEXT    PRIMARY KEY,
    tool_name           TEXT    NOT NULL,
    tool_version        TEXT    NOT NULL,
    canonical_args_hash TEXT    NOT NULL,
    expected_effect_ref TEXT,
    status              TEXT    NOT NULL DEFAULT 'prepared'
                                CHECK (status IN (
                                    'prepared', 'dispatching', 'applied',
                                    'verified', 'unknown', 'failed', 'cancelled'
                                )),
    error_code          TEXT,
    output_name         TEXT,
    sha256              TEXT,
    created_at          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    dispatched_at       TEXT,
    applied_at          TEXT,
    verified_at         TEXT,
    finished_at         TEXT
);

CREATE INDEX IF NOT EXISTS idx_action_attempts_status
    ON action_attempts (status)
    WHERE status IN ('prepared', 'dispatching', 'applied');

CREATE INDEX IF NOT EXISTS idx_action_attempts_tool
    ON action_attempts (tool_name, created_at);

-- ── events ──────────────────────────────────────────────────────────────
-- Append-only audit log.  Every state transition on an action_attempt
-- emits an event row.  event_data is a JSON blob whose schema depends
-- on event_type.

CREATE TABLE IF NOT EXISTS events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    action_id   TEXT    NOT NULL,
    event_type  TEXT    NOT NULL,
    event_data  TEXT    NOT NULL DEFAULT '{}',
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (action_id) REFERENCES action_attempts (action_id)
);

CREATE INDEX IF NOT EXISTS idx_events_action
    ON events (action_id, event_id);

-- ── approvals ───────────────────────────────────────────────────────────
-- Optional pre-dispatch approval gate.  An action_attempt whose tool has
-- risk_floor >= HIGH is blocked until an approval row appears.

CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT    PRIMARY KEY,
    action_id   TEXT    NOT NULL UNIQUE,
    decision    TEXT    NOT NULL CHECK (decision IN ('approved', 'denied')),
    reason      TEXT,
    decided_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (action_id) REFERENCES action_attempts (action_id)
);

-- ── F1 compatibility ────────────────────────────────────────────────────
-- Mark legacy tasks table deprecated but keep it readable.  A future
-- production migration may drop it once all consumers have switched to
-- action_attempts.  For development, leave it intact.
