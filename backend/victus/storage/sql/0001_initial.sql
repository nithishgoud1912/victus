-- 0001_initial.sql
-- Foundation-era schema extracted from the inline Database.__init__ DDL.
-- This migration is applied idempotently; it creates the F1 tasks table
-- only when it does not already exist.

PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS tasks (
    task_id     TEXT PRIMARY KEY,
    result_json TEXT NOT NULL
);
