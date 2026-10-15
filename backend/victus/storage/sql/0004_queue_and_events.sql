-- 0004_queue_and_events.sql
-- Adds sequenced task events and client request deduplication.

-- ── task_events ─────────────────────────────────────────────────────────
-- Sequenced, append-only event log for task lifecycle.
-- event_id is an AUTOINCREMENT integer providing a strictly monotonic ordering source.

CREATE TABLE IF NOT EXISTS task_events (
    event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         TEXT    NOT NULL,
    event_type      TEXT    NOT NULL,
    safe_payload    TEXT    NOT NULL DEFAULT '{}',
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_task_events_task_cursor
    ON task_events (task_id, event_id);

CREATE INDEX IF NOT EXISTS idx_task_events_event_id
    ON task_events (event_id);

-- ── client_requests ─────────────────────────────────────────────────────
-- Client request ID deduplication table.
-- Ensures duplicate submissions return the existing task_id.

CREATE TABLE IF NOT EXISTS client_requests (
    client_request_id   TEXT    PRIMARY KEY,
    task_id             TEXT    NOT NULL,
    created_at          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_client_requests_task
    ON client_requests (task_id);
