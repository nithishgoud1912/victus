BEGIN IMMEDIATE;
CREATE TABLE memory_entries (
 memory_id TEXT PRIMARY KEY, type TEXT NOT NULL CHECK(type IN ('preference','summary')),
 protected_value TEXT NOT NULL, provenance TEXT NOT NULL,
 created_at REAL NOT NULL, updated_at REAL NOT NULL, last_confirmed_at REAL NOT NULL,
 expires_at REAL
);
CREATE INDEX memory_lookup ON memory_entries(type, expires_at, last_confirmed_at);
CREATE TABLE memory_refs (
 memory_id TEXT NOT NULL, task_id TEXT NOT NULL, PRIMARY KEY(memory_id,task_id)
);
CREATE TABLE memory_forget_jobs (
 memory_id TEXT PRIMARY KEY, task_ids_json TEXT NOT NULL, created_at REAL NOT NULL
);
CREATE TABLE task_retention (
 task_id TEXT PRIMARY KEY, terminal_at REAL NOT NULL, pinned INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE evidence_index (
 evidence_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, relative_path TEXT NOT NULL UNIQUE,
 sha256 TEXT NOT NULL, byte_length INTEGER NOT NULL, pinned INTEGER NOT NULL DEFAULT 0,
 created_at REAL NOT NULL, expires_at REAL NOT NULL
);
