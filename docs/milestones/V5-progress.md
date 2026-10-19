# V5 implementation progress

Design recorded 19 October 2026 before V5 production edits.
Base: `20ef56946d8b253cc12ed02e6ca5002508671ef4` (main, including PR #8 conflict resolution and PR #9 handoff).
Branch: `codex/v5-implementation`. The existing V5 plan/checklist remain the implementation guide; inherited V4 gates stay open until measured.

## V5.0 — Starting inventory and scope

Starting source inventory: `.local/v50-start-01/source.json`, 302 files,
SHA-256 `46e446ace57deb0f8fb38396982f1f1951b5e2b2fc125949cbdecfdffe63a03e`.
No personal runtime was selected. Windows-only native/audio/package qualification is unavailable on this Linux host. Local model and exact browser prerequisites will be probed rather than presumed available.

## V5.1 — Storage investigation and durable journal invariants

Retain the V4 SQLite I/O, journal-crash unknown and missing-ledger observations. A passing isolated run does not explain them. First run the focused unchanged-source suite and a finite fresh-root workload; record filesystem and SQLite identities and every failure. Compare an actual different filesystem where available.

Code inspection finds `CheckpointStore.complete` silently accepts a missing claim and overwrites an already completed result. This is a separate demonstrated journal invariant gap, not a diagnosis of V4's I/O errors. Enforce one completion of an existing claimed node with a conditional atomic update; preserve FULL durability and raise on missing/already completed claims. Add meaningful missing/duplicate/concurrent completion and rollback tests. Do not retry a possibly applied effect.

Add a portable, explicit storage diagnostic runner that writes only to a new isolated directory, uses a finite repetition count, captures SQLite/OS error codes without payloads and checks committed rows and hard-exit recovery. It must retain partial results after failure, never touch a selected user runtime and never count diagnostics as full app qualification.

## V5.2 — Browser prerequisites and production admission

Attempt the exact locked Playwright engine. Reuse strict fixture qualification and promotion; do not promote generic browser repetitions. Inspect the normal production-bootstrap configuration and add/run a real authenticated HTTP/SSE production-admission probe with no injected capability sets when matching complete evidence exists. Evidence/runtime/engine changes invalidate admission. Keep Windows descendant observation separate.

## V5.3–V5.6 — Remaining boundaries

Reuse existing native session, strict voice aggregation, local benchmark and frozen package workflows. Perform meaningful portable checks; document missing installed model, corpus, actual Windows Save/DPI/audio/frozen/account sessions and full-duration qualification explicitly. No simulated physical pass, automatic approval, source-to-frozen digest relabel or resource-guard relaxation is allowed. Record actual outcomes and implementation gaps below after execution.

### Browser portability finding before edits

`qualified_browser()` currently requires a Windows `.exe` and `%LOCALAPPDATA%` even in source mode on Linux. This prevents ordinary portable bootstrap from consuming otherwise matching Linux engine evidence. Add a narrow Windows/Linux exact-installed-Chromium resolver using the locked Playwright package's browser descriptor and documented cache environment. Require the canonical installed revision/layout plus record hash, rather than accepting caller-provided browser paths. Missing/changed/linked engines stay unavailable. Do not download, launch a browser or promote a record during discovery. Test Windows/Linux/cache override and stale/malformed boundaries. Add a separate real-socket production research probe that retains blocked reports when matching qualification is absent.

## Measured portable implementation outcomes

The unchanged-source focused baseline passed 86/86 tests. A finite 12-case graph
crash/resume campaign passed on overlay and tmpfs; it did not reproduce or explain
V4's intermittent failures. No journal/ledger timing assumption was weakened.

The separate journal completion invariant is fixed with one conditional UPDATE:
only an existing incomplete claim can complete once. Missing and duplicate
completion fail; concurrent completers have one durable winner. Failed
serialization leaves the claim incomplete for safe recovery. Focused post-change
storage/budget/graph/Notepad validation passed 96/96.

Exact-installed Chromium discovery now supports Windows/Linux cache layouts while
retaining canonical revision/path/hash and report identity checks. Browser-focused
regression passed 72/72. Discovery agrees with the actual Playwright executable
layout on this Linux installation. The exact engine archive again failed to install;
no alternate engine was relabelled or qualification promoted.

The real ordinary-bootstrap production probe passed four negative admission checks
against an empty qualification directory. A positive attempt retained a blocked
report before admitting work. The probe's admitted research branch remains to be
executed with complete exact-engine qualification, separately from its negative
pass. No injected capability sets were used.

Final backend regression passed 911/911 tests, 0 failures/errors/skips, in 97.81
seconds. Frontend 23/23, lint, API generation and TypeScript/Vite build passed on
Node 24.22.0. Dependency locks/generated contracts remained unchanged. Real API,
alternate-browser and short reliability outcomes are retained in the final summary.

The final source manifest before/after portable regression is 307 files,
SHA-256 `c2c51729369b8c5fc47cbba8c8476a1258d3b2e169566d89763fb784ac59563c`.
Runtime identity: `6f02bb172093b68363f1f281ffbcfb03a91b160d5666f43e6be43043d8441c5d`.
Native Save/DPI/review, real corpus/physical audio, local model pin/benchmark,
complete production browser admission, full two-hour reliability and new Windows
frozen/fresh-account release qualification remain open. Full V5 is not declared
complete. See the V5 handoff and sanitized execution summary for exact boundaries.
