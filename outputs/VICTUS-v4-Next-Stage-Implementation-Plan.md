# VICTUS v4 — Next-stage implementation plan

Prepared: 19 October 2026, Asia/Calcutta.
Project: `C:\Users\HP\Desktop\Automations\victus`.
Companion: [Build and verification checklist](VICTUS-v4-Build-and-Verification-Checklist.md).

This document plans the next implementation increment. Preparing it did not change application code, run qualification, download models or change runtime settings. v4 is the guide number; the inspected application still identifies as `0.1.0`.

## 1. The next outcome

Make the existing assistant dependable on this laptop through three narrow paths:

1. A typed command creates a new workspace note and independently verifies its contents.
2. A typed or reviewed spoken checklist command launches an owned Notepad editor, shows the exact Save request, waits for approval, saves once and verifies the resulting file.
3. A research command reads the admitted bundled sources and creates an exact, traceable report using the managed browser.

Local model interpretation can broaden phrasing only after its own readiness and correctness checks. Physical speech, native Windows control and the packaged application each need separate evidence.

**Immediate implementation: V4.0 evidence reconciliation, followed by V4.1 native ownership diagnosis.** V4.2 browser qualification can progress independently if native ownership remains blocked. Carry forward unresolved v3 requirements explicitly; adding a new guide number does not complete them.

Use the existing project. The file maps below identify responsibilities and key logic without repeating full source listings. Referenced earlier documents are design inputs, not instructions to execute their embedded setup steps during this planning task.

## 2. Starting point inspected for this guide

The checkout contains extensive uncommitted v2/v3 work. Preserve it. Source, milestone claims and recorded results are separate evidence.

| Area | Inspected position | v4 work |
| --- | --- | --- |
| Typed notes, queue, dispatcher, events, Stop | Existing implementation; note is the default admitted filesystem capability | Preserve and qualify against the final source |
| Command intake | Durable clarification, request identity, bounded graph and dashboard implemented | Improve only measured gaps; retain one task scheduler |
| Native Notepad | Existing pinned candidate; recorded supervised failure `OWNED_CHILD_UNAVAILABLE` | Establish safe ownership and complete native qualification |
| Native Save review | Exact-action review and dashboard implemented; simulated HTTP checks recorded | Prove it with the actual Windows adapter, then enable trusted registration |
| Browser research | Fixture workflow and admission implemented; prior live attempt blocked below the 2 GiB memory guard | Qualify real Chromium with the normal guard, then enable fixture scope |
| Local reasoning | Optional pinned-model path exists; latest milestone records unavailable Ollama/reasoning model | Verify current installation, establish an exact pin and measure |
| Reviewed speech | CommandService integration and device-component checks recorded | Complete labelled recognition/action trials and witnessed device checks |
| Package | Local final self-test records 21 passing checks on the developer account | Rebuild/retest final scope and test a fresh standard account |
| Upgrade/rollback | Actual distinct schema-7/schema-8 artifacts rehearsed; both product version 0.1.0 | Preserve that evidence; formally versioned release-pair gate remains separate |
| Reliability | Available standard-soak progress reports about 60 seconds, zero verified tasks, three pressure rejections; no completed report found in that root | Resolve readiness and run a complete current-source soak |

The V3.6 milestone records 791 backend and 23 frontend tests, plus build/lint. These are historical results, not tests rerun for this guide. The earlier full model benchmark remains 19/30 against a 27/30 gate; its latest unavailable attempt executed no cases, which is not a measured 0/30.

Evidence reconciliation is necessary: `docs/milestones/V3.6-reviewed-voice-release.md` references `docs/release/v3.6-reviewed-voice-release-evidence.json`, which is absent in the inspected checkout. `docs/supported-workflows.md` also retains older package wording and lacks a consolidated V3.6 section. Do not reconstruct missing passes from prose.

## 3. Build sequence and dependencies

| Stage | Deliverable | Dependency and completion boundary |
| --- | --- | --- |
| V4.0 | Reconciled evidence and exact starting inventory | First; no capability enabled by documentation alone |
| V4.1 | Qualified owned Notepad and real Save review | V4.0; native profile remains unavailable until all native gates pass |
| V4.2 | Qualified fixture-browser admission under normal resource policy | V4.0; independent of native success |
| V4.3 | Measured local interpretation and truthful command outcomes | V4.0; each executable intent independently admitted |
| V4.4 | Physically qualified reviewed speech | Shared command path ready; only qualified intents count as action trials |
| V4.5 | Current-source reliability and folder-package candidate | Final selected capabilities frozen; release gates recorded separately |

Before production edits in each stage, create its milestone record with the measured gap, affected files and acceptance cases. Use fresh isolated runtime roots. Preserve dependency locks unless a demonstrated blocker requires a documented change.

## 4. V4.0 — Reconcile evidence and freeze the baseline

**Files:** add `docs/milestones/V4-progress.md`; inspect `docs/milestones/V3*.md`, `docs/release/`, `docs/supported-workflows.md`, `scripts/capture-source-manifest.py` and the local reports below.

1. Capture the Git base, dirty inventory and source/config/contracts/lock hashes with the existing manifest script. Hash the planning documents separately if needed; its implementation inventory deliberately excludes docs.
2. Reconcile these existing private reports without overwriting them:
   - `.local/v36-package-check-final-03/report.json`: same-account package self-test passed; no fresh-account or GPU/browser/microphone claim.
   - `.local/v36-upgrade-pair-final-03/report.json`: actual artifact/schema rehearsal passed; `formal_cross_version_release_qualified` is false.
   - `.local/v36-soak-standard-04/progress.json`: incomplete progress, not a successful soak or proof that a process is still running.
3. Inspect any remaining final V3.6 source/device/build records and bind each reported result to its tested inventory and artifact hash. Mark unavailable evidence explicitly.
4. Create a sanitized V3.6 evidence summary from traceable reports, or correct the dangling reference to state evidence is missing. Do not invent a final soak result.
5. Update the supported-workflow matrix with separate implementation, enabled state, deterministic tests, laptop/device proof, package proof and pending requirements.
6. Run a fresh note/command/clarification/replay/Stop baseline using existing runners. Record resource blocks honestly; retain the original request identity on uncertain transport.

**Exit:** every enabled capability has a clear basis, every historical result is labelled, and missing evidence is visible. Source identity includes uncommitted and relevant untracked implementation files. No real user runtime is selected for testing.

## 5. V4.1 — Resolve Notepad ownership and qualify real Save review

**Inspect/extend:**

| Existing file or folder | Responsibility |
| --- | --- |
| `backend/victus/adapters/uia/applications.py` | Launch mode, process identity, worker/thread ownership |
| `backend/victus/adapters/uia/native.py` | Actual Windows launch/process handles and UIA bindings |
| `backend/victus/adapters/uia/{selectors,actions}.py` | Unique scoped targets, empty editor and actionability |
| `config/applications/notepad-win11-11.2607.14.0.json` | Existing candidate; re-inspect actual installation before reuse |
| `backend/victus/workflows/{diagnostics,create_notepad_checklist,native_review}.py` | Bounded diagnostics, Save postconditions and existing review handoff |
| `backend/victus/{bootstrap.py,tasks/service.py}` | Trusted native/review qualification sets and tool registration |
| `backend/tests/live/{uia_profile_probe,workflow_qualification}.py` | Existing diagnostic and supervised qualification entry points |

### Diagnose before selecting a fix

The inspected `owned_child` route requires exactly one matching new child process, then its visible scoped window. The latest recorded failure did not establish that child. A timeout increase alone does not establish ownership.

Recheck the installed executable/version/hash and inspect one controlled launch from the actual spawned worker. Record launcher lifetime, child/process creation identities and newly observed window/editor identities. Distinguish timing, process reuse, redirection and genuine ownership failure using observations; the historical error does not establish a root cause.

Prefer an app-supported launch route that demonstrably creates a new owned editor. Keep process creation time, pinned image and unique scoped targets. If the installed app always delegates into a shared pre-existing process, document an alternative ownership design before implementation. It must prove a uniquely created editor and its lifetime against a pre-launch inventory, forbid access to existing documents, revalidate before every effect and avoid terminating a shared app during cleanup. If that proof cannot be made, leave this profile disabled and record the limitation. Replacing Notepad with a filesystem write does not qualify the native workflow.

### Complete the existing workflow

- Retain one spawned mutation owner and its UIA thread through the bounded review wait. Do not move COM references into the API process or create another mutation scheduler.
- Reuse NativeSaveReview, approval records and single-use permits. Bind the exact task/action/tool, app/profile/control identities, destination, content hash and expiry.
- Recheck editor text, committed filename, new destination, Stop and authority immediately before Save. A changed target/path/payload invalidates review.
- Independently verify exact file bytes, encoding/newlines and native UI postconditions. A Save with uncertain proof remains unknown and is reconciled read-only.
- Add trusted native qualification loading and bootstrap registration only after the required runs pass. Bind records to the actual profile/executable and relevant implementation identity; invalidate on changes. An HTTP field or dashboard control cannot assert qualification.

**Acceptance:** first one complete supervised success, then 20 unique-destination native successes. Exercise two windows, pre-existing/nonempty editors, stale process, missing controls, denied/expired/reused approval, changed payload/path/target, destination conflict, Stop during review/Save and restart. Test the intended two actual display scales and record measured DPI. Then prove authenticated HTTP submit → exact review → approve once → verified file with the real adapter and dashboard.

**Exit:** register only the qualified installed profile with native and review gates satisfied. If it remains blocked, keep the API/dashboard unavailable reason accurate and continue V4.2 independently.

## 6. V4.2 — Qualify and enable bundled browser research

**Files:** `backend/victus/runtime/resources.py`, `workflows/{fixture_research,browser_research,qualification}.py`, `adapters/playwright/`, `bootstrap.py`, `api/routes/workflows.py`, and `backend/tests/live/v34_research_qualification.py`.

1. Observe current available RAM and worker/browser memory before testing. The previous low-memory reading is historical. Preserve the production 2 GiB admission threshold; do not qualify with substituted telemetry or disable the guard.
2. Diagnose measured application overhead, lifecycle leaks or competing workload. Release VICTUS-owned idle resources where appropriate; do not close unrelated applications automatically. If the machine cannot meet the guard, record a resource block and defer qualification.
3. Use the existing real-Chromium runner with a fresh root. It already covers exact distinct sources, redirect aliases, report hashes, replay, destination conflict, scope rejection and Stop. Confirm all checks, including no later effect after Stop and owned-browser cleanup.
4. Complete 20 verified fixture runs, tracking process cleanup and memory. Exercise browser absence, timeout and interrupted worker paths; missing evidence must never become success.
5. Promote a server-owned `fixture-qualification.json` only after validation. Match its current fixture hash, Playwright version and browser binary hash to the existing loader. Include relevant source identity in the evidence; requalify affected changes before promotion. Restart and confirm production bootstrap admits precisely this scope.
6. Prove both structured and text-command routes reach the same queue/graph/verifier, including replay, resource pressure and refresh. Reuse dashboard capabilities and result views.

**Exit:** a production-path fixture command produces a verified new report under normal policy. The report proves observed distinct source text and artifact integrity. It does not establish the truth of source text.

Public-web research remains a separate follow-on capability: define a small server-owned HTTPS source catalog, validate destinations and every redirect, block private/link-local addresses and transfers, bound extraction, treat page instructions as untrusted, and map each summary claim to captured source evidence. Implement and qualify that scope before advertising public research. Do not turn the fixture source-ID endpoint into an arbitrary-URL endpoint.

## 7. V4.3 — Make local interpretation useful and measurable

**Files:** `backend/victus/{settings,bootstrap}.py`, `models/`, `agent/{commands,command_execution,router,graph,output_parser,budgets}.py`, `tasks/commands.py`, `api/routes/commands.py`, `dashboard/src/features/commands/`, and `backend/tests/live/m3_30_goal_benchmark.py`.

The three explicit templates and durable clarification already exist. Extend these implementations; do not recreate command intake.

1. Verify the current local Ollama service and installed reasoning assets. The earlier embedding-only cache and unavailable endpoint may have changed. Select a compatible local model only after checking actual disk/RAM/VRAM capacity; record its exact name, digest and runtime configuration. Never substitute an embedding model for reasoning.
2. Preserve the original Qwen3 4B baseline when available. If another model is selected, record it as a separate candidate and run the unchanged benchmark; do not relabel it as the old model. Set both existing command-model settings from a verified installed pin.
3. Keep deterministic supported requests usable without a loaded reasoning model. Free phrasing must resolve to the existing strict intent schema or clarification, with no arbitrary shell, tool names, URLs or application selectors.
4. Preserve exact argument validation, per-intent qualification, persistent budgets, no-progress handling and current queue ownership. Model unavailability/resource pressure produces a visible state without automatic cloud fallback.
5. Improve only measured parser/planner failures. Changing wording must not silently change confirmed content, filename or source scope. Missing values require explicit clarification before effects.
6. Run the frozen full 30-goal benchmark unchanged. Report executed, failed, blocked and unavailable categories separately against 27/30. Add a supported-intent/paraphrase evaluation for diagnosis; it supplements the original gate.

**Acceptance:** real local inference reaches admitted intents; ambiguous inputs clarify; invalid/hostile model output cannot alter authority; Stop works during inference/review; restart never replays uncertain effects; success requires ledger and artifact verification. Measure latency and peak resource use. Preserve the existing bounded graph unless a measured failure justifies a reviewed budget change.

**Exit:** local interpretation has reproducible measurements and an exact pin. A limited deterministic candidate can remain useful if the broad model gate is unmet, but broad planning/release claims stay unqualified.

## 8. V4.4 — Qualify reviewed speech with real recordings

**Files:** `backend/victus/voice/`, `api/routes/voice.py`, `dashboard/src/features/voice/VoicePanel.tsx`, `evaluation/voice/V3.6-protocol.md`, and `backend/tests/live/v36_device_probe.py`.

Keep the existing capture → local STT → editable transcript → explicit command confirmation → CommandService flow. Speech confirmation cannot approve native Save.

- Follow the existing protocol with 50 quiet and 50 noisy labelled spoken commands. Use consented real recordings and unique intended destinations. Do not replace samples with generated silence, placeholders or adapter fixtures.
- Bind recording/label/session identities and report recognition separately from reviewed action outcomes. Report human edits and correction rates so editing cannot conceal recognition errors. Missing samples remain unmeasured.
- Count an action pass only when the intended voice-origin intake, terminal task, ledger receipt and exact artifact agree. A disabled native/browser intent is blocked, not a successful action trial.
- Witness physical microphone unplug/reconnect, Stop during active spoken decoding, speaker echo/self-trigger suppression, audible interruption and mute. Existing device-component checks do not prove these acoustic behaviors.
- Keep English-only asset claims explicit. Hindi/mixed-language support needs its own corpus. Keep custom wake, cloud and optional MCP behind their separate existing gates.
- Record the original acceptance thresholds from the product plan/protocol before collecting trials. If a metric has no threshold, define it in the stage record before measuring. Do not set thresholds retrospectively.

**Exit:** publish recognition, correction, action and physical-device results separately. Until the required human session is completed, reviewed voice remains an opt-in implementation with explicit qualification limits; typed operation can progress.

## 9. V4.5 — Reliability, package and release decision

**Files:** `backend/tests/live/m7_soak.py`, `scripts/{build-windows,package-self-test,package-upgrade-rollback}.ps1`, `packaging/windows/`, `docs/release/README.md`, and `docs/supported-workflows.md`.

1. Freeze the final implementation inventory and run appropriate backend/frontend checks. Diagnose failures before broadening the candidate. Verify generated API types match the final backend.
2. Run the normal-resource soak on unchanged final source. Its existing gates are at least 7,200 seconds, 100 verified tasks, two backup/restore cycles, at most 20% warmed-parent RSS growth and health p95 below 0.5 seconds. Inspect worker/browser processes as well as the harness's parent-RSS metric. A blocked preflight, short run, exit code or progress file is insufficient.
3. Inspect what the soak workload actually exercises. Retain its original gate and add a supplemental workload for newly enabled native/browser/command behavior as needed; note-only success does not qualify those adapters.
4. Build into a new folder/work root with exact source and lock hashes; preserve old bundles. Run the existing frozen self-test and targeted checks for each capability advertised in the package. Model/STT/browser dependencies remain explicit prerequisites.
5. Run on a fresh standard Windows account or dedicated machine without the repository/developer toolchain on PATH. Use fresh account-owned data; DPAPI data from the developer account is not assumed portable.
6. Keep product versioning separate from guide numbers. If shipping a new release, choose a real candidate version and propagate it through project metadata, executable resources and manifests. Only an honestly established prior released version and new candidate can close the formal cross-version gate. Preserve the same-version artifact rehearsal as its own result.
7. Test offline backup, candidate migration and rollback to a new restored root with both actual bundles. Invalidate old approvals/intakes; never replay possible effects or downgrade a live database in place.
8. Export sanitized evidence and update capability claims. Package qualification may be narrower than the overall project vision; every omitted or blocked gate remains explicit.

**Exit:** a reproducible folder candidate with exact supported scope, current-source reliability evidence, account/device limitations and a clear release decision. Public distribution, installer work and broader application coverage are separate increments.

## 10. Verification entry points

Run from the project root in the existing environment. These are planned commands, not results from preparing this guide. Use a new output name on every repeat. Inspect live runner arguments and prerequisites before real-window, audio, soak or package execution.

```powershell
backend/.venv/Scripts/python.exe scripts/capture-source-manifest.py --output-directory .local/v40-start-01
backend/.venv/Scripts/python.exe -m pytest backend/tests --basetemp=.local/v4-regression-01 --junitxml=.local/v4-regression-01.xml
npm --prefix dashboard test
npm --prefix dashboard run lint
npm --prefix dashboard run build
```

Use focused existing tests during implementation: `test_uia_profiles.py`, `test_notepad_workflow.py`, `test_native_http_review.py`, `test_workflow_api.py`, `test_research_admission.py`, `test_command_admission.py`, `test_command_execution.py`, `test_reviewed_voice_commands.py`, and `test_packaging_release.py`. A final regression is required after final implementation changes.

After confirming that the installed profile still matches, the first native run is:

```powershell
backend/.venv/Scripts/python.exe backend/tests/live/workflow_qualification.py notepad --data-dir .local/v41-native-one-01 --repetitions 1 --profiles config/applications/notepad-win11-11.2607.14.0.json --profile notepad-win11-11.2607.14.0 --encoding utf-8
```

Only after success, repeat in a new root with `--repetitions 20`. Separately qualify native HTTP approval; this workflow runner alone does not prove that path.

```powershell
backend/.venv/Scripts/python.exe backend/tests/live/v34_research_qualification.py --output .local/v42-browser-one-01
backend/.venv/Scripts/python.exe backend/tests/live/m7_soak.py --seconds 7200 --require-ready --fail-fast --output .local/v45-soak-01
```

Inspect benchmark model/digest arguments against the actual installed model before running. For packaging, use the existing scripts' `OutputDirectory`, build `WorkDirectory`/`SourceManifest`, self-test `Bundle`, and pair `PriorBundle`/`CandidateBundle` parameters with fresh paths. Capture final inventories after generated contracts are stable; compare before and after qualification to detect drift.

## 11. First implementation handoff and definition of done

The first implementation batch should complete V4.0 and diagnose one V4.1 native attempt. Deliver the reconciled matrix, starting inventory, exact failing ownership boundary and the smallest evidence-supported fix or ownership design. Complete native checks before enabling that profile. Independently progress browser qualification when resource conditions permit.

For every stage record changed files, rationale, exact tested source, commands/results, isolated roots, artifact hashes, manual interventions and remaining limitations. Keep raw user content, audio, credentials, native trees and private machine logs out of exported evidence.

v4 implementation is complete only when its selected capabilities satisfy the stated gates, or its scope is explicitly revised with unfinished requirements preserved. A safe blocked result demonstrates correct blocking; it does not complete the requested workflow. A written plan completes this planning request, not the implementation milestones above.
