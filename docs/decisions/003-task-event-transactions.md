# Decision 003: Task/event transaction ownership

Date: 2026-10-18. Scope: V2.2 source candidate.

TaskQueue remains the single scheduler with one active task and at most three
pending tasks. Admission is serialized in the process protected by the existing
data-directory instance lock. The task, client request mapping and initial safe
event commit before the queue can expose work. A repeated retained request ID
returns its original task; changed content never replaces the original command.

`EventManager.record_event_in` appends to a caller-owned transaction without
committing. Both admission and `Database.save(..., event_type=...,
event_payload=...)` use it. Queue start/terminal/Stop/error transitions therefore
commit the task snapshot, retention marker when terminal, and lifecycle event
together. Metadata-only action-ID binding still uses save without a lifecycle
event because it does not change task status. Startup recovery already updates
interrupted tasks and their events in one transaction.

The same SQLite AUTOINCREMENT log serves ordered replay and live polling. There
is no in-memory publication handover. Snapshots use existing cursor IDs and do
not append audit rows or submit work. Querying a task or reconnecting cannot
create an action or approve anything. Task outcome and action effect state stay
separate: interrupted queued work is cancelled; a possibly dispatched effect is
unknown, even if its task was interrupted. Recovery does not execute adapters.

Pending command bodies are volatile and are discarded on restart, deliberately
avoiding automatic resume. Once an action is prepared, its arguments use the
existing restricted, expiring payload store; task/action/event metadata retain
only references, hashes and safe operational fields. Existing task retention is
unchanged: deduplication persists with retained task history (30 days for unpinned
terminal tasks), not forever after that history is deleted.

Each migration's DDL/data and schema version marker now share an explicit
transaction. Historical migration files 5-7 already opened BEGIN IMMEDIATE; the
runner removes that redundant opening in memory before wrapping the script.
Existing SQL files, table definitions and schema version remain unchanged. SQL
failure or failure to insert the version marker rolls back the migration. This
fix changes execution boundaries and needs no additive schema migration.

Qualification uses fault injection, concurrent admission, restart, paginated
replay, authenticated loopback SSE, and Chromium refresh/reconnect checks. It
does not qualify a new executable, public-site workflow, physical device or new
long-duration soak.
