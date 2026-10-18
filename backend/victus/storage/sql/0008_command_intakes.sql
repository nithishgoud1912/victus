-- Protected clarification intent and stable mapping to the existing task queue.
CREATE TABLE command_intakes (
 command_id TEXT PRIMARY KEY,
 request_id TEXT NOT NULL UNIQUE,
 payload TEXT,
 state TEXT NOT NULL CHECK(state IN ('waiting','ready','submitted','invalidated')),
 task_id TEXT,
 expires_at REAL NOT NULL
);
