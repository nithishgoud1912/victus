# VICTUS v9 — Next-stage implementation plan

Prepared: 20 October 2026.
Repository: `nithishgoud1912/victus`.
Inspected branch/revision: `main` / `10226a45c3b791fa9a7439ce519db24aa9f89100`.
Theme: **Reliability, frozen Windows candidate and release decision**.
Companions: [Checklist](VICTUS-v9-Build-and-Verification-Checklist.md) · [Full Markdown audit and cross-version roadmap](VICTUS-v7-v8-v9-Markdown-Audit-and-Roadmap.md).

These are proposed implementation stages, not completed work or new validation results. Guide numbers do not change the product version. The inspected repository identifies as a `0.1.0` candidate. No application code, lockfile, generated contract, qualification record or runtime data was changed for this planning request.

**V6 reconciliation is mandatory:** the inspected `main` has merged V5 (PR #10), but no tracked V6 Markdown, V6 remote branch or matching V6 pull request was found. A separate filename search did not resolve a V6 plan. This does not establish that work in another checkout never happened. At implementation start, locate any V6 work, record its actual revision and evidence, and replace overlapping tasks with validation of that work. If unavailable, retain `V6_NOT_RECONCILED`; use the measured V5 baseline below without claiming V6 completion.

The plans split the existing unfinished work into three focused increments: V7 dependable execution, V8 measured local interpretation and reviewed speech, V9 reliability and frozen Windows release. This allocation is a planning decision based on the audit, not an already approved expansion of runtime capabilities.

## 1. What we are building next

Produce a reproducible Windows folder candidate whose advertised workflows are backed by matching runtime, package, account and recovery evidence. Establish a truthful release decision after final-source reliability.

**Entry:** V7/V8 selected capability evidence and reconciled V6 state. Packaging scaffolding can be inspected earlier; final qualification requires frozen identities. A narrower candidate must be explicitly documented, preserving all omitted obligations.

**Expected end state:** Final-source stability gates, immutable Windows package, frozen-bound capability checks, fresh standard-account test and compatible backup/migration/rollback evidence are complete for the declared scope. A missing formally versioned prior release remains a named open gate, not a fabricated pass.

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
| V9.0 | Freeze release scope and required evidence | V7/V8 handoffs; portable preparation |
| V9.1 | Run final regression and full-duration reliability | Frozen final implementation/config/contracts/locks |
| V9.2 | Build and verify the immutable Windows folder candidate | V9.0; build final source after V9.1 identity freeze |
| V9.3 | Qualify capabilities using the actual candidate | V9.2 exact bundle plus advertised workflow prerequisites |
| V9.4 | Prove fresh standard-account deployment | V9.2/V9.3; actual fresh Windows account or dedicated machine |
| V9.5 | Rehearse actual-artifact migration and rollback | Retained compatible prior bundle plus exact candidate |
| V9.6 | Publish evidence and record the release decision | All mandatory selected gates; no unresolved hidden failure |

Design and unchecked acceptance cases belong in the proposed milestone before production edits. Existing code paths are reused unless an observed gap justifies an extension. A newly changed runtime invalidates affected earlier qualification.

## 4. V9.0 — Freeze release scope and required evidence

**Dependency:** V7/V8 handoffs; portable preparation.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `docs/supported-workflows.md; docs/release/README.md` | Declare advertised source/frozen capability scope and release procedure. |
| `backend/victus/runtime/release.py; backend/pyproject.toml; packaging/windows/` | Inspect actual version/resource owners before deliberate product-version changes. |
| `Proposed docs/milestones/V9-progress.md; docs/V9-TESTS-AND-INCOMPLETE.md` | Release checklist, mandatory gate matrix and remaining obligations. |

**Key logic:**

1. Choose the exact candidate scope based on measured V7/V8 status. A typed-note-only candidate can be separately proposed, but it does not close native/model/speech requirements.
2. Record source commit, dirty files, lock/config/contracts inventory and selected target OS/profile/engine/model/STT prerequisites.
3. Keep guide V9 separate from executable product version. If a version is deliberately changed, update all actual metadata/resource owners consistently and recapture identity.
4. Classify every required gate as passed/current, failed, blocked-prerequisite, Windows-pending, human-pending, duration-pending or not-advertised with retained debt.

**Acceptance / exit:**

- An unambiguous mandatory gate matrix and advertised capability list exist before final campaigns.
- No optional integration or omitted capability is implicitly qualified.

## 5. V9.1 — Run final regression and full-duration reliability

**Dependency:** Frozen final implementation/config/contracts/locks.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `backend/tests/live/m7_soak.py; evaluation/reliability/README.md` | Existing core reliability harness and original thresholds. |
| `backend/victus/runtime/owned_processes.py; supervisor.py; resources.py` | Owned process cleanup, resource telemetry and failure retention. |
| `Proposed backend/tests/live/v9_workflow_soak.py, only if existing harness lacks needed coverage` | Supplemental admitted-workflow workload; separate report, no replacement of the core gate. |

**Key logic:**

1. Run relevant focused checks and final serial full backend/frontend/lint/build/API-generation on the final code. Preserve earlier evidence rather than carrying old counts as new.
2. Capture pre/post manifests and run >=7,200 real wall-clock seconds, >=100 verified tasks, >=2 checksum-verified backup/restores, zero recorded failures, warmed-parent RSS growth <=20% and health p95 <0.5 seconds.
3. Keep actual RAM/disk safeguards. Pressure rejections are reported distinctly from accepted-task failures; blocked preflight or an incomplete progress file is not a completed soak.
4. Inspect owned worker/browser processes in addition to the core parent RSS metric. Report measurement scope and orphan/cleanup findings explicitly.
5. Where browser/native/command paths are advertised, run a supplemental declared workload with their actual adapters. Keep deliberate native review manual; do not auto-approve to accelerate a soak.
6. If source changes, retain the attempt as historical and rerun affected qualification on the new final identity. An old M7 two-hour pass does not qualify V9 bytes.

**Acceptance / exit:**

- Final report, unchanged source and all original core stability thresholds pass.
- Every advertised additional workflow has separate current workload and cleanup evidence.

## 6. V9.2 — Build and verify the immutable Windows folder candidate

**Dependency:** V9.0; build final source after V9.1 identity freeze.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `scripts/build-windows.ps1; packaging/windows/; backend/victus/__main__.py` | Existing onedir resources, frozen entry and multiprocessing setup. |
| `scripts/package-self-test.ps1; backend/victus/runtime/paths.py; runtime/release.py` | Actual executable entry, immutable resources, user-data separation and self-test. |

**Key logic:**

1. Build into fresh output/work directories with the selected source manifest. Preserve previous bundles; do not overwrite an active application folder.
2. Keep executable, _internal resources and release manifest together. Bundle no API tokens, sessions, prompts, models, recordings or personal data.
3. Run the actual frozen self-test with normal policy: authentication, note worker/readback, lock, Stop, dependency messages, backup/migrate/restore and restart.
4. Check source_sha256 and bundle_manifest_sha256 in new self-test evidence and independently verify all listed bundle bytes.
5. Observe graceful shutdown separately from bounded owned-process cleanup; a harness Kill fallback cannot establish that the server exited gracefully.

**Acceptance / exit:**

- The tested bundle exactly matches its manifest/source record and preserves separate account-owned runtime data.
- Fresh frozen self-tests pass; package presence alone enables no hardware-dependent capability.

## 7. V9.3 — Qualify capabilities using the actual candidate

**Dependency:** V9.2 exact bundle plus advertised workflow prerequisites.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `backend/victus/workflows/qualification_records.py; runtime_identity; qualification_path` | Frozen manifest integrity and external runtime/account-specific qualification records. |
| `backend/victus/cli.py; workflows/fixture_qualification.py; native_qualification.py` | Run candidate-owned prepare/qualify/assemble/promote entry points. |
| `backend/tests/live/v5_production_research.py; existing native/voice/model live runners` | Inspect harness compatibility; extend target selection only if needed, without injecting capability sets. |

**Key logic:**

1. Use Victus.exe qualification commands for advertised browser/native scope. Never copy or relabel a source qualification digest as frozen evidence.
2. Store frozen records under the existing account-owned qualifications/<runtime identity> location or explicit absolute qualification root. Do not modify immutable bundle resources to promote.
3. For each advertised capability retain actual candidate-bound adapter/asset identities, backing artifacts and verified ledger records; repeat physical/device gates where candidate changes affect their boundary.
4. Restart the ordinary frozen service and test authenticated HTTP/SSE/dashboard admitted paths, exact Save review where enabled, replay, refresh and Stop.
5. In isolated negative copies alter bundle/profile/engine or evidence and confirm refusal. Preserve the actual tested candidate unmodified.

**Acceptance / exit:**

- Advertised frozen capabilities work after ordinary restart using matching external records.
- Changed/missing qualification or bundle bytes leave the relevant capability unavailable.
- No source-test-only override or injected registry supplies production admission.

## 8. V9.4 — Prove fresh standard-account deployment

**Dependency:** V9.2/V9.3; actual fresh Windows account or dedicated machine.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `docs/release/README.md; scripts/package-self-test.ps1` | Existing deployment procedure and actual bundle self-test. |
| `backend/victus/adapters/credentials.py; storage/payloads.py; runtime/instance_lock.py` | Account-scoped secrets/protected payloads, writable data and single ownership. |

**Key logic:**

1. Copy the complete candidate and test script into a fresh standard account or dedicated machine with no repository/Python/Node environment on PATH.
2. Run without elevation, use a fresh writable data root and verify default loopback/authentication, immutable app files, locks and explicit prerequisite messages.
3. Configure only intentionally provided model/browser/STT assets and rerun the advertised capability checks. No first-launch download, autostart or microphone activation is implied.
4. Test intended account-owned protected data. DPAPI content from the developer account is not assumed portable and must fail safely where account binding prevents access.
5. Record OS/build, executable version, bundle/runtime identity and sanitized outcome. An unelevated developer/admin-account session does not replace this gate.

**Acceptance / exit:**

- Fresh standard-account self-test and advertised-scope checks pass without developer PATH or elevation.
- Missing assets and foreign-account protected payloads fail safely with no mutation replay.

## 9. V9.5 — Rehearse actual-artifact migration and rollback

**Dependency:** Retained compatible prior bundle plus exact candidate.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `scripts/package-upgrade-rollback.ps1; runtime/maintenance.py; storage/migrations.py; storage/backups.py` | Inspect existing owners, offline locks, transactional migration and checksum-verified backup/restore. |
| `docs/release/README.md; runtime/release.py` | Prior/candidate identity and schema/version distinction. |

**Key logic:**

1. Run the old executable on isolated old-version data and produce its own verified offline backup after all owners stop.
2. Use the candidate to migrate a compatible restored copy and create a new verified result. Reject newer schema and held instance locks; preserve transactional migration semantics.
3. Stop the candidate, use the old executable to restore its backup into a new root and verify old operation. Preserve the candidate data for diagnosis.
4. Invalidate old approvals/intakes and prevent automatic replay of interrupted effects. Never downgrade an active database or overwrite the only backup.
5. Report actual binary/hash/schema identities separately from formal released-version identities. The historical schema-7-to-8 pair used product 0.1.0 on both sides; it is not formal cross-version release proof.

**Acceptance / exit:**

- Both actual executables complete verified backup/migration/new-output/rollback on isolated roots.
- A formal cross-version pass requires genuinely distinct retained release versions; absent prior release remains explicitly pending.

## 10. V9.6 — Publish evidence and record the release decision

**Dependency:** All mandatory selected gates; no unresolved hidden failure.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `Proposed docs/release/v9-release-status.json; docs/V9-TESTS-AND-INCOMPLETE.md` | Machine-readable current gate outcomes, retained debt and explicit release_qualified decision. |
| `docs/supported-workflows.md; README.md; dashboard/README.md; docs/release/README.md` | Consistent support matrix, setup, prerequisites and recovery guidance. |

**Key logic:**

1. Create the final evidence summary from actual reports, with per-capability source/runtime/bundle/asset identities and hashes. Missing private backing files are unavailable, not reconstructed from hashes.
2. Check exports for private host/account paths, tokens, audio/transcripts, browser profiles, prompt content and service logs.
3. Record go/no-go against the predeclared mandatory matrix. Open mandatory gates keep release_qualified false; a proposed narrower scope has its own explicit decision and retained obligations.
4. Deliver the folder candidate, exact setup/self-test/rollback instructions and honest limitations. Preparing a release does not publish it or deploy it.
5. Keep signing/public distribution, installer/autostart, arbitrary applications/public-web scope, extra languages, custom wake and cloud/MCP expansion in separately selected future work.

**Acceptance / exit:**

- Every support claim maps to current evidence and every open requirement has a next action.
- No public publication, installer, always-on listening or extra automation scope is performed by this plan.

## 11. Verification entry points

All commands below are planned follow-ups from the repository root, not checks executed while writing this plan. Use a fresh output name/root on every attempt. Keep existing locks and the pinned project toolchain. On Linux use `backend/.venv/bin/python` and `backend/.venv/bin/victus`; Windows uses `Scripts`. Windows native/audio/package work still requires its target environment.

Existing verification entry points: `backend/tests/live/m7_soak.py`, `scripts/build-windows.ps1`, `scripts/capture-source-manifest.py`, `scripts/package-self-test.ps1`. Use current help and isolated test outputs; private machine configuration is omitted from this public guide.


Capture the pre-soak inventory too and compare it with the final source inventory. Use the exact bundle path returned by the build; the path above follows the current documented convention. Repeat the self-test and advertised checks on the fresh standard account. For a retained real artifact pair:

Existing verification entry points: `scripts/package-upgrade-rollback.ps1`. Use current help and isolated test outputs; private machine configuration is omitted from this public guide.


Inspect script help and actual prerequisite requirements first. A same-version artifact rehearsal, harness smoke, blocked preflight or forced cleanup does not establish a broader release gate. Candidate-owned `Victus.exe qualify-fixture`, native session commands and promotion must use the candidate's own identity and external qualification location.

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

Start with V9.0 and V9.1: freeze advertised scope and mandatory gates, then qualify final-source regression and the full-duration core workload.

Create the stage record before code edits. Deliver a reviewable implementation increment, actual checks and `docs/V9-TESTS-AND-INCOMPLETE.md`; no new PR or deployment is created by this planning request.

**Full V9 completion:** Final-source stability gates, immutable Windows package, frozen-bound capability checks, fresh standard-account test and compatible backup/migration/rollback evidence are complete for the declared scope. A missing formally versioned prior release remains a named open gate, not a fabricated pass.

Public-web expansion, extra applications, arbitrary MCP/cloud, custom wake, additional languages, installer/autostart and public distribution remain separately selected proposals. Completion of this document does not complete or waive any implementation or qualification gate.
