# V4 implementation handoff — tests to run and incomplete work

Prepared: 19 October 2026. Branch: `codex/v4-implementation-handoff`.
Base: `e87b1050217d342551aa1c43da37e2add276336e`.

The user's clarified instruction is to **skip Windows-dependent checks only**.
Portable Linux checks have now been executed. The original all-tests-skipped
statement applied to the first PR increment and is superseded by this follow-up.
No native Windows action, real microphone/SAPI session or Windows package test
was performed. No qualification record was promoted.

## Latest Linux validation — 19 October 2026

The test environment uses Python 3.12.14, locked backend dependencies,
Node **24.22.0** and the dashboard lockfile. Dependency lock bytes were preserved.
The initial system Node 24.19.0 was replaced only for these checks by an isolated
copy of the pinned Node executable; no project engine requirement was relaxed.

| Check | Measured result / scope |
| --- | --- |
| Expanded full backend regression | **875/876 passed**, 1 failed, 0 skipped, 194.614 seconds in the final serial run. Failure: `test_twelve_action_attempts_are_shared_across_plans`, SQLite disk I/O error at `backend/victus/storage/checkpoints.py:119`. Earlier 876-test run: 875 passed, one hard-restart recovery failure. Regression remains non-green. |
| New evidence/voice/process/Stop tests | Added `test_v4_portable_qualification.py`, `test_v4_voice_and_readiness.py`, `test_v4_process_observation.py` and two native-boundary fake tests: **59 additional tests**, all passing in the final full run. All run on Linux without touching a real desktop or microphone. |
| Frontend tests | **23/23 passed** on pinned Node 24.22.0. |
| Frontend lint, API generation, TypeScript/Vite build | Passed; generated contract bytes and dependency locks unchanged. |
| Changed Python lint/format | Ruff checks passed; final details recorded in the summary. |
| Real source HTTP/SSE baseline | **23/23 passed**, including commands/clarification, exact bytes, stable replay, auth and Stop. Real memory guard retained. |
| Real dashboard/API smoke | Passed real note/readback, deduplication, production session/reload/logout and mobile checks; no page errors. |
| Dashboard browser contracts | M5, M6, M7, M8, V3.3, V3.5 and V3.6 all passed. V3.3 11 checks, V3.5 9 checks, V3.6 10 checks. These use backend fixtures and do not qualify hardware. |
| Real browser adversarial fixtures | **10/10 passed** with explicitly selected Chromium 153.0.8010.0 and Playwright 1.64.0. |
| Supervised browser workflow repetitions | **20/20 passed**, required source counts/artifact hashes and observed scale factors recorded. Real normal resource policy retained. |
| Short reliability smoke | **30.313 seconds**, 4 verified notes, 4 memory cycles, 1 backup/restore, 59 health requests, no failures. This is **not** the required two-hour soak. |
| Live structured model samples | Attempted; `MODEL_UNAVAILABLE`, zero inference samples and no pin. |
| Frozen 30-goal model benchmark | Attempted; `MODEL_UNAVAILABLE`, zero executed goals, unscored. Historical 19/30 is unchanged. |

### Browser prerequisite limitation

The exact Playwright Chromium 156/build1248 download repeatedly returned an
invalid/truncated archive. This is an attempted **dependency/environment block**,
not a Windows-only skip. For portable regression, a separately downloaded,
explicitly selected Chromium **153.0.8010.0** from `@sparticuz/chromium@153.0.0`
was used. Its actual version/hash and Playwright version are recorded. No engine
path was disguised, production pin changed or qualification record installed.
The successful alternate-engine regressions do not qualify the missing pinned
engine, production fixture admission or Windows process cleanup.

### Failures discovered and changes made

- Fixed a real voice-evidence bug: empty negative-category objects could satisfy
  the aggregate gate. Every negative category now requires actual positive sample
  count and a strict, bounded proposal count. Regression tests cover this.
- Made the installed-profile inspection test portable by checking original
  Windows path syntax and loading a temporary fixture path; actual UIA is not
  simulated into a native pass.
- Updated the native failure-report test to supply a real reviewed profile and
  initialized test ledger, matching the strengthened runner's prerequisites.
- Added portable browser-test launch helpers for Node, process creation flags and
  an explicitly identified alternate Chromium. Original browser assertions are
  retained. V3.3 now accepts a fresh `--output` directory.
- Historical full-run failures remain recorded: a missing-ledger error during
  wrong-byte Save verification and a journal-crash recovery returning unknown.
  The wrong-byte case and both hard-restart cases passed isolated reruns. Their
  intermittent persistence behavior has not been diagnosed; isolated passes do
  not erase a full-run failure. The final serial run instead failed with
  `sqlite3.OperationalError: disk I/O error` while setting
  `PRAGMA synchronous=FULL` in `CheckpointStore.connect`
  (`backend/victus/storage/checkpoints.py:119`), reached from
  `test_twelve_action_attempts_are_shared_across_plans`. This storage/environment
  failure is unresolved and is not a Windows skip; no persistence assertion was
  weakened or retry added to conceal it.

Raw XML/logs remain private under `.local/v4-linux-validation/`. Sanitized counts,
exact report hashes, source identity and unresolved gates are in
[the Linux validation summary](release/v4-linux-validation.json). The full V4 and
release qualification flags remain false.

## 1. Implemented in this branch

| Area | Implementation and location |
| --- | --- |
| Native cancellation | `backend/victus/adapters/uia/applications.py`: worker-local operation guard checks before launch, owned-child/window polling and new-tab invocation/polling. Cleanup remains independent of Stop. |
| Native input | `backend/victus/adapters/uia/actions.py`: recheck operation guard before native Value/keyboard/Invoke boundaries; final Invoke guard also applies to explicit keyboard fallback. |
| Native workflow | `backend/victus/workflows/create_notepad_checklist.py`: connects worker Stop guard and checks Stop during verification polling. New-tab creation remains inside the dispatcher-routed launch effect. |
| Save authority | `backend/victus/workflows/native_review.py`: review target hash explicitly includes selected tab/window identity; policy is `native-save-v2`. |
| Evidence records | `backend/victus/workflows/qualification_records.py`: schema-2 strict JSON, duplicate/nonfinite/type rejection, bounded records, artifact/ledger/source identity validation and exclusive local publication. |
| Native promotion | `backend/victus/workflows/native_qualification.py`: prepare pending case/DPI templates, assemble retained runs/observations and promote only complete evidence. Operator observations are explicit, not cryptographic attestations. |
| Browser reports | `backend/victus/workflows/fixture_qualification.py`: startup/missing-binary/hash/cleanup failures produce reports; real Playwright timeout required; reports identify TestClient boundary and record task/action receipts. |
| Owned browser observation | `backend/victus/runtime/owned_processes.py`: read-only identity-based descendant tracking; unrelated browsers are neither included by name alone nor terminated. Uncertain observation prevents qualification. |
| Native repetition reports | `backend/victus/workflows/qualification.py`: schema-2 profile/runtime/report bindings, receipt IDs, unique filenames, fresh resource checks and partial failure persistence. |
| Frozen qualification | `qualification_records.py` and `packaging/windows/victus.spec`: frozen identity binds the exact bundle manifest and checks listed files; records live outside immutable bundle resources. Source records are not copied into frozen bundles. |
| Readiness | `backend/victus/runtime/readiness.py`: explicit current RAM/GPU/disk and local model-tag inventory. It never downloads, starts a model, infers or grants capability. |
| Voice evidence | `backend/victus/voice/{evaluation,action_evaluation}.py`: runtime/manifest/binding identity checks; recording hashes and unique recording requirement; recognition output refuses overwrite. |
| Voice session | `backend/victus/voice/qualification_session.py`: explicit predeclared thresholds and separate recognition/action/physical report aggregation for English notes. Preparation performs no capture/inference. |
| CLI | `backend/victus/cli.py`: readiness, native preparation/repetitions/assembly/promotion; fixture repetition count option and existing promotion retained. |
| Documentation | Root/dashboard README updated; empty M0 feasibility record filled; V4 progress, release procedure and this handoff explain current limits. |

## 2. Coverage map and additional cases still required

The lists below describe the broader desired coverage, not a claim that every
listed case now passes. Portable existing suites and the newly added tests were
run; consult the measured result table and exact test inventory. Add still-missing
cases where needed. Fake OS/audio/provider cases do not replace Windows hardware
qualification. Failed portable tests must be fixed or retained as open defects,
not labelled Windows-only skips.

### A. UIA ownership, Stop and native workflow

Files: `test_uia_profiles.py`, `test_notepad_workflow.py`,
`test_native_http_review.py`, `test_workflow_diagnostics.py`,
`test_approval_dispatch.py`, `test_supervisor.py`.

- Stop before launch, during child/window wait, before Add New Tab and during
  new-tab wait; no new native call after the observed latch.
- Original process/executable/creation/window identity preserved; no title-first
  selection, shared-process termination, restored-tab removal or document erase.
- No new tab, two new tabs, replaced/removed old tab, foreign process, duplicate
  runtime IDs, ambiguous container/window, invalid selection and missing editor.
- New-tab creation does not replace independent empty-editor proof.
- Change selected tab/window after approval is requested; binding invalidates.
- Direct pattern and explicit keyboard fallback obey the final cancellation guard.
- Stop during editor/dialog/file verification is bounded; partial effects remain
  unknown rather than rolled back or successful.
- Denied/expired/reused Save approval, changed target/text/path, conflicting file,
  shutdown/restart and exactly one mutation owner through review.
- Cleanup closes handles/COM despite Stop without terminating user documents.
- Exact approved filename/encoding/newlines/file bytes and native UI postconditions.

### B. Qualification records and native assembly

Files: `test_qualification_records.py`, `test_research_admission.py`,
`test_workflow_api.py`, and a proposed `test_native_qualification.py`.

- Valid schema-2 fixture/native records and bootstrap registration; schema 1,
  wrong version/kind, duplicate JSON keys, nonfinite numbers, booleans as counts,
  malformed arrays/strings and extra/missing required evidence rejected.
- Missing/oversized/linked/reparse file or ancestor, stale runtime/profile/engine,
  changed native executable and unsafe evidence-relative paths.
- 19 runs, duplicate filenames/task IDs/action IDs, wrong/missing artifact,
  inconsistent SHA, nonverified/missing/wrong-task ledger receipt rejected.
- Both structured/text routes required for browser promotion; a one-run smoke may
  pass smoke checks but cannot qualify or promote.
- Fixture source paths/origins/observation IDs/text hashes/distinct count checked.
- Native pending templates and partial sessions cannot promote. All named cases,
  retained backing evidence and two observed physical DPI reports required.
- Changing case/evidence/profile/executable/source after assembly prevents promotion.
- Native run roots remain beneath session; multiple native batches have distinct
  output names and never overwrite previous evidence.
- Concurrent publication, existing destination, partial publication and symlinks
  fail safely; installing a record does not change runtime identity.
- Missing or interrupted qualification output stays a failed/blocked report, not
  an unexplained apparent successful command.

### C. Browser qualification and process observation

Files: proposed `test_fixture_qualification.py`,
`test_browser_session.py`, `test_browser_network.py`,
`test_browser_observation.py`, `test_research_admission.py`,
and proposed `test_owned_processes.py`.

- Browser missing before startup, sync-driver error, fixture-startup failure,
  executable disappearing/changing, unknown telemetry and cleanup failure still
  persist useful reports with unavailable hashes explicit.
- A genuine Playwright timeout plus cleanup passes the timeout case; generic
  launch error, absent dependency or stale process observation does not.
- Process-tree tracking: exact creation times, PID reuse, rapid child exit,
  reparenting, inaccessible identities, bound/freshness failure and thread shutdown.
- Unrelated browser/driver launch does not authorize cleanup or become a VICTUS
  leak by process name alone. Monitor never terminates a process.
- Twenty unique verified artifacts, both routes, replay, redirects/aliases,
  destination conflicts, forbidden scope/transfers/popups, interrupted worker,
  no later post-Stop write and owned process shutdown.
- In-process TestClient evidence stays distinct from the real socket/ordinary
  production-bootstrap tests below.

### D. Source/frozen package qualification

Files: `test_packaging_release.py`, `test_qualification_records.py`,
`test_optional_integrations.py`, and actual frozen qualification commands.

- Source record cannot admit frozen runtime; two different bundle manifests
  produce different frozen identities even with the same application version.
- Missing manifest/source hash/file, changed size/hash, path escape, linked
  component and malformed inventory fail closed.
- Integrity cache rechecks metadata and rehashes changed files; unchanged
  inventory avoids repeated full-file hashing. The unsigned manifest does not
  authenticate its publisher or defend against a malicious same-user rewrite.
- Frozen records are under `%LOCALAPPDATA%/VICTUS/qualifications/<runtime hash>/`;
  source compatibility location remains adjacent to the source module unless
  `VICTUS_QUALIFICATION_DIR` selects an absolute external directory.
- Overrides, missing LOCALAPPDATA, link/reparse directories and changed
  executable/profile/browser prerequisites handled safely.
- Packaging excludes source qualification records and preserves previous bundles.
- Frozen CLI preparation/qualification/promotion, restart and targeted native/
  browser tests on the actual candidate; never manually replace a source digest.

### E. Local model readiness and commands

Files: proposed `test_readiness.py`, `test_ollama_provider.py`,
`test_model_gateway.py`, `test_command_admission.py`,
`test_command_execution.py`, `test_agent_budgets_progress.py`.

- Current low/unknown RAM, unavailable GPU/disk/service, model-tag ambiguity,
  wrong exact name and changed digest; inventory does not load/download anything.
- Pin selection is inventory only; an embedding model or installed tag does not
  become a qualified reasoning model.
- Deterministic commands work without a reasoning model; model output cannot
  change confirmed arguments, tool scope, approvals or verification.
- Explicit installed-pin structured samples, shared budgets, repair, timeout,
  clarification, Stop and restart; frozen 30-goal benchmark unchanged.

### F. Voice session and evaluation

Files: `test_reviewed_voice_commands.py`, existing voice evaluation tests,
and proposed `test_voice_qualification_session.py`.

- Exactly 50 quiet +50 noisy English labels, opaque unique IDs and required
  negatives; valid predeclared per-condition thresholds and nonnegative negative
  proposal limit; malformed/null/bool/nonfinite thresholds rejected.
- Thresholds/manifest fixed before measurement; changing source/manifest/audio/
  bindings during evaluation rejects the result.
- Reusing one audio file under multiple labels rejected; hashes do not export
  raw audio/reference/transcript paths or text.
- Recognition/action reports bind current runtime and same manifest; missing
  samples/metrics, stale reports and incomplete physical observations never pass.
- Missing reports produce an incomplete aggregate; no false accuracy for an
  unmeasured condition. Manual corrections cannot be reported as raw recognition.
- Existing note/action evaluator remains note-only; other intents/languages need
  additional labels/verifiers and corresponding explicit qualification.
- CLI invalid input, exclusive outputs and compatibility with existing voice
  review/clarification/cancellation flows.

## 3. Remaining work — distinguish skipped, blocked and incomplete

### Windows-dependent checks skipped in this environment

| Remaining check | Required evidence |
| --- | --- |
| Actual Notepad Save diagnosis | Observe installed app/process/tab/dialog transitions, committed destination, exact file/UI postconditions. Historical unknown Save is not claimed fixed. |
| Native workflow/review/DPI campaign | One native success, then >=20 unique saves; real adversarial cases, authenticated HTTP/dashboard Save review, actual display scales and Windows owned-process cleanup. |
| Windows physical input/output | Microphone disconnect/reconnect, spoken decoding Stop, audible SAPI mute/interruption, physical shortcut and actual speaker echo/cooldown. |
| Frozen Windows candidate | Build with Windows toolchain, actual frozen self-test, bundle-bound native/browser qualification and ordinary restart/admission checks. |
| Fresh standard Windows account/release pair | Clean account without developer PATH, DPAPI boundaries, actual prior/candidate backup/migration/new-root rollback and honest version identities. |

### Not Windows-only: attempted blockers and outstanding work

| Remaining item | Actual status |
| --- | --- |
| Portable full-regression reliability | Historical full runs exposed intermittent persistence/recovery failures. See each run, isolated reruns and final serial result in the summary; no weakened assertion or production deadline was introduced. Root cause remains unresolved. |
| Exact pinned Chromium | Installer attempted and failed with a truncated archive. Alternate Chromium regressions passed, but this dependency gate remains blocked. |
| Real local reasoning | Both live runners attempted; no local reasoning service/model was available. No score, automatic model download or cloud fallback. |
| Real labelled voice corpus | Synthetic unit tests passed; no 50 quiet/50 noisy consented recorded set was supplied. Thresholds, recordings, corrections and reviewed-action pairing remain required. |
| Two-hour reliability gate | The 30-second harness smoke passed, but >=7200 seconds, >=100 tasks, >=2 restores and full stability gates were not measured. This is a separate long-duration qualification, not a Windows-only test. |
| Production browser/native admission | Real note/command/API/UI paths passed. No browser/native qualification was promoted; real admitted production behavior still requires matching complete evidence. |
| Optional scope | Public-web catalog, custom wake, Hindi/mixed language and live cloud remain separately gated and outside these portable core checks. |

## 4. Follow-up commands and reproduction

The commands below use the target Windows environment and remain follow-ups
there; their Linux equivalents were run where reported above. Choose fresh roots
on repeats. Stop remains latched until service restart.

Portable backend reproduction from the repository root:

```bash
uv sync --project backend --group dev --locked
backend/.venv/bin/python -m pytest backend/tests --basetemp=.local/v4-linux-new --junitxml=.local/v4-linux-new.xml
npm --prefix dashboard ci --ignore-scripts --no-audit --no-fund
npm --prefix dashboard test
npm --prefix dashboard run lint
npm --prefix dashboard run build
```

Use the pinned Node 24.22.0 on PATH. Portable live dashboard runners accept
`VICTUS_TEST_NODE` and `VICTUS_TEST_BROWSER_EXECUTABLE` as explicit absolute paths;
`VICTUS_TEST_BROWSER_METADATA` optionally writes private JSONL identity metadata.
This never alters application production admission. For exact per-run arguments
and outcome boundaries see the sanitized summary and private logs.

### Source baseline and regression

```powershell
backend/.venv/Scripts/python.exe scripts/capture-source-manifest.py --output-directory .local/v4-final-source-new
backend/.venv/Scripts/python.exe backend/tests/live/v3_baseline.py --data-dir .local/v4-live-new
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_uia_profiles.py backend/tests/test_notepad_workflow.py backend/tests/test_native_http_review.py backend/tests/test_qualification_records.py backend/tests/test_research_admission.py --basetemp=.local/v4-focused-new --junitxml=.local/v4-focused-new.xml
backend/.venv/Scripts/python.exe -m pytest backend/tests --basetemp=.local/v4-regression-new --junitxml=.local/v4-regression-new.xml
npm --prefix dashboard test
npm --prefix dashboard run lint
npm --prefix dashboard run build
```

### Resource and exact installed-model inventory

Create the output parent first. This does not infer or qualify a model:

```powershell
backend/.venv/Scripts/victus.exe readiness --output .local/v4-readiness-new.json --model qwen3:4b
```

Use the actual installed name/digest from a deliberate selection for
`m3_model_samples.py` and `m3_30_goal_benchmark.py`; do not reuse a historical digest
blindly or select an embedding tag as reasoning.

### Native campaign and promotion

Confirm the installed profile still matches before opening real windows:

```powershell
backend/.venv/Scripts/victus.exe prepare-native --profile notepad-win11-11.2607.14.0 --output .local/v4-native-session-new
backend/.venv/Scripts/victus.exe qualify-native --source config/applications/notepad-win11-11.2607.14.0.json --profile notepad-win11-11.2607.14.0 --repetitions 1 --output .local/v4-native-session-new/runs/first
```

Only after a complete verified first success, run a fresh batch with
`--repetitions 20`. Observe the actual native adversarial/review/DPI cases. For
each `cases/<name>.json`, record observed status/source/profile/guard identity,
then bind retained backing evidence as `evidence: [{"file":"relative/path",
"sha256":"actual hash"}]` beneath the session. Keep private case data private.
`dpi-1.json` and `dpi-2.json` need actual witnessed DPI, passed/real_windows/
physical_observed and matching before/after identities. Do not check boxes to
work around missing proof.

```powershell
backend/.venv/Scripts/victus.exe assemble-native --source .local/v4-native-session-new/session.json --output .local/v4-native-session-new/report.json
backend/.venv/Scripts/victus.exe promote-native --source .local/v4-native-session-new/report.json
```

Assembly can write an incomplete report and exit 2. Promotion rejects incomplete,
stale or already installed evidence. All operator case observations remain
operator-trusted input; a checksum is not proof that a human performed a check.

### Browser campaign

```powershell
backend/.venv/Scripts/victus.exe qualify-fixture --repetitions 1 --output .local/v4-browser-smoke-new
backend/.venv/Scripts/victus.exe qualify-fixture --repetitions 20 --output .local/v4-browser-20-new
backend/.venv/Scripts/victus.exe promote-fixture --source .local/v4-browser-20-new/report.json
```

Restart normally and separately prove production HTTP/SSE/dashboard flows without
test-only service/registry injection. Public sites remain outside this gate.

### Voice protocol

Finalize the private English note label manifest before preparing a session.
Supply a private threshold JSON with `quiet` and `noisy` objects each containing
`max_word_error_rate`, `min_intent_accuracy`, `min_target_accuracy`,
`min_action_accuracy` (fractions 0..1), plus integer `max_negative_proposals`.
These are user-selected, predeclared thresholds, not invented historical gates.

```powershell
backend/.venv/Scripts/python.exe -m victus.voice.qualification_session prepare --source C:/private-voice/labels.json --thresholds C:/private-voice/thresholds.json --output C:/private-voice/v4-session
```

Record the labelled audio at paths referenced by the copied session manifest.
Use existing `victus.voice.evaluation` and `victus.voice.action_evaluation` to
write `recognition.json` and `actions.json` in that session. Record corrections
separately, complete witnessed `physical.json`, then:

```powershell
backend/.venv/Scripts/python.exe -m victus.voice.qualification_session evaluate --source C:/private-voice/v4-session/protocol.json --output C:/private-voice/v4-session/summary.json
```

### Soak and frozen candidate

```powershell
backend/.venv/Scripts/python.exe backend/tests/live/m7_soak.py --seconds 7200 --require-ready --fail-fast --output .local/v4-soak-new
./scripts/build-windows.ps1 -OutputDirectory dist/v4-candidate-new -WorkDirectory .local/v4-build-new -SourceManifest .local/v4-final-source-new/source.json
./scripts/package-self-test.ps1 -Bundle dist/v4-candidate-new/Victus -OutputDirectory .local/v4-package-new
```

In a frozen build, use that exact `Victus.exe` for readiness/qualification/
promotion; its records are bound to that bundle. Source records are deliberately
invalid for it. Qualify actual advertised capabilities before claiming package
support. Fresh-account and actual prior-release pair remain separate gates.

## 5. Review and merge status

The prior all-tests-skipped status is superseded by the Linux results above.
Keep the PR as a draft while portable persistence failures and required Windows/
model/audio/release gates remain unresolved. No previous 804/23 count, source
fixture, silent audio or edited digest is represented as a new qualification.
A passing isolated rerun is reported alongside the failed full run. No runtime
safeguard, graph budget or no-replay assertion was relaxed to obtain results.

## PR #8 conflict resolution — 19 October 2026

Merged main revision `ae3876c9b10b2f94136fb529096849198cef5834` into the PR
branch. The conflict in `workflows/qualification_records.py` is resolved by
combining main's fixture artifact provenance checks with V4's strict schema-2
parsing, artifact/ledger receipts, runtime/engine binding and exclusive publication.
Main's 20-run request count and alternating route checks are retained. Synthetic
fixtures now include the real report fields required by both implementations.
The main-branch regression tests are retained with additional malformed-provenance
cases.

Targeted portable validation: **68/68 passed**, zero errors/failures/skips, covering
fixture provenance, V4 qualification, qualification records and research admission.
Changed Python Ruff lint/format and `git diff --check` passed. No Windows or new
full-suite campaign ran for this conflict-only update; earlier full-suite failures
remain unresolved. Earlier runtime/source-bound results describe their original
inventory, not this merged runtime. No capability was promoted.
