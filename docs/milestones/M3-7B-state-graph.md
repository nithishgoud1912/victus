# M3 section 7B: persistent state and bounded graph

Implemented a real LangGraph `StateGraph`, pinned to `langgraph==1.2.15` and
`langgraph-checkpoint-sqlite==3.1.2` (full dependency resolution in `backend/uv.lock`).
This change builds on section 7A / PR #5. It does not enable an autonomous public API
or claim that the candidate Ollama model, Windows applications or public sites are qualified.

## State and persistence

`agent/state.py` defines the checkpoint state and validates snapshots strictly. It contains
`task_id`, `goal_payload_ref`, task status, observation references, action ledger references,
current proposal reference, approval/evidence references, bounded safe error history,
remaining budgets, cancellation status, node sequence and next node. The current proposal
is a typed reference to the full validated decision in restricted payload storage; raw
arguments, goal text, observations and model answers do not enter graph checkpoints.

`storage/checkpoints.py` uses a file-backed **AsyncSqliteSaver**, WAL and synchronous FULL
commits in `<data_dir>/agent/checkpoints.sqlite3`. `AgentRunner` invokes the graph with
`durability="sync"`, task ID as thread ID, and a bounded recursion limit. The supported
`agent(...)` entry point always opens this persistent saver. An in-memory saver is rejected
by the graph builder. The serializer accepts bounded JSON only: no pickle or arbitrary
class reconstruction. Live adapters, locators, COM objects, service objects and callbacks
are never checkpointed.

An OS owner lock serializes graph access to the checkpoint directory; the runner rejects
concurrent invocations and duplicate starts. This is additional to the existing runtime's
resource/worker ownership requirements, not a replacement for them. Goal, proposal,
observation, approval and evidence payloads are task- and kind-bound, at most 128 KB, and
expire within 24 hours. `purge_expired()` removes expired raw payloads; unavailable payloads
block progress. Files have private creation modes where the operating system supports them.
Checkpoint and journal retention should be managed with completed-task retention policy.

## Graph and domain boundaries

The main path is:

`intake -> route -> observe -> propose -> validate -> authorize -> execute -> verify`

Each module under `agent/nodes/` implements one operation. `AgentServices` supplies trusted
routing, observation, planning, target validation, authorization and independent goal
verification. Nodes do not import Playwright or pywinauto.

- `verify` continues through `observe`, finalizes a verified goal, or sends failure to
  `failed -> recover`. Recovery may request a new observation or proposal within its
  budget. Uncertain effects stop for review; they are never automatically retried.
- A model finish decision goes from validation to verification. The independent goal
  verifier must prove completion, including promised source counts or file contents.
  The model's finish text is never accepted as evidence. An explicit blocked finish stops.
- `execute.py` calls the **existing shared Dispatcher.dispatch_step**. It does not invoke
  an adapter directly. Policy, tool schemas, risk/scope authorization, cancellation,
  ledger writes, restricted payloads and the tool's verifier remain in that dispatcher.
  Existing file-returning tools are supported by normalizing their bounded workspace
  artifact to JSON metadata while passing the actual Path to their original verifier.
- `verify.py` consumes task-bound, verified ledger receipts and calls the trusted independent
  goal verifier. It checks tool/argument identity for the latest execution. Action verification
  and whole-task completion remain distinct; a verified action can leave the goal incomplete.
- Authorization binds an expiring approval reference to the exact stored proposal. Live
  target validation and current authorization run again immediately before dispatch.

Pending approvals end the invocation with `awaiting_approval` and a durable checkpoint.
After the actual approval service receives the user's decision, `resume(task_id)` re-enters
validation before authorization. It neither fabricates an approval nor accepts client-supplied
checkpoint state. The approval callback returns True (approved), None (pending), or False
(denied). Domain callbacks must implement real policy and freshness checks; never bind a
model answer as an approval or goal verifier.

## Budgets and cancellation

Defaults: 96 graph nodes, 8 actions, 16 observations, 8 model requests, 4096 reserved output
tokens, one schema repair, two recovery attempts, and a 180-second task deadline. Initial
deadlines cannot exceed ten minutes. The remaining counters and wall-clock deadline persist
across restart. Normal callbacks are bounded by a 60-second async node deadline and the
remaining task deadline. Native blocking calls still require the existing M1 process
supervisor; coroutine cancellation cannot terminate a stuck COM call. Construct services and
adapter owners inside the appropriate supervised worker, and keep the existing resource locks.

`GatewayPlanner` reconstructs M3-7A allowances from persisted remaining counters. A successful
planning step charges its actual gateway reservations. Failed or interrupted planning is
charged conservatively for up to two calls/1024 output tokens and consumes the remaining
repair allowance, so restarting or recovery cannot replenish a budget. Recovery and
observation attempts are finite too. No LangGraph automatic node retry policy is installed.

`runner.cancel(task_id)` latches cancellation durably; an optional shared stop Event is also
latched when observed. Async operations are monitored for cancellation. Stop before an action
prevents dispatch. Stop during an effect cancels its awaiting operation, reconciles the ledger
and leaves the result unknown. No rollback is claimed.

## Restart without effect replay

A durable node journal records `(task_id, sequence, node)` **before** the domain operation,
then its reference-only result **before** LangGraph's checkpoint. Recovery has two cases:

1. The node result is durable: return the cached state update without repeating the domain
   call, then continue from the persistent graph checkpoint.
2. The node started but has no durable result: mark the task unknown and require review.
   For execution, reconcile task-bound ledger records, retain action references, cancel
   prepared attempts and mark interrupted dispatching/applied attempts unknown.

This does not promise atomic transactions with external applications or exactly-once effects.
It specifically avoids repeating an effect in the crash window between the effect and its
checkpoint. Even a read/model operation interrupted in that window stops conservatively.
Use the same task ID and data directory on resume; do not resubmit it as a new task.

## Composition and validation

```python
# Bind reviewed, owner-local domain services before entering the graph.
# `services` is an AgentServices instance; store and context_factory share task ownership.
goal_ref = services.store.put_payload(task_id, "goal", reviewed_goal)
async with agent(services) as runner:
    result = await runner.start(task_id, goal_ref)
# After process restart, recreate the same trusted services and reacquire adapter owners.
async with agent(services) as runner:
    result = await runner.resume(task_id)
```

Tests use deterministic model/domain responses with the real graph, SQLite saver, shared
dispatcher, ledger, independent verifiers and local files. They cover normal and multi-action
flows, finish claims, denied/pending approvals, restart revalidation, budgets, recovery,
cancellation, task-scoped payload retention, concurrency and the existing F1 note tool.
They also exercise the real M3-7A gateway using fake provider responses, including a repair
that cannot reset between graph turns.

- Full Python suite: **341 passed**.
- Graph tests: **34 passed**, including two hard subprocess exits.
- Changed Python files pass Ruff.
- [Recorded hard-restart probe](evidence/M3-7B-restart-probe.json): after-write crash resumes
  unknown with zero repeated writes; after-journal/before-checkpoint crash resumes through
  verification with zero repeated writes. Each leaves exactly one saved fixture file.

Probe entry point: `tests/live/m3_graph_crash_probe.py`. It deliberately exits with 71 or 72
for its crash modes; `resume` runs in a separate process. This is a real local persistence
probe using deterministic fixture services, not live model or Windows UIA qualification.
