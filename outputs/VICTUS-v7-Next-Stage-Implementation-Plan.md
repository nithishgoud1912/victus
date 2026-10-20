# VICTUS v7 — Next-stage implementation plan

Prepared: 20 October 2026.
Repository: `nithishgoud1912/victus`.
Inspected branch/revision: `main` / `10226a45c3b791fa9a7439ce519db24aa9f89100`.
Theme: **Dependable execution and qualified local workflows**.
Companions: [Checklist](VICTUS-v7-Build-and-Verification-Checklist.md) · [Full Markdown audit and cross-version roadmap](VICTUS-v7-v8-v9-Markdown-Audit-and-Roadmap.md).

Execution follow-up: [V7 progress](../docs/milestones/V7-progress.md) and
[V7 verification/incomplete work](../docs/V7-TESTS-AND-INCOMPLETE.md) record the
implemented portable increment, current results and still-open target gates.
The planning snapshot below retains its original inspected revision.

These are proposed implementation stages, not completed work or new validation results. Guide numbers do not change the product version. The inspected repository identifies as a `0.1.0` candidate. No application code, lockfile, generated contract, qualification record or runtime data was changed for this planning request.

**V6 reconciliation is mandatory:** the inspected `main` has merged V5 (PR #10), but no tracked V6 Markdown, V6 remote branch or matching V6 pull request was found. A separate filename search did not resolve a V6 plan. This does not establish that work in another checkout never happened. At implementation start, locate any V6 work, record its actual revision and evidence, and replace overlapping tasks with validation of that work. If unavailable, retain `V6_NOT_RECONCILED`; use the measured V5 baseline below without claiming V6 completion.

The plans split the existing unfinished work into three focused increments: V7 dependable execution, V8 measured local interpretation and reviewed speech, V9 reliability and frozen Windows release. This allocation is a planning decision based on the audit, not an already approved expansion of runtime capabilities.

## 1. What we are building next

Make the existing note, bundled fixture-research and owned Notepad workflows usable through ordinary authenticated production paths, with truthful status and exact verification. Close operational gaps before adding new automation domains.

**Entry:** Reconciled V5/V6 baseline and a recorded stage design. Browser and native work may proceed independently after foundation checks; neither may be advertised before its own admission gates pass.

**Expected end state:** Current-source notes remain usable; the exact-engine fixture and exact-profile Notepad paths each have complete target evidence, successful ordinary-bootstrap admission and real dashboard results. Historical persistence observations have a documented disposition. A portable-only increment can be handed off with Windows gates open, but it is not full V7.

## 2. What already exists and what remains open

Primary starting evidence: [V5 handoff](../docs/V5-TESTS-AND-INCOMPLETE.md), [V5 execution summary](../docs/release/v5-execution-evidence.json), [native findings](../docs/decisions/007-v4-native-ownership-findings.md) and [release procedure](../docs/release/README.md). These reports were inspected, not rerun.

| Area | Latest checked-in evidence at the inspected revision | Carry-forward decision |
| --- | --- | --- |
| Shared execution | Durable queue/events, one mutation owner, dispatcher, bounded graph, exact review, independent verification and Stop already implemented | Extend existing services; preserve authority and no-replay invariants |
| V5 backend/frontend | 911/911 backend, 23/23 frontend, lint/build/API generation recorded as passed | Historical source-bound evidence; run fresh checks after implementation |
| Real note transport | 23/23 HTTP/SSE checks and real dashboard/API smoke recorded as passed | Preserve working deterministic notes and durable clarification |
| Persistence | V5 one-time journal-completion invariant fixed; finite crash checks passed | Earlier V4 SQLite I/O, recovery-unknown and missing-ledger observations remain undiagnosed |
| Browser | Exact Playwright 1.64.0 Chromium 156.0.8078.4/revision1248 installation blocked by invalid archives; alternate Chromium 153 regression passed | Exact-engine strict campaign, promotion and positive ordinary production path still required |
| Native | Owned-child/new-tab lease and exact Save review/session tooling exist | Actual Save, >=20 repetitions, adverse cases, two physical scales and production review unqualified |
| Reasoning | Gateway/parser/graph/readiness and benchmark tooling exist | Latest attempts executed zero inference; historical 19/30 remains below 27/30 |
| Voice | Local capture/STT/review/CommandService/SAPI and session aggregation exist | 50 quiet +50 noisy real trials and witnessed physical/audio checks absent |
| Reliability/release | V5 60.420-second smoke: four tasks, one restore, no failures | New final-source two-hour gate, current frozen build and fresh-account qualification remain open |

## 3. Implementation order and dependencies

| Stage | Deliverable | Dependency / environment |
| --- | --- | --- |
| V7.0 | Reconcile V6 and freeze the implementation boundary | First; portable |
| V7.1 | Resolve demonstrated storage and recovery defects | V7.0; portable investigation plus Windows confirmation |
| V7.2 | Qualify the exact bundled browser workflow | V7.1 foundation; independent of Notepad |
| V7.3A | Obtain one independently verified Notepad Save | V7.1; actual Windows UIA required |
| V7.3B | Complete native review, campaign and admission | V7.3A success; actual Windows plus human review |
| V7.4 | Finish operator-facing status and recovery clarity | V7.2/V7.3 for positive paths; unavailable UI work can start earlier |
| V7.5 | Close V7 with source-bound evidence | All selected V7 positive and negative gates |

Design and unchecked acceptance cases belong in the proposed milestone before production edits. Existing code paths are reused unless an observed gap justifies an extension. A newly changed runtime invalidates affected earlier qualification.

## 4. V7.0 — Reconcile V6 and freeze the implementation boundary

**Dependency:** First; portable.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `scripts/capture-source-manifest.py` | Existing implementation/config/contracts/lock inventory; keep full-source and runtime identities distinct. |
| `docs/V5-TESTS-AND-INCOMPLETE.md; docs/milestones/V5-progress.md` | Retain measured V5 results and every unresolved inherited gate. |
| `docs/supported-workflows.md; README.md; dashboard/README.md` | Reconcile current capability navigation ahead of historical sections. |
| `Proposed docs/milestones/V7-progress.md; docs/V7-TESTS-AND-INCOMPLETE.md` | Record design, actual V6 findings, commands, outcomes and unfinished work. |

**Key logic:**

1. Inspect current branches, commits, working tree and any recovered V6 artifacts. Match claims to actual code and evidence; do not synthesize a V6 milestone from chat history.
2. Capture a fresh manifest before edits. Record OS, Python, Node, SQLite, Playwright descriptor, actual engine/profile and normal resource state without opening devices.
3. Build one carry-forward table with status, evidence revision, dependency, responsible file and next action for every open V4/V5/V6 gate.
4. Classify scope by workflow. Retain no qualification promoted as the last V5 fact unless newer matching evidence proves otherwise.

**Acceptance / exit:**

- Every inherited gate has an explicit disposition and evidence reference.
- No previously implemented intake, promotion, readiness or voice-session subsystem is recreated.

## 5. V7.1 — Resolve demonstrated storage and recovery defects

**Dependency:** V7.0; portable investigation plus Windows confirmation.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `backend/victus/storage/checkpoints.py; storage/database.py; storage/action_ledger.py` | Claim/completion invariants, DB/WAL/SHM lifetime and durable action receipts. |
| `backend/victus/agent/graph.py; recovery/reconcile.py; runtime/storage_diagnostics.py` | Crash ordering, bounded diagnostics and read-only uncertain-effect recovery. |
| `backend/tests/test_v5_storage.py; test_agent_graph.py; test_agent_budgets_progress.py; test_notepad_workflow.py` | Existing focused regressions and the three inherited failure observations. |

**Key logic:**

1. Preserve V4 failure descriptions and any available failed roots. A clean new clone does not reconstruct private XML, databases or logs from their hashes.
2. Declare a finite reproduction schedule using fresh roots, isolated and surrounding-suite order, and two filesystem types where available. Record all outcomes, SQLite codes, free space/inodes and connection ownership.
3. Trace process/thread open, commit, close and teardown alongside journal claim/completion and ledger transitions. Distinguish environment I/O from a demonstrated application ordering error.
4. Reuse V5 atomic completion and storage-check. Fix only demonstrated defects; preserve unknown status, FULL durability and the one durable winner on concurrent completion.
5. If unreproduced, record unresolved investigation explicitly. Obtain supported Windows crash/recovery evidence and a reviewed disposition before calling the full stage closed.

**Acceptance / exit:**

- Crash-after-effect and crash-after-journal resume without an extra effect.
- Missing/duplicate/concurrent completion and serialization rollback remain correct.
- Focused then final serial regression passes; unresolved historical mechanisms remain visible.

## 6. V7.2 — Qualify the exact bundled browser workflow

**Dependency:** V7.1 foundation; independent of Notepad.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `backend/victus/adapters/playwright/installation.py; network.py; session.py` | Canonical engine discovery, mediated requests and owned sessions. |
| `backend/victus/workflows/fixture_qualification.py; fixture_research.py; qualification_records.py` | Strict campaign reports, engine/source/artifact/ledger binding and local promotion. |
| `backend/tests/live/v5_production_research.py; runtime/owned_processes.py; bootstrap.py` | Ordinary production admission and actual descendant/cleanup boundaries. |

**Key logic:**

1. Prepare the engine selected by the installed lock and descriptor. The V5 pin is a historical comparison, not permission to force it after a deliberate dependency change. An archive failure stays blocked.
2. Run one strict smoke, then >=20 unique-destination repetitions on unchanged source/engine. Use qualify-fixture, not the generic browser repetition report.
3. Prove structured and text routes, promised distinct final sources, redirect-alias deduplication, exact report bytes and matching verified ledger receipts.
4. Exercise scope redirects/popups/transfers, stale/ambiguous targets, startup failure, deadlines, worker interruption, destination conflict and Stop. Keep failed/partial reports and cleanup outcomes.
5. On Windows observe exact executable/creation/ancestry identities alongside an unrelated browser. The monitor must never terminate unrelated processes.
6. Promote only matching complete evidence, restart ordinary bootstrap and run the positive HTTP/SSE probe and dashboard flow. Also retain the separate unavailable-mode negative probe.

**Acceptance / exit:**

- Matching exact engine and strict >=20-run report are accepted without injected capability sets.
- Production structured/text/replay/refresh/result/Stop work under normal guards.
- Changed runtime/engine/fixture/artifact/receipt evidence refuses admission; public URLs remain unavailable.

## 7. V7.3A — Obtain one independently verified Notepad Save

**Dependency:** V7.1; actual Windows UIA required.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `backend/victus/adapters/uia/applications.py; native.py; selectors.py; actions.py` | Pinned process/window/new-tab lease and unique owner-local controls. |
| `backend/victus/workflows/create_notepad_checklist.py; native_review.py` | Exact Save approval, revalidation and independent file/UI verification. |
| `config/applications/notepad-win11-11.2607.14.0.json; docs/decisions/007-v4-native-ownership-findings.md` | Existing candidate and actual Save findings; inspect installed drift before reuse. |

**Key logic:**

1. Compare the installed executable/profile with the candidate. Capture bounded phase and identity diagnostics for a fresh supervised run, preserving earlier unknown outcomes.
2. Prove the owned child, original main window, exactly one new selected tab and all old tabs preserved. Independently recheck the editor is empty immediately before text entry.
3. Observe actual menu/dialog/filename-host/Save/main-window transitions. Diagnose unique-window reacquisition and missing artifact separately; do not guess a selector or widen a timeout from an old error.
4. Make only the observed fix; keep handles in the worker, Value/Invoke before any explicitly allowed key input and current foreground checks where applicable.
5. Revalidate exact tab, editor contents, destination, permit expiry/single use and Stop after review and immediately before Save.
6. Verify exact file bytes, encoding/newlines and actionable native UI with no unresolved modal. On uncertainty quiesce and reconcile read-only; preserve user documents.

**Acceptance / exit:**

- One complete supervised Save succeeds with the expected ledger, bytes and native postconditions.
- A failed/unknown first run stops the campaign and does not trigger another Save.
- No restored document is erased, selected for mutation or closed to make the test pass.

## 8. V7.3B — Complete native review, campaign and admission

**Dependency:** V7.3A success; actual Windows plus human review.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `backend/victus/workflows/native_qualification.py; qualification.py; qualification_records.py` | Reuse prepare/repetition/assembly/promotion rather than add another authority path. |
| `backend/victus/api/routes/workflows.py; tasks/service.py; bootstrap.py` | Intersection of native and review qualification at every admission route. |
| `backend/tests/test_native_http_review.py; dashboard/src/features/approvals/ApprovalPanel.tsx` | Existing exact-action review contracts and real installed-adapter UI path. |

**Key logic:**

1. Run >=20 successful unique native saves with unchanged source/profile/executable. Stop on the first failure and retain all attempted cases.
2. Complete real multiwindow, restored/nonempty, stale/foreign/replaced-tab, missing/ambiguous-control, deny/expiry/reuse, changed text/path/tab, conflict, Stop and restart cases.
3. Use two actual physical Windows display scales and record measured window DPI. Browser device-pixel emulation is separate evidence.
4. Exercise installed-adapter HTTP and dashboard review under one retained mutation owner. Refresh/disconnect/repeated approval cannot mint authority or create an extra effect.
5. Assemble retained runs and witnessed observations; reject incomplete or identity-mismatched evidence. Promote and restart before an ordinary new production request.

**Acceptance / exit:**

- Both native and exact-review qualification are complete and matching.
- Structured and text checklist paths produce exactly the reviewed artifact after ordinary restart.
- The generic task route cannot bypass the same qualification gate.

## 9. V7.4 — Finish operator-facing status and recovery clarity

**Dependency:** V7.2/V7.3 for positive paths; unavailable UI work can start earlier.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `backend/victus/api/routes/workflows.py; tasks/commands.py; api/routes/events.py` | Server-owned availability, saved clarification and read-only replay. |
| `dashboard/src/features/commands/ChecklistForm.tsx; TextCommandForm.tsx; features/health/HealthPanel.tsx` | Usable existing forms and precise unavailable/resource messages. |
| `dashboard/src/features/tasks/TaskResult.tsx; TaskTimeline.tsx; features/approvals/ApprovalPanel.tsx` | Evidence-backed final state and current exact preview; Stop remains reachable. |

**Key logic:**

1. Use actual server capability state to distinguish missing prerequisite, unqualified capability, low resources, waiting review and unknown effect.
2. Keep one request/body on an uncertain transport retry. Read-only refresh and SSE reconnect restore state without submission or approval.
3. Show verified result/source references and bounded safe error reasons. Unknown outcomes explain the next read-only inspection step without a retry button that repeats effects.
4. Check literal hostile text, keyboard-only review/deny/Stop, mobile overflow and authentication/logout. Regenerate API types from final backend changes rather than hand-edit generated files.

**Acceptance / exit:**

- Actual note, admitted fixture and admitted checklist flows agree between API, events and dashboard.
- Unavailable and uncertain flows are understandable without exposing private diagnostics.
- No page load, reconnect or repeated click creates a second mutation.

## 10. V7.5 — Close V7 with source-bound evidence

**Dependency:** All selected V7 positive and negative gates.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `backend/tests/live/v3_baseline.py; m5_dashboard_smoke.py; v5_production_research.py` | Real isolated transport/UI checks alongside focused adapter cases. |
| `Proposed docs/release/v7-execution-evidence.json; docs/V7-TESTS-AND-INCOMPLETE.md` | Sanitized actual counts, source/runtime identities, blockers and target boundaries. |

**Key logic:**

1. Freeze final contracts/locks and inventory, run appropriate focused and serial full backend/frontend checks, then affected real HTTP/dashboard paths.
2. Compare pre/post identities and invalidate any qualification affected by runtime/profile/engine drift. Retain raw backing reports privately and export safe summaries.
3. Publish per-workflow status and carry reasoning/voice/soak/package obligations into V8/V9. Record every unresolved defect rather than marking the earlier guides complete.

**Acceptance / exit:**

- V7 checklist is supported by actual matching evidence for each selected workflow.
- Portable-only completion is explicitly partial; no frozen-package or broad desktop claim is inferred.

## 11. Verification entry points

All commands below are planned follow-ups from the repository root, not checks executed while writing this plan. Use a fresh output name/root on every attempt. Keep existing locks and the pinned project toolchain. On Linux use `backend/.venv/bin/python` and `backend/.venv/bin/victus`; Windows uses `Scripts`. Windows native/audio/package work still requires its target environment.

Existing verification entry points: `scripts/capture-source-manifest.py`, `victus.exe`. Use current help and isolated test outputs; private machine configuration is omitted from this public guide.


Restart ordinarily after promotion. Run the positive probe using the same absolute qualification directory used by promotion; set `VICTUS_QUALIFICATION_DIR` consistently before promotion/startup. Its `--expect-unavailable` mode is a separate negative check.

Existing verification entry points: `backend/tests/live/v5_production_research.py`, `victus.exe`. Use current help and isolated test outputs; private machine configuration is omitted from this public guide.


Use that profile only after the installed identity matches. After one complete success, use a new run root beneath that session’s `runs/` directory and `--repetitions 20`. Add actual run/case/DPI evidence to the prepared session, then use `assemble-native --source SESSION/session.json --output SESSION/assembled-new.json` and `promote-native --source NEW_REPORT.json`. Inspect current help/schema for session paths; never mark an unobserved case passed.

Final implementation regression uses the existing environment:

Use the existing locked command-line tools with fresh, isolated test outputs. Inspect their current help before execution.


Run relevant focused checks while implementing and the required final regression once final code stabilizes. Documentation-only planning needs link/coverage/diff checks, not application test campaigns.

## 12. Invariants and evidence contract

1. Keep `Dispatcher.dispatch_step` as the effect path. Graph nodes call domain services; adapters retain their own loop/thread/COM ownership.
2. Keep one active task, the existing bounded queue and one mutation owner. Failed cleanup retains ownership and latches Stop.
3. Preserve server-created identities, exact scoped permits, single use, expiry and target/content/path binding. A model, transcript or client cannot grant authority.
4. Preserve durable intent/receipt ordering, FULL SQLite durability, persistent budgets and read-only recovery. A possibly applied effect remains unknown until independently reconciled; never replay it automatically.
5. Keep actual production RAM/disk safeguards, exact locks/contracts and local-only model behavior. Missing assets or resource pressure never triggers cloud fallback.
6. Keep implementation, availability, deterministic proof, laptop proof and frozen-package proof separate. Historical counts and negative-admission passes are not positive workflow qualification.
7. Keep raw audio, transcripts, native trees, tokens, credentials, browser profiles and private runtime logs outside exported evidence.
8. Run portable checks during implementation. Mark only truly Windows-dependent work as Windows-skipped; missing model/engine/corpus and unfinished duration/manual work have separate statuses.

For each stage record the problem/design, source/runtime identity, exact changed files, environment, fresh root, commands, all outcomes, backing artifact/report hashes, cleanup and remaining requirements. Operator pairing/witness statements remain trusted human observations; hashes do not authenticate the witness.

## 13. First implementation handoff and definition of done

Start with V7.0 and V7.1: recover the actual V6 state, capture the current inventory, then investigate retained storage observations with a finite schedule.

Create the stage record before code edits. Deliver a reviewable implementation increment, actual checks and `docs/V7-TESTS-AND-INCOMPLETE.md`; no new PR or deployment is created by this planning request.

**Full V7 completion:** Current-source notes remain usable; the exact-engine fixture and exact-profile Notepad paths each have complete target evidence, successful ordinary-bootstrap admission and real dashboard results. Historical persistence observations have a documented disposition. A portable-only increment can be handed off with Windows gates open, but it is not full V7.

Public-web expansion, extra applications, arbitrary MCP/cloud, custom wake, additional languages, installer/autostart and public distribution remain separately selected proposals. Completion of this document does not complete or waive any implementation or qualification gate.
