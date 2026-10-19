# VICTUS V3 — Incomplete work, skipped tests, and handoff

**Recorded:** 2026-10-19 (Asia/Kolkata)  
**Repository:** `nithishgoud1912/victus`  
**Scope:** Original [V3 implementation plan](VICTUS-v3-Next-Stage-Implementation-Plan.md), [V3 checklist](VICTUS-v3-Build-and-Verification-Checklist.md), V3 milestone/evidence records, and later [V4 observed status](../docs/milestones/V4-progress.md).  
**Testing instruction for this consolidation:** **Do not execute any tests or device qualifications.** All test cases listed below are an unexecuted future checklist. Recorded historical test counts are not rerun here.  
**Release decision:** **NOT FULLY QUALIFIED.** Do not convert an implemented feature, a simulated test, or a safe refusal into a live successful workflow. Leave unqualified features gated.

## 1. What is already implemented

| V3 slice | Existing source work | Capability / qualification state |
| --- | --- | --- |
| V3.0 — Baseline | Source/dirty inventories, normal-policy note/HTTP/SSE baseline and historical test evidence | Core notes/queue/replay/Stop implemented; subject to authentication and resource pressure |
| V3.1 — Native Notepad | Pinned UIA profile, worker ownership, diagnostics, empty-editor checks, exact-byte Save verification, stop-on-unknown runner | **Native installed-app Save remains unqualified and disabled** |
| V3.2 — Approval | Persisted waiting-for-review state, exact target/path/payload/expiry binding, single-use permit, worker handoff and restart/Stop invalidation | Simulated worker/HTTP review tested historically; **real installed-app end-to-end approval unqualified** |
| V3.3 — Dashboard | Checklist form, server capability/unavailable status, literal preview, persistent task/approval IDs, replay, keyboard Stop | Implemented, historical browser/front-end evidence exists; **native UI control stays disabled** |
| V3.4 — Fixture browser | Closed server-owned fixture catalog, authenticated admission, owned browser/dispatcher/verified JSON reports | **Real Chromium 20-run gate not passed; disabled** |
| V3.5 — Text commands | Deterministic note/clarification path, bounded graph and strict model schemas | Deterministic admitted notes available; **broad local reasoning not qualified** |
| V3.6 — Voice/release | Reviewed transcript -> same command service, cancellation and generic result speech, packaging and evidence tools | Optional voice implementation exists; **real-corpus/device and release qualification incomplete** |

**Already in `main`:** The substantial earlier V3 implementation and historical evidence files. A pull request from a new branch can only show differences from `main`; it cannot re-submit unchanged historical code as new changes.

**Included in this consolidated PR:** The earlier separate V3 browser-artifact promotion-integrity code and regression tests, this closeout record and references from the original V3 checklist/plan. These additional code changes are **not tested in this request** and do **not** enable any capability.

## 2. Outstanding V3 implementation and real-world qualification

### V3.0 — Baseline / regression

- [x] Historical source inventory, isolated data-root controls, authentic note/queue/Stop baseline recorded.
- [ ] Rerun full note -> exact-bytes -> duplicate-ID replay -> snapshots/events -> clarification -> Stop baseline on the **final candidate source**, normal telemetry and isolated fresh data. The extended 23-check V4 baseline remained **blocked by real HTTP 503 / RAM pressure**, not passed.
- [ ] Capture a final before/after source/config/contract/lock inventory for the consolidated code changes, and retain relevant private reports; do not replace previous evidence.

### V3.1 — Native Notepad / owned editor and Save

- [x] Pinned installed profile, ownership isolation, diagnostic phases, empty-editor and pre-Save revalidation code exists.
- [ ] Finish a safe *new tab/document editor lease* for installed Notepad where session restoration presents nonempty tabs: require a newly proved, unique empty tab while preserving all existing documents. Follow [decision 007](../docs/decisions/007-v4-native-ownership-findings.md); no process-name/title-only fallback, no killing unrelated Notepads.
- [ ] Diagnose and resolve the live Save/window reacquisition issue. V4 observed a cold owned child and valid editor write, then an **unknown Save** with `WINDOW_MISSING_OR_AMBIGUOUS` and no confirmed output; a second run refused a nonempty editor. Preserve unknown ledger effects, inspect read-only before any new attempt; never auto-repeat a possible Save.
- [ ] Prove **one** verified supervised installed-Notepad workflow with exact file bytes, correct path/encoding and native UI postconditions, then **20** further successful independent runs with unique destinations.
- [ ] Prove negative tests on real app: second window/tab, restored/nonempty editor, stale/replaced process, missing/duplicate controls, existing destination, denied/expired/reused approval, changed payload/path/target, Stop during Save, and no writes to unrelated documents.
- [ ] Measure and pass at least **two actual physical Windows display scales**; recording one DPI=120 observation is not a two-scale pass.
- [ ] Keep native production registration disabled until both native and real review gates pass.

### V3.2 — Real approval + task service

- [x] Single worker-owned review lifecycle, durable approvals, permit binding, API routes and revalidation coded; deterministic/simulated tests historically passed.
- [ ] With the **actual installed Notepad adapter**, prove authenticated submit -> persisted waiting state -> literal destination/content/expiry review -> approve once -> Save invoked once -> independently verified bytes/UI.
- [ ] Validate deny, expiration, reuse, browser disconnect/reconnect, changed editor/target/path, Stop, restart, uncertain response retry using same identity, generic `/api/tasks` bypass rejection, and no automatic replay.
- [ ] Bind/persist trusted *native and review qualification* on exact runtime/profile/executable; only then permit server-side bootstrap registration. Never admit qualification from client request fields.

### V3.3 — Dashboard

- [x] Checklist, read-only capability status and unavailable reason, review preview and replay/Stop UI implemented; historical frontend and simulated-browser evidence passed.
- [ ] Re-run keyboard-only review/deny/Stop, refresh during review, reconnect/cursor, duplicate click, expired login/approval, mobile viewport, literal HTML-safe text, reduced-motion, unknown result, and unavailable-profile contracts **on the final candidate and real service**.
- [ ] Demonstrate the real installed-app HTTP/dashboard approval interaction when V3.1/V3.2 gates permit it. Do not render native as available meanwhile.

### V3.4 — Fixture research / Chromium

- [x] Strict fixture-only contract, observed-source hashes, dispatcher and graph routing, no arbitrary URL/unsafe transfer admission implemented.
- [ ] Run actual Chromium under the **unchanged 2 GiB free-RAM admission policy**, using new isolated roots; previous V3/V4 attempts stopped with `RESOURCE_PRESSURE` before completing research.
- [ ] Pass **20** unique verified reports with distinct sources and exact report hashes; alternate structured and text commands; prove request replay and post-run owned browser/driver process cleanup.
- [ ] Pass redirect alias and scope-escape protection, source shortage, destination conflict, missing browser binary, timeout, interrupted worker, Stop-no-later-effect, and resource-pressure cases.
- [ ] Review the new artifact-provenance validation and tests included in this PR. Re-run source-bound qualification after any code change. Promote `fixture-qualification.json` only from complete matching proof, then restart and test actual bootstrap admission.
- [ ] **Public web is not part of fixture qualification.** A separate server-reviewed public HTTPS catalog, redirect/network/transfer constraints, source-to-claim checking and public-site live tests are needed before calling public research supported.

### V3.5 — Local natural-language reasoning

- [x] Bounded commands, durable clarification, strict parser/graph, budgets, deterministic note route and verifier requirements implemented.
- [ ] Observe currently installed Ollama reasoning model, select a supported **exact name + digest**, record memory/VRAM/context configuration and prove its loopback readiness. Historical inspection found only an embedding model and unavailable Ollama service; **no reasoning pin**.
- [ ] Rerun the **unchanged full 30-goal benchmark**, with its existing >=27/30 verified requirement, and publish all executed/failed/blocked categories. Historical result **19/30** failed the gate; later V3/V4 runs executed **zero** goals because the model was unavailable—this is **not** a measured 0/30 score.
- [ ] Test ambiguous/missing values -> clarification before effects, hostile page instructions, invalid JSON/tool output, model timeout, budget exhaustion, Stop during model/review, restart/replay and zero false positive finishes, on a real local pinned model.
- [ ] Keep deterministic note commands available without model; never silently switch to cloud or authorize unsupported browser/desktop tools.

### V3.6 — Reviewed speech, reliability and Windows release

- [x] Speech transcription review -> same `CommandService`, Stop/cancellation hooks and result-speech implementation exists; historical isolated device components and packaging scripts have evidence.
- [ ] Collect **50 consented, labelled quiet** and **50 consented, labelled noisy** real commands; measure STT recognition separately from human edits/corrections and verified end-to-end actions. Historical count: **0/50 quiet and 0/50 noisy**.
- [ ] Witness physical microphone unplug/reconnect, Stop while real speech is decoding, acoustic self-trigger/echo suppression, audible interruption/mute and privacy/ownership handling. Component simulations/device smoke do not establish these outcomes. Hindi/mixed-language and custom wake require independent qualification.
- [ ] Freeze final tested source and run backend/frontend regression, API contract generation, lint, production build and relevant real Windows/browser/voice integration tests; **none is rerun in this PR**.
- [ ] Complete **7,200 seconds (2 hours)** of unchanged-source reliability with at least **100 verified tasks**, >=2 backup/restore cycles, warmed RSS growth <=20% and health p95 <0.5s, with real RAM guard and no false-success ledger outcomes. Earlier V3.6 soak was incomplete; V4 preflight refused a new run for `RESOURCE_PRESSURE`.
- [ ] Build and self-test a **fresh folder package from this final source**, with exact implementation/bundle manifest identity; run relevant frozen behavior. The previous V3.6 package passed **21 historical same-account checks**, not new-source qualification.
- [ ] Run on a **fresh standard Windows account** (not the developer environment) and qualify actual targeted dependencies (model, browser, microphone) for advertised capabilities.
- [ ] Use a formally distinct **versioned** prior release / new candidate pair for real install/upgrade, migration, backup/restore and old-bundle rollback. The historical schema-7 -> schema-8 test passed **8 checks** between two artifacts both identifying product version `0.1.0`; this did **not** meet formal cross-version qualification.
- [ ] Publish an exact evidence-bound capability matrix. Do not advertise native, browser, public-site, model, voice or release readiness without its independent passing gate.

## 3. Test status (no tests run for this handoff)

**Explicit decision:** Testing and qualification are *deferred at the user's request*. No new pytest, dashboard tests, browser/Notepad runs, local-model inference, audio sampling, soak or frozen-package check was executed to create this document/PR. The status of the new browser evidence-integrity code is **unverified pending tests**.

| Recorded evidence from older source states | Historical result (not rerun or applicable automatically to this PR) |
| --- | --- |
| V3.0/V3.1 backend and real HTTP/SSE | 735 backend tests; 14/14 real authenticated loopback checks |
| V3.2/V3.3 backend/frontend | 751 backend; 23 frontend; simulated native review/browser checks |
| V3.4/V3.5 backend/frontend | 781 backend; 23 frontend; live fixture blocked by RAM; frozen 30-goal rerun unavailable |
| V3.6 backend/frontend | 791 backend; 23 frontend; 21 prior-package self-test checks; 8 prior-artifact-pair checks |
| Later V4 changed-source regression | 804 backend; 23 frontend; **23-check live baseline still resource-blocked**, native/browser/model/soak gates open |

These numbers are snapshots of *different tested inventories*, not an assertion of passing tests on this PR.

### Deferred test entry points (for a later deliberate Windows session)

All commands below are **instructions only, not executed**, and should use new unused output roots. Before any actual UI/AUDIO run, inspect script arguments and qualify external effects with a human present.

```powershell
# PR-specific focused checks
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_qualification_records.py backend/tests/test_fixture_artifact_provenance.py

# Final backend and dashboard regression
backend/.venv/Scripts/python.exe -m pytest backend/tests --basetemp=.local/v3-closeout-regression-new --junitxml=.local/v3-closeout-regression-new.xml
npm --prefix dashboard test
npm --prefix dashboard run lint
npm --prefix dashboard run build

# Real source baseline and native first supervised run (fresh roots)
backend/.venv/Scripts/python.exe backend/tests/live/v3_baseline.py --data-dir .local/v3-closeout-api-new
backend/.venv/Scripts/python.exe backend/tests/live/workflow_qualification.py notepad --data-dir .local/v3-closeout-native-one-new --repetitions 1 --profiles config/applications/notepad-win11-11.2607.14.0.json --profile notepad-win11-11.2607.14.0 --encoding utf-8

# Only after safe one-run native success: 20 fresh supervised runs and human review
# Independent real-Chromium fixture qualification (20 runs by default)
backend/.venv/Scripts/python.exe backend/tests/live/v34_research_qualification.py --output .local/v3-closeout-browser-new

# Soak only after final source is frozen and prerequisites are ready
backend/.venv/Scripts/python.exe backend/tests/live/m7_soak.py --seconds 7200 --require-ready --fail-fast --output .local/v3-closeout-soak-new
```

Inspect model benchmark flags and package script prerequisites from the original V3/V4 guides; do not assume a model or Windows executable is installed. Never claim an unavailable or pressure-blocked task as a pass.

## 4. Evidence sources and ownership of next actions

- [Original V3 plan](VICTUS-v3-Next-Stage-Implementation-Plan.md) and [original checklist](VICTUS-v3-Build-and-Verification-Checklist.md).
- [V3.0/V3.1 native milestone](../docs/milestones/V3-progress.md) and [native diagnostic decision](../docs/decisions/007-v4-native-ownership-findings.md).
- [V3.2/V3.3 real review/dashboard milestone](../docs/milestones/V3.2-3-native-review-dashboard.md).
- [V3.4/V3.5 browser/commands milestone](../docs/milestones/V3.4-5-browser-commands.md).
- [V3.6 voice/release milestone](../docs/milestones/V3.6-reviewed-voice-release.md) and [sanitized V3.6 evidence](../docs/release/v3.6-reviewed-voice-release-evidence.json).
- [V4 observations](../docs/milestones/V4-progress.md), [V4 execution evidence](../docs/release/v4-execution-evidence.json), and [supported-workflow matrix](../docs/supported-workflows.md).

**Handoff:** Code/deterministic integration is not equivalent to machine qualification. Keep the production gates intact; clear live conditions on the actual laptop and add source-bound evidence only when those checks are performed. This file is a truthful snapshot of incomplete V3 requirements, not a completion certificate.
