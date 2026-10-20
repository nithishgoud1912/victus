# VICTUS v5 — Next-stage implementation plan

Prepared: 19 October 2026, Asia/Kolkata.
Repository: `nithishgoud1912/victus`.
Inspected local revision: `8e76938a682020cbd7662a167cc62d570bbd19da`.
Equivalent published implementation: `550ee86a28095f3bfbc55e4bb0e9b5230d782b16`, PR #8.
Both revisions have tree `c90ba11ce6570eaeb48f65a18b97c2479d8d2231`.
Companions: [Build and verification checklist](VICTUS-v5-Build-and-Verification-Checklist.md) · [Baseline and carry-forward review](VICTUS-v5-Baseline-and-Carry-Forward-Review.md).

Execution follow-up: see [V5 progress](../docs/milestones/V5-progress.md) and [verification/incomplete work](../docs/V5-TESTS-AND-INCOMPLETE.md) for the portable implementation increment and still-open qualification gates. The planning snapshot below retains its original inspected revision.

This is a plan, not a claim that V5 is implemented. It follows the V3/V4 guide structure: current state, ordered stages, file responsibilities, key logic, acceptance checks and implementation handoff. V5 is a guide number; the application remains a `0.1.0 candidate` until deliberately versioned. Unfinished V4 requirements remain open under their original evidence history.

## 1. What we are building next

Make the existing local assistant dependable enough for a narrowly defined Windows release candidate:

1. Persist and recover tasks without repeating an uncertain effect or losing durable progress.
2. Create typed notes through real authenticated HTTP/dashboard paths with truthful verified outcomes.
3. Admit bundled browser research only after complete matching evidence and an ordinary production restart test.
4. Complete the owned Notepad editor and exact Save approval path on the actual laptop.
5. Measure one installed local reasoning model and reviewed English speech against declared gates.
6. Freeze and test the actual folder package, including long-duration reliability and account boundaries.

Example end result: issue a supported command → clarify missing fields → retain one request/task identity → execute through the existing dispatcher → approve the exact native Save if needed → independently verify → display a result backed by evidence. Stop or an uncertain effect never becomes an implicit retry.

The immediate implementation is **V5.0: reconcile the current baseline**, followed by **V5.1: diagnose storage and crash recovery**. Browser and native work can then advance independently behind their existing gates. No new general-purpose agent, arbitrary desktop control or public-web scope is required for this release candidate.

## 2. What already exists and what remains open

Authoritative starting references: [V4 handoff](../docs/V4-TESTS-AND-INCOMPLETE.md), [sanitized Linux evidence](../docs/release/v4-linux-validation.json), [V4 progress](../docs/milestones/V4-progress.md), [native findings](../docs/decisions/007-v4-native-ownership-findings.md) and [release procedure](../docs/release/README.md).

| Area | Existing implementation / measured evidence | V5 continuation |
| --- | --- | --- |
| Execution foundation | Shared dispatcher, durable queue/events, bounded graph, spawned supervision, approvals and Stop | Resolve persistence observations; preserve no-replay and exact authority |
| Backend | Final Linux serial run: 875/876 passed, one SQLite I/O failure; previous expanded run failed a different recovery case | Reproduce and diagnose; no uniformly green baseline yet |
| Dashboard and API | 23 frontend tests, lint/build, 23 real HTTP/SSE checks, real dashboard/API smoke and seven UI contracts passed | Revalidate changed paths; production tests for newly admitted capabilities |
| Browser | 10 adversarial cases and final 20 supervised repetitions passed using alternate Chromium 153.0.8010.0 | Exact Chromium 156/build1248 download blocked; no qualification promotion or admitted production browser proof |
| Native UIA | Owned child/new-tab lease, operation guards, tab-bound Save review, native session/assembly/promotion tooling | Actual Save remains unqualified; first success, full case campaign, DPI and production review still required |
| Evidence | Strict schema-2 loaders, artifact/receipt/source binding, frozen manifest integrity and external bundle record location | Exercise real end-to-end producers/promotion/restart; close demonstrated gaps only |
| Local reasoning | Strict gateway/parser, bounded planning, readiness inventory and benchmark runner | Latest attempts: MODEL_UNAVAILABLE, zero inference; historical 19/30 below 27/30 remains historical |
| Voice | Capture/STT/review/shared CommandService, action evaluation, protocol preparation/aggregation | Real 50 quiet + 50 noisy trials, negative conditions and witnessed device behavior absent |
| Reliability | 30.313-second Linux smoke, four tasks, one restore, no failures | Full 7,200-second qualification remains unmeasured |
| Packaging | Existing Windows folder build, self-test, actual-artifact-pair rehearsal and frozen-bound evidence design | Current-source frozen build, fresh standard account and honest release decision |

Do not rebuild V4's native promotion commands, frozen record location, readiness API, voice protocol aggregator or portable browser launcher. They already exist. Inspect and extend them only when a failing case demonstrates a gap.

## 3. Implementation order and dependencies

| Stage | Deliverable | Dependency / execution boundary |
| --- | --- | --- |
| V5.0 | Reconciled source inventory, capability matrix and test classification | First; portable |
| V5.1 | Diagnosed persistence failures and trustworthy recovery regression | V5.0; portable investigation, then Windows confirmation |
| V5.2 | Exact-engine fixture qualification and ordinary production admission | Stable foundation; independent of Notepad; Windows process checks separate |
| V5.3A | One verified owned Notepad Save | Stable foundation; actual Windows UIA |
| V5.3B | Native campaign, review and admission after restart | V5.3A plus full native/DPI gates |
| V5.4 | Pinned local reasoning and measured interpretation | Installed model; full benchmark success also needs its tool prerequisites |
| V5.5 | Real reviewed English-note speech qualification | Qualified note path, model assets and human/audio session |
| V5.6 | Final regression, full soak, frozen candidate and release decision | Selected implementation/config/contracts/locks frozen |

Write the stage design and acceptance cases into a proposed `docs/milestones/V5-progress.md` before production edits. This plan does not create a completed milestone. Capture a new inventory after any implementation change; earlier qualification becomes historical when its bound identities change.

## 4. V5.0 — Reconcile the baseline and test policy

**Inspect/extend:**

| File | Responsibility |
| --- | --- |
| `scripts/capture-source-manifest.py` | Exact implementation/config/contracts/locks inventory and dirty state |
| `docs/release/v4-linux-validation.json` | Preserve original attempts, report hashes and unresolved observations |
| `docs/V4-TESTS-AND-INCOMPLETE.md` | Inherited failures, Windows-only work and non-Windows blockers |
| `docs/supported-workflows.md` | Place a current matrix before historical per-revision sections |
| `README.md`, `dashboard/README.md` | Consistent setup and scope navigation |
| Proposed `docs/milestones/V5-progress.md` | Per-stage decisions, actual outcomes and remaining gates |

**Key logic:**

1. Record the selected branch/base, clean or dirty state, full source digest and separate runtime digest. The latest V4 final inventory covers 301 files with digest `51c78f861b808a348c861a5ff6143b9aa713f0259780a24440d3d899bbfa42a0`; it is a comparison, not a substitute for a fresh capture.
2. Preserve all prior attempts. Raw `.local` reports are private and may be absent from another clone; use checked-in hashes/counts without inventing missing raw evidence.
3. Classify every requested check: portable, Windows-only, blocked prerequisite, or pending long-duration/manual session. Run portable checks. Skip only checks that actually require Windows in a Linux session.
4. Keep final-backend failure, exact-browser download, unavailable model, missing recordings and unfinished two-hour soak as different statuses. Do not classify them all as Windows skips.
5. Keep normal 2 GiB RAM and 64 MiB mutation disk guards, dependency locks and generated contracts. Measure resource pressure; do not weaken guards.
6. Reconcile the leading capability table with the Linux results. Existing older tables retain their named historical scope rather than describing the latest state implicitly.

**Acceptance:** a new source-bound starting record and a capability/test matrix that agrees with the retained evidence. No implementation or capability is enabled by a documentation change.

## 5. V5.1 — Diagnose persistence and crash recovery first

**Inspect/extend:**

| File | Responsibility |
| --- | --- |
| `backend/victus/storage/checkpoints.py` | `CheckpointStore.connect`, `claim`, `complete`, persistent saver and ownership lock |
| `backend/victus/storage/database.py`, `action_ledger.py` | Actual connection/transaction lifecycle and action receipts; confirm exact call chain |
| `backend/victus/agent/graph.py` | Node journal ordering, resume and side-effect reconciliation |
| `backend/tests/test_agent_budgets_progress.py` | Shared action budget regression that encountered the final I/O failure |
| `backend/tests/test_agent_graph.py` | Hard process termination and recovery without repeated file writes |
| `backend/tests/test_notepad_workflow.py` | Wrong-byte verification and missing-ledger observation under fake UIA |

### Retained failures to explain

- Final serial run: `test_twelve_action_attempts_are_shared_across_plans` raised `sqlite3.OperationalError: disk I/O error` while executing `PRAGMA synchronous=FULL` in `CheckpointStore.connect` (line 119 in the inspected revision).
- Earlier expanded run: `test_hard_process_restart_never_repeats_file_write[journal-72-succeeded]` returned `unknown` where the fixture expected `succeeded`; isolated cases and the final serial suite passed.
- Initial run: wrong-byte Save verification reached `mark_unknown` with an absent action; subsequent runs passed.

These observations may have different causes. Storage environment, ownership/teardown, abrupt termination and journal/ledger ordering are hypotheses until measured. Passing isolated reruns do not establish a diagnosis.

**Key logic:**

1. Preserve failed roots before investigation. Record filesystem/mount type, free space/inodes, SQLite version, journal mode and available OS error codes without dumping private DB payloads.
2. Reproduce each failing case with fresh roots, both alone and in its surrounding suite order. Use a declared finite diagnostic schedule, retain every result and stop rerunning just to obtain green output.
3. Compare the same focused workload on the workspace filesystem and an ordinary local temporary filesystem if available. A mount-specific result is evidence about that environment, not proof of a production algorithm defect or proof that Windows is safe.
4. Trace which process/thread opens, commits, closes, checkpoints and removes each DB/WAL/SHM file. Confirm the existing instance lock and test cleanup do not overlap a live saver/worker.
5. Inspect journal claim/completion versus action-receipt durability around each crash boundary. A verified artifact alone cannot authorize replay; an uncertain receipt must not be translated to a fresh effect.
6. Make the smallest demonstrated fix. Preserve FULL durability, ownership locks and bounded cancellation. Do not catch I/O errors as success, delete WAL files, add unbounded retries or relax recovery assertions.
7. Add focused regression cases only for the demonstrated mechanism. Verify an unavailable/corrupt store fails safely and does not leave an indefinitely active task; derive the safe outcome from existing task/ledger policy.
8. Run focused recovery/budget/ledger tests, then a serial full suite on the final code. Repeat the affected crash workload on Windows before claiming Windows recovery qualification.

**Acceptance:** documented cause and fix, or a supported-environment limitation with reproducible evidence and an explicit unresolved status. Full V5 requires the supported target to pass regression. An unexplained isolated pass or blanket environment exemption does not close this stage. At every boundary, effects are attempted at most under their existing authority, and unknown work is never silently repeated.

## 6. V5.2 — Qualify the exact browser and production research path

**Inspect/extend:** `workflows/{fixture_qualification,fixture_research,qualification_records}.py`, `runtime/owned_processes.py`, `bootstrap.py`, `api/routes/workflows.py`, existing research-admission tests, and `tests/live/browser_support.py`.

**Key logic:**

1. Retry preparing the exact engine required by the locked Playwright version; validate the actual downloaded executable/version. The V4 alternate engine stays labelled alternate. If the exact archive remains unavailable, retain the block or make an explicit separately reviewed dependency change and requalify its affected scope.
2. Use the existing `qualify-fixture` runner for one smoke and a fresh 20-run complete campaign. The generic browser repetition report is not interchangeable with the stricter fixture promotion report.
3. Require both structured/text routes, distinct sources after redirect aliasing, exact artifact hashes, unique destinations and verified task/action receipts on unchanged source.
4. Exercise missing binary, real timeout, scope/redirect/popup/download restrictions, stale/ambiguous targets, destination conflict, interrupted worker and Stop. Report startup and cleanup failures without replacing the primary failure.
5. Validate owned-process observation on Windows: executable/creation/ancestry identities, unrelated concurrent browser launches, observation errors and no termination of user processes. Portable boundary mocks do not qualify Windows process enumeration.
6. Promote the complete matching report through the existing local maintenance command, restart an ordinary backend and prove actual registration without injected capability sets.
7. Use real authenticated HTTP/SSE for capability reporting, structured research, text command, replay, refresh, result readback and Stop. Follow with the dashboard path, literal rendering and keyboard controls.
8. Alter engine/fixture/runtime/evidence bytes in isolated negative fixtures and confirm admission is refused. Preserve the real promoted report separately.

**Acceptance:** exact intended engine, complete evidence and successful production-bootstrap flow for the bundled catalog. Windows process-cleanup qualification remains a separate required target check. No arbitrary URL or public website is admitted.

## 7. V5.3A — Complete one owned Notepad Save

**Inspect/extend:** `adapters/uia/{applications,native,selectors,actions}.py`, `workflows/{create_notepad_checklist,native_review}.py`, the installed Notepad profile and focused native tests.

**Key logic:**

1. On the actual Windows installation, compare executable hash/version with the pinned profile. Reinspect a changed app; never silently reuse stale selectors or ownership assumptions.
2. Confirm owned-child identity, one newly created selected tab, preservation of old tabs, unique window/control identity and an independently empty editor. Keep COM objects inside their worker.
3. Capture one fresh-root attempt with bounded phase/identity diagnostics around menu/dialog/filename/Save and verification. Historical missing/ambiguous-window and absent-artifact findings do not identify the current cause.
4. Correct only the observed Save or reacquisition boundary. Do not select the first ambiguous control, connect by process name or erase restored content.
5. Revalidate process/window/tab/editor, exact text/path, expiry, single-use review authority and Stop after waiting and immediately before the effect.
6. Verify exact file bytes/encoding/newlines plus native UI postconditions. File presence alone is insufficient.
7. On uncertainty, retain unknown, quiesce the owner and reconcile read-only. Preserve existing documents; cleanup must not terminate shared/restored user work.

**Acceptance:** one completely verified current-source native workflow. Do not launch a 20-run campaign after an unknown or failed first Save. If Windows is unavailable, code inspection and fake UIA tests can proceed, but this exit stays pending.

## 8. V5.3B — Finish native evidence, approval and admission

**Reuse:** existing `prepare-native`, `qualify-native`, `assemble-native` and `promote-native`; `workflows/native_qualification.py`, `qualification.py`, `qualification_records.py`; `test_native_http_review.py`; dashboard checklist contracts.

1. Prepare a session with fresh paths. Record >=20 successful unique-destination saves on unchanged runtime/profile/executable.
2. Complete actual multiwindow/restored/nonempty/stale/replaced/foreign-tab cases; missing/ambiguous controls; deny/expiry/reused approval; changed content/path/tab; conflict; Stop during wait/Save; shutdown/restart invalidation.
3. Capture both required physical display scales and actual measured DPI. Browser device-scale emulation does not satisfy this gate.
4. Exercise real authenticated HTTP and dashboard Save approval while the installed adapter retains its single mutation owner. Refresh/disconnect and duplicate clicks cannot create authority or a second Save.
5. Assemble reports from retained backing evidence and inspect missing cases. Operator observations remain operator-trusted; file hashes do not authenticate a human witness.
6. Promote only complete evidence, restart and verify the exact native profile is admitted through structured/text/review paths. Changed identities or incomplete review evidence keep it unavailable.

**Acceptance:** complete native/review/DPI record plus a fresh ordinary production request with exact independently verified result. No broad desktop capability follows from qualifying Notepad.

## 9. V5.4 — Pin and measure local command reasoning

**Inspect/extend:** `runtime/readiness.py`, `models/{gateway,ollama,contracts}.py`, `agent/{commands,command_execution,output_parser,router,context,budgets,benchmark}.py`, command service and existing sample/benchmark runners.

1. Inventory actual local runtime/tags, model name/digest, context/output settings and RAM/VRAM. The target remains 16 GB RAM and RTX 4050 ~6 GB VRAM; fit and latency require measurement.
2. Select one free local reasoning model deliberately. Qwen3 4B is the historical comparison, not a newly measured best-model recommendation. A missing service/model is a prerequisite block; embeddings cannot satisfy it. No paid/cloud fallback is required.
3. Keep deterministic note templates usable without inference. Serialize heavy model use through existing inference ownership; retain CPU/int8 STT where configured.
4. Pass live strict structured-output samples. Preserve closed tools, exact confirmed arguments, one repair within global budget, clarification and verifier-based success.
5. Diagnose measured failures, including historical F06 two-file behavior. No Python/shell/code fence becomes executable authority.
6. Execute the unchanged frozen 30-goal suite with its original 27/30 gate. Preserve suite SHA-256 `1a23540e729f3b62f9e0991fd7c53d6cd6e279a514f45f1e4a697949a273e340` after checking the actual file. Unavailable desktop prerequisites stay in the accounting; zero-executed attempts are unscored.
7. Add a separately reported held-out phrasing set for supported intents, ambiguity, missing values and prompt injection. Do not mix this score with the frozen benchmark.

**Acceptance:** reproducible exact model pin, actual inference and measured latency/resources/accuracy. Full reasoning qualification requires the frozen gate. Deterministic usability does not imply broad planning success.

## 10. V5.5 — Qualify reviewed English speech

**Reuse/extend:** `voice/{evaluation,action_evaluation,qualification_session}.py`, existing capture/STT/SAPI code, reviewed voice API/dashboard and `evaluation/voice/V3.6-protocol.md`.

1. Use the implemented protocol preparation and strict aggregation. V4 already fixed empty negative-category evidence; preserve those tests.
2. Freeze labels and numeric thresholds before evaluation. Collect 50 quiet and 50 noisy consented English note recordings plus silence/background/assistant-speech negatives. Separate tuning from held-out trials.
3. Report raw STT WER, intent and target accuracy by condition. Record manual corrections separately; corrected text is not raw recognition success.
4. Pair actual recording/session/reviewed command/task identities with independently verified note artifacts. Retain the operator-supplied pairing limitation and unique-recording requirements.
5. Witness microphone reconnect, actual decoding/review/playback Stop, audible mute/interruption, physical shortcut and speaker echo/cooldown on Windows.
6. Keep transcript confirmation separate from consequential Save approval. Native/browser speech needs its own labels/verifiers/corpus before expanding the note-only action evaluator.

**Acceptance:** declared thresholds met for recognition and actions, with separate witnessed physical evidence. Missing corpus or human session remains pending. Fake audio and UI contracts prove only their tested boundaries.

## 11. V5.6 — Freeze, soak and qualify the Windows folder candidate

**Inspect/extend:** `tests/live/m7_soak.py`, `scripts/{build-windows,package-self-test,package-upgrade-rollback}.ps1`, `packaging/windows/`, `runtime/release.py`, existing qualification identity and `docs/release/README.md`.

### Final regression and reliability

- Freeze selected implementation/config/contracts/locks. Run meaningful focused tests during edits and final backend/frontend/lint/build checks after the last source change. Preserve complete failure history.
- Run >=7,200 seconds, >=100 verified tasks, >=2 backup/restores, <=20% warmed-parent RSS growth, health p95 <0.5 seconds and no recorded failures, on unchanged source with normal guards.
- The V4 30-second smoke does not satisfy duration or workload gates. A full Linux run can establish portable harness behavior; confirm the actual Windows candidate separately.
- Add a supplemental workload for enabled browser/command/native paths and owned-child cleanup. Deliberate human review remains required; a note-only soak does not qualify native reliability.
- Capture identities before/after; source drift, blocked preflight or interrupted progress cannot produce qualification.

### Frozen package and deployment

1. Use fresh output/work folders with the pinned packaging environment and a final source manifest; retain previous bundles.
2. Test the actual frozen executable and its complete directory. Existing frozen identity and external account-owned record publication are implemented; validate them rather than redesigning them by default.
3. Run the candidate's own qualification commands for every advertised native/browser capability. Source records must not be relabelled or copied to bypass frozen identity.
4. Test missing/stale record, changed bundle/profile/browser, restart and ordinary capability reporting. Ensure record placement does not mutate the immutable implementation identity.
5. Run core package self-test and each advertised capability's targeted checks. Core self-test alone does not prove inference, hardware audio or native/browser automation.
6. Test on a fresh standard Windows account/dedicated machine without developer tools on PATH. Use account-owned data and respect DPAPI boundaries.
7. Separate guide number, app version, schema identity and artifact identity. Formal cross-version upgrade/rollback requires actual appropriately versioned old/new artifacts; same-version rehearsal stays labelled as such.
8. Rehearse old-binary backup, candidate migration and old-binary restore into a new root. Do not downgrade an active database or reuse old approvals.
9. Publish sanitized source/laptop/frozen/account evidence and an accurate scope decision. Keep raw tokens/audio/prompts/native trees/logs private.

**Acceptance:** full regression and stability gates, tested immutable package, matching frozen capability evidence and account/deployment proof. A limited typed-note candidate may be proposed explicitly while full V5 remains incomplete; it cannot silently waive inherited gates.

## 12. Verification entry points

These are future commands, not tests run while preparing this plan. Run from the repository root; use a new output suffix for every attempt and the appropriate pinned toolchain. Inspect existing runner help for optional model/profile parameters.

### Portable baseline and regression

```bash
uv sync --project backend --group dev --locked
backend/.venv/bin/python scripts/capture-source-manifest.py --output-directory .local/v50-start-01
backend/.venv/bin/python -m pytest backend/tests/test_agent_budgets_progress.py backend/tests/test_agent_graph.py backend/tests/test_notepad_workflow.py --basetemp=.local/v51-focused-01 --junitxml=.local/v51-focused-01.xml
backend/.venv/bin/python -m pytest backend/tests --basetemp=.local/v51-full-01 --junitxml=.local/v51-full-01.xml
backend/.venv/bin/python backend/tests/live/v3_baseline.py --data-dir .local/v50-baseline-01
npm --prefix dashboard ci --ignore-scripts --no-audit --no-fund
npm --prefix dashboard test
npm --prefix dashboard run lint
npm --prefix dashboard run build
```

Use pinned Node 24.22.0 on PATH. Portable UI runners support explicit absolute `VICTUS_TEST_NODE` and `VICTUS_TEST_BROWSER_EXECUTABLE`; optional `VICTUS_TEST_BROWSER_METADATA` records identity. These overrides never qualify a different production engine. Full regression failure must remain visible even when selected tests pass.

### Windows readiness and exact-engine fixture campaign

Create `.local/v5-readiness-01` first; the output parent must exist. Readiness reports do not perform inference or grant capability.

```powershell
backend/.venv/Scripts/victus.exe readiness --output .local/v5-readiness-01/report.json --model qwen3:4b
backend/.venv/Scripts/victus.exe qualify-fixture --repetitions 1 --output .local/v52-fixture-one-01
backend/.venv/Scripts/victus.exe qualify-fixture --repetitions 20 --output .local/v52-fixture-20-01
```

Only after inspecting a complete matching report:

```powershell
backend/.venv/Scripts/victus.exe promote-fixture --source .local/v52-fixture-20-01/report.json
```

Restart and separately prove ordinary production admission; promotion is not that proof. Equivalent source-mode checks can run on Linux where dependencies exist, while Windows process boundaries still need Windows evidence.

### Native first success, then full session

Confirm the actual installed profile identity before use; the profile below is the current candidate, not a promise that Windows updates preserve it.

```powershell
backend/.venv/Scripts/victus.exe prepare-native --profile notepad-win11-11.2607.14.0 --output .local/v53-session-01
backend/.venv/Scripts/victus.exe qualify-native --source config/applications/notepad-win11-11.2607.14.0.json --profile notepad-win11-11.2607.14.0 --repetitions 1 --output .local/v53-native-one-01
```

After verified success, use a fresh run directory and `--repetitions 20`. Populate the prepared session with actual run/case/DPI backing evidence, following its schema; do not mark unobserved cases as passed.

```powershell
backend/.venv/Scripts/victus.exe assemble-native --source .local/v53-session-01/session.json --output .local/v53-session-01/report.json
backend/.venv/Scripts/victus.exe promote-native --source .local/v53-session-01/report.json
```

Assembly may write an incomplete report and exit 2; only a complete matching record is promotable. Retain previous evidence and follow existing no-overwrite publication rules.

### Model, speech and final reliability

Use the actual installed model/digest with `m3_model_samples.py` and `m3_30_goal_benchmark.py`; no historical digest is assumed. Use real private corpus/threshold/binding paths with the existing voice modules. Preparation does not collect speech or witness hardware behavior.

```powershell
backend/.venv/Scripts/python.exe backend/tests/live/m7_soak.py --seconds 7200 --require-ready --fail-fast --output .local/v56-soak-01
backend/.venv/Scripts/python.exe scripts/capture-source-manifest.py --output-directory .local/v56-final-source-01
./scripts/build-windows.ps1 -OutputDirectory dist/v5-candidate-01 -WorkDirectory .local/v56-build-01 -SourceManifest .local/v56-final-source-01/source.json
./scripts/package-self-test.ps1 -Bundle dist/v5-candidate-01/Victus -OutputDirectory .local/v56-package-check-01
```

Capture a pre-soak manifest too and compare it to the final inventory. Use `package-upgrade-rollback.ps1` with actual retained prior/candidate bundles and a fresh output directory when that pair exists.

## 13. Definition of done and first implementation handoff

First implementation batch:

1. Capture V5's actual starting tree and record its relationship to PR #8.
2. Reproduce the three persistence observations, distinguish filesystem behavior from application ordering and document the measured cause before fixing it.
3. Make the smallest fix, retain no-replay/durability guarantees and run focused plus full portable checks.
4. Prepare the exact browser engine and complete fixture production admission independently of Windows Notepad progress.
5. Report exact changed files, commands/results, source identity and remaining Windows/model/corpus/duration requirements.

For every stage retain: problem, design, source/runtime identity, changed files, isolated root, actual boundary, commands, all outcomes, report/artifact hashes, cleanup and unresolved gates. Do not convert a missing prerequisite into a pass or erase an earlier failure with a later isolated success.

Full V5 completion requires the selected mandatory gates and inherited V4 obligations to be satisfied with matching evidence. Typed, browser, native, model, speech and packaged capability claims must each match their own measured scope.

Public-web catalog expansion, more applications, arbitrary MCP, custom wake, Hindi/mixed speech, cloud providers, installer/autostart and public distribution remain separate optional proposals. Complete the dependable core before expanding those surfaces.
