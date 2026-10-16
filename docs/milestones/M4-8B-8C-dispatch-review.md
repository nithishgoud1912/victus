# M4 / 8B–8C — Single-use dispatch and durable review

The agent now uses the durable 8A approval store rather than its earlier
proposal-reference timeout gate.

## Dispatch binding and cancellation

`safety/permits.py` exposes `issue_permit()`, `validate_binding()` and
`consume_permit()` both as store methods and module-level helpers. A SQLite
write transaction checks expiry and all immutable bindings, transitions an
approved record to consumed, and removes the token hash before returning.
Cancellation is checked both before entering consumption and inside its
transaction. Permit issuance and consumption remain single use across processes.

The agent prepares an action ledger ID before approval. The dispatcher reuses
that ID and checks its task, tool version, argument hash and prepared status.
It revalidates live policy, latest observation and resolved target, then checks
cancellation and consumes the permit at its dispatch barrier immediately before
marking the action dispatching and invoking the adapter. The existing mutation
lock serializes workflow steps. Runner cancellation uses that same dispatch
barrier; adapter cancellation remains cooperative once dispatch has committed.
Blocked native operations still require the existing outer worker supervisor.

Filesystem bindings include the resolved destination, parent identity and current
file identity/size/modification time. Browser/UIA integrations must provide a
trusted `AgentServices.target_identity` resolver which checks live adapter
freshness; opaque model references alone are insufficient. The browser benchmark
now supplies its real resolver. Adapters still pin/check the actual target when
performing a mutation. A changed or stale target invalidates the approval and
blocks this dispatch. Continuing requires a new observation and approval.

No permit token or raw preview is placed in graph checkpoints. A crash after
consumption cannot recreate or replay the token. Interrupted execution reconciles
the same ledger attempt: unstarted prepared work is cancelled; dispatched or
applied work becomes unknown. Neither case is automatically retried.

## Authenticated approval API

All routes use the existing bearer authentication and host/origin restrictions:

- `GET /api/approvals/{approval_id}` returns metadata.
- `GET /api/approvals/{approval_id}/preview` returns the protected preview to the
  authenticated reviewer while it remains available.
- `POST /api/approvals/{approval_id}/resolve` accepts only a decision and explicit
  review confirmation, for example:

```json
{"decision":"approved","confirmation":"explicit_user_review"}
```

Use `"denied"` to decline. The body cannot supply another action ID, target,
arguments, policy version or tool version. Unknown fields are rejected with 422.
Missing IDs return 404; expired, consumed, previously resolved or invalidated
records return 409 with a state-specific explanation. Resolution after service
Stop also returns 409 and invalidates a live request. Concurrent resolutions are
serialized by the store.

High and critical risk agent tools always pause for explicit review, even when
the policy callback returns true. Voice transcription and model resume data do
not resolve approvals; no voice-confirmation adapter is connected to this route.
The authenticated UI/CLI caller is the trust boundary for explicit user review.
Future voice features must continue to require a separate explicit confirmation
for consequential actions. Approval also cannot waive scopes or tool policy.

The route records the decision. The owner then calls `AgentRunner.resume(task_id)`;
HTTP resolution does not launch another worker or create an unbounded background
task. The foundation task API continues to expose its existing queued file action;
this change does not add an autonomous-agent HTTP submission endpoint.

## Durable LangGraph interrupt

The graph now contains an `authorize → review → execute` path. Authorization
persists the pending request and action ID before entering the separate review
node. Its first operation is `langgraph.types.interrupt()` with task/approval IDs.
There are no external writes before this interrupt in that replayable node.

The owner returns `awaiting_approval`. Polling while pending does not renew expiry,
recreate records, spend active time or invoke tools. Once resolved, resume uses
`Command(resume=True)` as a wake-up signal. The review node reads the saved
decision; a forged resume payload is not authority. Review waiting pauses the
active task clock, keeps its separate expiry, and preserves the prior budget
limits. Cancellation, denial and expiry terminate safely. Dispatch revalidates
the approved action again after resume.

The review node bypasses the ordinary node journal wrapper so legitimate
interrupt replay is not mistaken for an interrupted effect. `GraphInterrupt` is
explicitly rethrown by generic graph/dispatcher boundaries. The JSON checkpoint
serializer supports only the known LangGraph Interrupt structure in addition to
ordinary JSON; it still rejects arbitrary live objects, pickle and dynamic class
imports. At this milestone, service startup preserved live pending/approved
prepared review actions while retaining unknown recovery for dispatched work.
The subsequent 8D recovery milestone supersedes this startup behavior: old
authority is invalidated on service restart, requiring fresh observation/review.

Existing checkpoints using the earlier proposal-only approval payload cannot
silently gain authority through the new store; missing durable approvals fail
closed and require a fresh task/review.

## Validation

`tests/test_approval_dispatch.py` and `tests/live/m4_approval_crash_probe.py` cover:

- Real durable interrupts, repeated polling/replay and reopened graph completion.
- Authenticated resolution, body tampering, voice-only input rejection and clear
  conflicts after expiry/consumption/Stop.
- Target, observation and policy changes, cancellation and expiry before dispatch.
- Cancellation inside permit consumption and concurrent single-use guarantees
  retained from the 8A suite.
- Hard process exits after permit commit and after an actual file write; repeated
  restart performs no write and preserves consumed state/unknown outcomes.
- Explicit interrupt serialization and propagation through dispatcher validation.

Existing graph review tests now perform a saved explicit approval instead of
treating a policy flag change as human approval. No live model benchmark, physical
voice test or native desktop qualification was run for this milestone.

Final validation on 2026-10-16: **445 tests passed in 207.05 seconds**, including
19 new integration cases. Ruff lint and formatting checks passed for the 19
changed Python files; Python compilation and `git diff --check` passed. The
final test artifacts are `.local/8bc-verified.xml` and `.local/8bc-verified.log`.
