# M3 7D: Routing, bounded context and verified model benchmark

## Build guide

Add `agent/router.py` for explicit known commands and reviewed workflow bindings.
Deterministic steps must enter the existing graph/dispatcher, not bypass policy,
budgets, cancellation or independent verification. Unknown/ambiguous requests
fall back to a bounded planner with only the relevant, enabled tool catalog.

Add `agent/context.py` for bounded goals, recent outcomes, observations and
reviewed preferences. External page content is labelled untrusted data in a
separate message; it must never be appended to system instructions. Restrict
the output parser/schema to the selected tool catalog too.

Run fake provider sequences covering two steps, invalid arguments, unknown tools,
premature finish, repeats, budget exhaustion and cancellation. Freeze a 30-goal
suite (10 browser, 10 desktop, 10 file/mixed) before live inference. Use the exact
installed Qwen3 4B digest, real local model calls, isolated outputs and independent
verifiers. Unqualified native adapters remain blocked and count as non-successes.
Never replace them with simulated desktop results. Preserve raw per-goal outcomes
and model-call counts; report qualification separately from task scores.

## Evidence

Validated on Windows/Python 3.12 on 16 October 2026:

- Final explicit fixture regression suite: **377 passed in 147.09 seconds**.
- Includes the requested seven fake-model sequences, real persistent graph,
  deterministic routing with zero model allowance, context trust separation,
  selected schemas, short-reference restoration/rejection and benchmark verifiers.
- Live pinned-model structured-output preflight: **6/6 passed**.
- Live frozen 30-goal benchmark: **19/30 verified; M3 gate failed**.
- Changed code/tests pass Ruff lint, formatting, compilation and whitespace checks.

Fixture tests and live benchmark runs were separate. Browser benchmark actions
were performed against owned ephemeral localhost pages. No native desktop
operation, public-site submission, cloud model or paid API was used.

## Implemented behavior

- `CommandRouter` accepts an explicitly enabled tool catalog. An anchored command
  such as `Create note alpha.txt containing "Hello"`, or a structured
  `create_note`/`create_notes` request, selects typed deterministic steps. Explicit
  reviewed workflow bindings can select browser/Notepad wrappers already
  registered by the application. Missing bindings block; no stub is treated as
  a qualified native adapter. Other requests select only matching file, browser
  or desktop tool families, with a maximum of eight tools.
- Routing plans and their arguments are kept in restricted task payload storage.
  Checkpoints retain only `route_ref`. Deterministic proposals consume zero model
  requests and still pass the same action budget, authorization, dispatcher,
  action ledger, independent verifier, cancellation and recovery gates.
- `ContextBuilder` selects the same limited catalog for the model's schema and
  parser. It includes at most two bounded observations, four recent outcomes and
  eight reviewed preference records. Only current targets are actionable; older
  observations are historical data. Context has an aggregate UTF-8 byte bound;
  this is not a claim of an exact tokenizer-specific token count.
- The system instruction is static. Web/observation data appears only in the
  user-message JSON under `OBSERVATIONS_UNTRUSTED`, with explicit trust labels.
  Preferences come from the trusted reviewed-store callback, never from a goal or
  web page claiming approval. Expired/unreviewed/unsupported preferences are
  excluded and preferences do not grant permissions.
- Current adapter references are represented as `o1`, `t1`, `t2`, etc. for the
  model. A task-local parser maps those aliases back to the original observation
  and target IDs before full validation and dispatch. Unknown aliases fail.
  Original origin, target identity, process, freshness, policy and verification
  checks remain in place; aliases grant no extra capability.

Caller composition: bind `CommandRouter(parser.tools)` to `AgentServices.router`
and use `GatewayPlanner` with that same reviewed catalog. Bind
`AgentServices.preferences` to the approved preference store when available.
Legacy explicitly supplied route callbacks remain supported. This stage does
not expose an autonomous agent through the foundation HTTP API.

## Live compatibility and qualification

The local Ollama-compatible API reports version `0.33.3`. It returns raw hex model
digests, now normalized to the existing `sha256:` pin representation. It rejected
the previous sampler grammar with HTTP 400. The Ollama adapter now compiles a
structural sampler schema, omitting string regex/length annotations that this
sampler cannot compile. The complete schema remains in the planning instruction
and strict local parser; all argument bounds and policy checks run before
execution. Invalid destinations are still rejected. No output is extracted from
prose or code fences, and no cloud or replacement model is used.

Six live structured-output samples passed **6/6** with the pinned Qwen3 4B model.
This qualifies those samples, not the entire assistant:
[schema sample evidence](evidence/M3-7D-live-schema-samples.json).

## Fixed real-model benchmark

Frozen suite: `evaluation/m3-30-goals-v1.json`, SHA-256
`1a23540e729f3b62f9e0991fd7c53d6cd6e279a514f45f1e4a697949a273e340`.
Both runs used the same 30 goals and exact model pin:
`qwen3:4b`, digest
`sha256:359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.
Expected outcomes live in the benchmark harness, not in the model prompt. Model
finish claims alone cannot count. Each success requires independently observed
expected results, verified action receipts, graph evidence and a live model
response. Failures and dependency-gated cases stay in the denominator.

| Category | Verified | Qualification scope |
| --- | --- | --- |
| Browser | 10/10 | Real headless Chromium, isolated localhost form fixtures; includes two page-injection cases |
| Desktop | 0/10 | No reviewed native Notepad profile; no substitute file-writing or simulated UI success |
| File/mixed | 9/10 | Actual new files and exact byte verification, including two-step goals |
| Total | **19/30** | **27/30 M3 gate has not passed** |

The final recorded run made **36 provider requests and received 36 real model
responses**. Desktop dependencies were unavailable; the model's premature finish
claims were rejected as `GOAL_NOT_VERIFIED` rather than counted as native success.
F06, a two-file request, stopped with `STEP_VALIDATION_OR_POLICY_DENIED` and did
not verify its complete promise. The supported browser/file subset scored 19/20;
that subset is not a replacement for the 30-goal score.

The initial run verified 11/30; opaque reference copying accounted for most
browser failures. Short context aliases improved the same frozen browser goals
from 2/10 to 10/10. Both reports are preserved:

- [Initial benchmark](evidence/M3-7D-benchmark-initial.json)
- [Benchmark with short context aliases](evidence/M3-7D-benchmark.json)

The native profile/DPI gate and unsupported task remain outstanding before M3 can
claim release qualification. These localhost results do not qualify public
websites, arbitrary desktop apps, speech or general computer autonomy.

Reproduce explicitly from `backend/`, using a new output directory:

```powershell
uv run python tests/live/m3_30_goal_benchmark.py --model qwen3:4b --digest sha256:359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7 --output ../.local/m3-30-new-run
```

Exit code 2 indicates the gate did not pass. The runner persists results after
each goal and refuses to overwrite a prior run directory. The current runner
also records unexpected destinations and false-success cases explicitly before
allowing any future qualification claim.
