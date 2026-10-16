# M3 7C: Shared budgets and progress rules

## Build guide

Preserve the existing persistent graph and dispatcher. Extract budget policy to
`agent/budgets.py` and add checkpointable loop fingerprints in `agent/progress.py`.
Default to 12 action attempts, eight model requests, one repair per decision,
180 seconds of active work and a separate finite graph recursion limit. Charge
failed/retried requests and execution attempts, pause only for explicit approval
waits and expire those waits independently. Detect equivalent proposals against
unchanged semantic observations, permit one recovery, then stop as partial.

Wire the rules through state, graph guards, model gateway/planner, proposal,
authorization and recovery nodes. Keep hashes/references in checkpoints, not raw
observation or argument content. Preserve unknown side effects and no replay on
restart. Test limits, request failures/repairs, restart, approval expiry, active
time, harmless observation-ID churn, real changes and bounded repeated proposals.

## Evidence

Validated on Windows with Python 3.12 on 16 October 2026:

- Focused graph/gateway/policy checkpoint: 64 passed before the final two boundary tests.
- Final explicit Python regression suite, including all 18 new 7C tests:
  **360 passed in 117.16 seconds**.
- Changed agent/gateway code and tests pass Ruff lint and formatting checks.
- Compilation and Git whitespace checks passed.
- Tests preserve the previous real hard-restart/no-effect-replay checks.

Windows test-harness corrections made during regression: bounded parameter IDs
prevent the oversized-parser-input test from exceeding Windows' environment
variable limit; the partial-write fixture waits for its final event before
asserting the complete event history. Assertions and input sizes were retained.

Run the tests with the locked development dependencies installed. This execution
needed an isolated test directory and Windows asyncio/loopback access outside
the restricted test sandbox; no desktop or model access was requested. Package
manifests and the lockfile were unchanged. Existing optional voice dependencies
were preserved/restored after synchronizing the locked graph dependencies.

For example, from `backend/`:

```powershell
uv run python -m pytest -p no:cacheprovider tests/test_agent_budgets_progress.py tests/test_agent_graph.py tests/test_model_gateway.py
```

## Implemented policy

`agent/budgets.py` owns validated defaults: 12 action attempts, eight total model
requests, 4096 reserved output tokens, one repair per decision, 180 seconds of
active work, 96 node entries, 16 observations, two general recoveries and a
separate LangGraph recursion limit of 80. Limits are finite and configurable by
trusted application code. No path automatically increases recursion limits.

The graph checkpoints the remaining allowances. Successful and failed model
requests consume their actual gateway reservations, including repair requests.
Each new decision can repair once, using the same remaining task request/token
allowances. `schema_repairs` is the per-decision setting; `repairs_used` records
the task's cumulative repair use. Failed or interrupted custom planning without
usage data is charged conservatively for up to two calls and 1024 reserved
tokens. Retried execution, observation and recovery consume their corresponding
shared counters. Approval/resume does not replenish any counter.

Active seconds are measured with a monotonic clock around graph-node work and
persisted after each node. Operation deadlines use the remaining active seconds;
the active clock does not run while the graph is parked for approval or between
invocations. Existing optional `deadline_epoch` inputs remain supported as an
additional deadline and are shifted by approval waiting. Abruptly interrupted
nodes retain the existing journal's conservative unknown/review behavior.

An explicit pending approval records an independent 60-second expiry. Repeated
polling cannot extend that original expiry. Resume checks cancellation and
expiry, then revalidates the exact saved proposal before authorization. Expiry
is checked again during revalidation/authorization; an expired wait never
dispatches. Actual M4 permit binding and effect reconciliation remain separate.

`agent/progress.py` hashes each proposal with its current semantic observation.
Dictionary key order, observation IDs, top-level capture timestamps and refreshed
browser target references do not manufacture progress. Target references map to
their observed identities and positions, so distinct same-label targets remain
distinct. Tool/argument changes and actual observed content changes are retained.
Paraphrasing a finish reason does not count as progress. Only bounded digests and
flags enter checkpoint state; source text remains in restricted payload storage.

On the first repeated equivalent proposal, dispatch is withheld and one bounded
re-observation/replanning recovery is attempted. If that proposal against that
observation repeats again, the graph ends with `status=partial` and
`error_code=NO_PROGRESS`, preserving evidence and action references. With no
recovery budget left it stops immediately. History survives checkpoint reopen
and detects alternating proposals too. An uncertain external effect always
remains `unknown`; progress policy cannot relabel it as successful or retry it.

Graph recursion exhaustion is caught and persisted as a terminal incomplete
result (`GRAPH_RECURSION_EXHAUSTED`). Resuming that checkpoint does not silently
start another recursion allowance. The separate node counter also persists.

This policy supersedes the older 7B defaults of eight actions, one task-wide
repair and a 300-superstep invocation ceiling. Budgets remain importable from
`agent.state` for existing callers, with their implementation in `agent.budgets`.

## Verification scope

`test_agent_budgets_progress.py` adds direct policy tests and real persistent graph
fixtures for independent counters, shared repair costs, actual failure accounting,
semantic equivalence, changing observations/targets, loop recovery, restart,
approval pause/expiry, active timeout and recursion exhaustion. Existing graph
tests now expect the requested per-decision repair and twelve-action semantics.

All model replies and automation services in these tests are deterministic
fixtures. The tests use real SQLite checkpoints, the real dispatcher, isolated
file effects, supervised subprocesses and local loopback streaming. They do not
qualify a live model, browser site, microphone or actual Windows application.
