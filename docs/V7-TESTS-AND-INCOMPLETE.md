# V7 implementation — completion status and remaining work

Branch: `codex/v7-implementation`.
Base: `10226a45c3b791fa9a7439ce519db24aa9f89100`.
Guide: [V7 plan](../outputs/VICTUS-v7-Next-Stage-Implementation-Plan.md).
Evidence: [Public aggregate summary](release/v7-execution-evidence.json).

## Completion status

The portable V7 implementation is implemented and verified. Full V7 remains
incomplete until its target-specific browser and Windows native gates pass.
Publishing this implementation does not qualify those capabilities. The remaining
work continues within V7; another implementation-plan version is unnecessary.

## Implemented changes

| Repository area | Result |
| --- | --- |
| `backend/victus/storage/checkpoints.py` | Checkpoint SQL and commit run as one owned-thread transaction. Synchronous journal writes cannot prevent the checkpoint commit from being scheduled. Cancellation waits for the writer, batches roll back on failure, and FULL durability/protected JSON/no-effect-replay remain. |
| `backend/victus/workflows/native_qualification.py` | Missing, malformed or changed run/case/DPI evidence yields a retained incomplete aggregate. Partial evidence cannot promote. Actual UIA ownership and Save behavior remain unchanged pending target observations. |
| `backend/victus/api/routes/workflows.py` | Read-only current memory/disk checks and a closed resource-reason field; pressure remains separate from qualification. |
| `dashboard/src/features/commands/ResearchForm.tsx` | Structured bundled-source research with server-owned source IDs, bounded destination, duplicate-click protection and exact uncertain-request replay. |
| `dashboard/src/features/health/HealthPanel.tsx` | Actual capability/model readiness, with model availability distinguished from inference quality. |
| `dashboard/src/features/tasks/TaskResult.tsx` | Unknown effects direct the operator to read-only inspection without an action-retry control. |
| Loopback test clients and generated contracts | Explicit proxy-independent local transport; API types regenerated from the backend. |

## Verification

| Check | Result |
| --- | --- |
| Final backend regression | **931/931 passed**, no failures/errors/skips |
| Frontend tests | **23/23 passed** |
| Frontend lint, API generation and build | Passed |
| Real authenticated HTTP/SSE baseline | **23/23 passed** |
| Real dashboard/API note/authentication/replay/reload checks | Passed |
| V7 / native-review / command UI contracts | **10 / 11 / 9 passed**; simulated HTTP boundaries |
| Browser adverse/isolation fixtures | **10/10 passed** with an explicitly alternate engine |
| Checkpoint contention, cancellation and batch rollback | **3/3 passed** |
| Focused post-fix storage/graph/approval/queue checks | **87/87 passed** |
| Negative production research admission | **4/4 passed**; no work admitted |
| Positive production research admission | Blocked by missing matching qualification |

The initial full regression exposed a checkpoint/journal lock cycle and a
loopback-proxy setup error. Both have concrete fixes and passing regressions.
Historical V4 I/O, recovery-unknown and missing-ledger observations remain
undiagnosed; the new lock-cycle fix does not establish their historical causes.
Detailed environment measurements, diagnostic paths and per-case artifacts are
kept private. This document publishes implementation facts and aggregate results.

## Why full V7 is pending

The outstanding gates require the actual supported target and exact prerequisites.
Tests with simulated native adapters or an alternate browser cannot substitute for
installed Windows Notepad, physical display scales, Windows process observation,
or the locked browser engine. No qualification record was promoted and no new
backend automation capability was enabled by this increment.

| Stage | Remaining requirement | Next action |
| --- | --- | --- |
| V7.0 | V6 work not present in the inspected repository | Reconcile an external V6 artifact if one exists; retain `V6_NOT_RECONCILED` meanwhile |
| V7.1 | Supported Windows crash/recovery confirmation and historical failure disposition | Run the existing graph/storage/approval cases on the supported target; investigate reproduced failures |
| V7.2 | Exact locked browser engine and strict campaign | Prepare the required engine; one strict smoke, then at least 20 unique-destination runs on unchanged source |
| V7.2 | Windows descendant observation and cleanup | Prove exact creation/executable identities and preserve unrelated browsers |
| V7.2 / V7.4 | Positive ordinary research API/dashboard flow | Promote complete matching evidence, restart normally and test structured/text/replay/result/Stop |
| V7.3A | First fully verified installed Notepad Save | Observe the actual Save transition; verify exact bytes and native postconditions before repetitions |
| V7.3B | Native repetition/adverse/review/display campaign | At least 20 successes, exact human approval, adverse/Stop/restart cases and two physical scales; assemble/promote and retest after restart |
| V7.5 | Complete target evidence | Close the above gates without weakening identity, resource, approval or no-replay checks |

## Follow-up entry points

Use the existing `storage-check`, `qualify-fixture`, `promote-fixture`,
`prepare-native`, `qualify-native`, `assemble-native` and `promote-native` commands.
Inspect current help and the V7 checklist before execution. Use isolated output
roots and the actual matching profile/engine; private paths belong in operator
configuration, not published documentation.

Do not start native repetitions after an unknown or failed first Save. Partial
assembly remains unqualified. Refresh is read-only, uncertain effects are never
automatically replayed, and changing identities invalidates affected qualification.

V8 retains local inference/benchmark and real reviewed voice/audio work. V9 retains
full-duration reliability, frozen package/account evidence and compatible rollback.
