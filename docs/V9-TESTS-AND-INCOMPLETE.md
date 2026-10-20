# V9 implementation, release decision and Windows tests

V8 is merged in `4af156fa82d12d98d31aca08f21140d566773665` (PR #12).
V9 extends those exact V8 file contents. Product version remains **0.1.0**;
V9 is a guide milestone. **Release decision: NO-GO.** There is no newly
qualified Windows bundle or completed final-source two-hour campaign.

## Implemented

- Added `victus verify-bundle`: read-only verification of source-bound manifest,
  every listed checksum/size, unique safe paths and the exact actual file set.
  Missing/changed/unlisted files and links/reparse points are refused. The frozen
  `serve` entry verifies integrity before initializing settings or runtime data.
  This is unsigned integrity checking, not publisher authentication.
- Windows builds require `-SourceManifest`. Manifest generation verifies the
  captured source/config/contracts/locks against current bytes and complete Git
  release-input scope. Existing manifest bytes cannot be overwritten. Runtime
  databases/WAL, recordings and external model formats are excluded.
- Core soak finalization now happens after cleanup. Short runs with failures,
  aborts, unfinished admitted tasks, changed source or surviving Python children
  fail. A successful smoke has its own status and never qualifies two hours.
  Both the original Python identity and full release-input identity are retained.
- Frozen self-test and rollback scripts record forced terminations separately
  from graceful shutdown and bound parent cleanup waits. Actual descendant
  cleanup and graceful console exit remain target tests. Self-test checks exact
  bundle identity before and after execution.
- Rollback rehearsals preserve old data and migrate a separate checksum-verified
  restored copy. Both artifacts are verified by the candidate integrity command,
  and executable/manifest identities are recorded. Compatible equal-schema
  migrations are valid rehearsals; they do not prove a schema upgrade or formal
  cross-version release. Formal release qualification remains false.

## Current portable results

Final-source regression: **1,004 backend tests and 23 frontend tests passed**,
with Ruff, frontend lint, API generation and build. The real 60.418-second smoke
passed four verified tasks and one verified restore with no failures, matching
source identities and completed server/Python-worker cleanup. It does not pass
the two-hour or Windows process-tree gate.

See [machine-readable V9 status](release/v9-release-status.json) for exact totals,
source identity and safe report hashes. Tests exercise synthetic bundle bytes;
no fixture executable is presented as a Windows package run. Python regression,
frontend tests/lint/API generation/build and the real core-smoke workload are
separate from frozen-package proof. PowerShell is unavailable here, so modified
Windows scripts require target execution; no PowerShell syntax/runtime pass is
claimed.

Reproduce with the locked Python environment and Node 24.22.x:

```bash
backend/.venv/bin/python -m pytest backend/tests
backend/.venv/bin/ruff check backend packaging/windows
npm --prefix dashboard test
npm --prefix dashboard run lint
npm --prefix dashboard run build
backend/.venv/bin/python backend/tests/live/m7_soak.py --seconds 60 --require-ready --fail-fast --output <fresh-smoke-directory>
```

Retain all reports in isolated private roots. Preserve normal RAM/disk guards.
`smoke_passed` is a short-harness outcome; only `qualified` in the final report
can pass the core stability gate. A progress file, exit without a final report,
resource-blocked preflight or changed-source run does not pass it.

## Windows-only tests: NOT RUN

Run on the supported Windows x64 target using Python 3.12, the pinned Node
version and the locked packaging environment. Keep the complete bundle together
and use fresh output/data roots. No installer, public distribution, autostart,
cloud service or automatic microphone activation is introduced.

| Gate | Procedure | Required evidence |
| --- | --- | --- |
| Actual folder build | Run `scripts/capture-source-manifest.py --output-directory <fresh-source-capture>`, then `scripts/build-windows.ps1 -SourceManifest <capture>/source.json -OutputDirectory <fresh-output> -WorkDirectory <fresh-work>`. Use the documented packaging dependency preparation. | Successful actual build, source identity and complete manifest/file verification. If dashboard generation changes captured inputs, freeze the new inputs and rebuild with a new capture/output. |
| Actual executable integrity/startup | Run `Victus.exe verify-bundle`, then `Victus.exe doctor` and ordinary `serve`. In separate disposable copies change a listed byte, add an unlisted file, remove a resource or introduce a link. | Untouched candidate starts; changed copies refuse startup before data initialization. Original candidate remains untouched. Integrity does not authenticate an unsigned publisher. |
| Frozen self-test | Run `scripts/package-self-test.ps1 -Bundle <actual-folder> -OutputDirectory <fresh-output>`. Exercise real worker spawn, authentication, locks, deterministic note/command, durable clarification, replay, Stop, backup/migrate/restore/restart. | All checks pass with unchanged source/bundle identities and normal resource guards. Pressure is a block, not a pass. Logs remain private. |
| Graceful shutdown | Start the ordinary frozen service in a console, finish/stop work, then use its normal console shutdown (Ctrl+C). Separately Stop during active work. | Server, owned workers and handles exit within a bound, lock is released and restart succeeds. API Stop only halts work. Harness Kill counts are forced termination, never graceful evidence. |
| OS process cleanup | Observe exact descendant executable/creation identities through worker execution, cancellation, backup/restart and failure paths. Include browser/native workers only when admitted. | No retained owned descendants; observation errors/unavailable inventory prevent a pass. Parent exit and `multiprocessing.active_children()` alone do not prove Windows process-tree cleanup. |
| Fresh standard account | Copy complete bundle and test scripts to a genuinely fresh standard account or dedicated machine without repository/Python/Node on PATH. Run unelevated, with account-owned data and intentionally supplied assets only. | Frozen self-test and advertised paths pass; immutable bundle files stay unchanged; explicit missing-dependency messages, no hidden downloads/listening/autostart. Developer-account execution does not count. |
| DPAPI/account isolation | Create protected payloads in the intended account; test access there and safe refusal of foreign-account protected data in an isolated copy. | No leaked payload, authority restoration or automatic replay; invalid account-bound data fails safely. Do not overwrite the original account's data. |
| Actual old-artifact rollback | Retain compatible prior and candidate folders. Run `scripts/package-upgrade-rollback.ps1 -PriorBundle <prior> -CandidateBundle <candidate> -OutputDirectory <fresh-output>`. | Prior executable creates verified data/backup; candidate restores/migrates a separate copy and verifies a new result; prior executable restores its own backup to a new root and verifies old bytes. Both bundles and prior data remain intact. |
| Frozen advertised capabilities | Restart the ordinary candidate with its own external qualification records; test authenticated HTTP/SSE/dashboard, reload/replay, exact review where enabled, Stop and mismatched/missing-record refusal. | Actual candidate-owned ledger/artifact/adapter evidence. Source qualification hashes and injected capability registries cannot qualify the frozen candidate. |
| Inherited native/audio target gates | Run V7 Notepad Save/review/adverse/repetition/two-DPI checks and V8 physical microphone/SAPI/echo/shortcut checks if those capabilities are advertised. | Actual target and human-witnessed evidence bound to final candidate/assets; see linked V7/V8 registers. |

The updated PowerShell scripts still use forced parent termination for their
bounded harness cleanup. Their functional pass does not close the separate
graceful-shutdown or OS-descendant gates. A retained old bundle lacking a valid
source-bound manifest is an explicit prerequisite block for the new exact
artifact verifier; do not rewrite its manifest to invent historical evidence.

## Open gates that are not Windows-only

| Gate | Status and next action |
| --- | --- |
| Final-source two-hour reliability | **Duration-pending.** Run the current `m7_soak.py --seconds 7200 --require-ready --fail-fast --output <fresh-directory>` on a stable awake target. Require >=7,200 actual seconds, >=100 verified tasks, >=2 checksum-verified restores, zero recorded failures, warmed parent RSS growth <=20%, health p95 <0.5 s, completed cleanup and matching full source identities. A 60-second smoke cannot substitute. No two-hour run is left active by this handoff. |
| Supplemental workload | Proposed Windows candidate scope is deterministic notes/command intake. Any advertised browser/native path needs its own real workload/cleanup evidence; manual Save review must remain manual. Core note reliability cannot qualify those paths. |
| Formal prior release | **Blocked-prerequisite.** No genuinely distinct retained released-version pair was qualified. Distinct binary hashes or equal product versions can establish an artifact rehearsal only. Do not invent a version bump or prior release. |
| V8 reasoning/voice | **Blocked-prerequisite/human-pending.** No current local-model inference, real 50 quiet/50 noisy corpus or witnessed physical qualification exists. Model/corpus absence is not a Windows skip. |
| Exact browser engine | **Blocked-prerequisite.** Locked Chromium installation/strict qualification remains open. Alternate-engine fixtures do not satisfy it. |
| V6 reconciliation and V4 diagnosis | V6 remains unreconciled in the inspected history. Historical V4 I/O/unknown-effect/missing-ledger observations remain undiagnosed; later regression passes do not establish their cause. |

A narrower typed-note Windows candidate is a proposal, not an approved release.
Omitted native/browser/model/voice obligations remain recorded in
[V7](V7-TESTS-AND-INCOMPLETE.md) and [V8](V8-TESTS-AND-INCOMPLETE.md).
All mandatory target, duration and artifact gates must pass before changing the
release decision. Signing/distribution, installers, wake/MCP/cloud expansion and
additional applications/languages remain separate work.
