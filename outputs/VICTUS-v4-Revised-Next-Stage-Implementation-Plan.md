# VICTUS v4 — Revised next-stage implementation plan

Prepared: 19 October 2026, Asia/Kolkata.
Repository: nithishgoud1912/victus.
Inspected branch: main.
Inspected commit: e87b1050217d342551aa1c43da37e2add276336e.
Scope: all 48 tracked Markdown files, existing V3/V4 plans, current milestone/evidence records, and selected implementation files.
Companions: [Markdown audit](VICTUS-v4-Markdown-Audit.md) · [Implementation checklist](VICTUS-v4-Revised-Build-and-Verification-Checklist.md).

This is a revised V4 implementation handoff. It preserves the original V4 plan and its numbering. It does not claim new application tests, Windows runs, model inference, recordings or package qualification. The repository already contains part of V4; complete and verify that work before expanding the product. The application version remains 0.1.0 unless a separate product-version decision changes it.

## 1. What we are building next

Deliver a dependable local assistant through the paths already designed:

1. Type a supported note command, clarify missing details and receive an independently verified file.
2. Submit a checklist through the dashboard or a reviewed command, use a newly owned empty Notepad tab, approve the exact Save once and verify the native result.
3. Request research from the bundled source catalog and receive a verified report with distinct source evidence.
4. Use a pinned local reasoning model for supported phrasing after measurement, while deterministic commands remain usable without it.
5. Submit reviewed English speech through the same command service and measure recognition separately from corrected actions.
6. Package the qualified scope with current-source reliability and deployment evidence.

Immediate work: V4.0 refreshes the actual baseline; V4.1 completes the existing tab/Save work; V4.2 finishes qualification and production admission for fixture research. Native and browser work can proceed independently after the shared baseline. Avoid another round of rebuilding the queue, graph, dashboard, approval system or voice pipeline: they already exist.

Example final path: “Create checklist study.txt with items [\"Read\", \"Practice\"]” → saved command → one task → owned Notepad/new empty tab → literal Save preview → explicit approval → one Save attempt → exact file/UI verification → verified result. An unknown Save remains unknown, with a separate read-only reconciliation outcome.

## 2. What the repository actually contains

### Current evidence and its limits

| Area | What exists | Remaining V4 work |
| --- | --- | --- |
| Execution foundation | Shared dispatcher, durable one-active/three-pending queue, atomic events, request replay, spawned supervision and Stop | Fresh final-source live baseline; preserve these boundaries |
| Commands/dashboard | Protected intake, durable clarification, bounded graph, forms, capabilities and refresh/reconnect behavior | Real production-path tests for each newly admitted capability |
| Notepad ownership | Pinned candidate, owned-child binding, diagnostics and newly added tab/window lease | Validate the latest lease; diagnose Save; complete native and HTTP/dashboard qualification |
| Qualification records | Runtime-bound fixture/native loaders, native bootstrap wiring and fixture promotion already present | Harden validation, report provenance and frozen-runtime qualification; add missing native promotion workflow |
| Browser runner | Twenty-run structured/text fixture runner now present | Fix evidence/error-path gaps and measure real runs under normal memory policy |
| Reasoning | Strict gateway/parser, bounded planning, exact model settings | Establish current installed reasoning pin and rerun the frozen benchmark |
| Voice | Capture/STT/review/CommandService/SAPI and separate action evaluator | 50 quiet + 50 noisy real recordings and witnessed physical checks |
| Reliability/package | Readiness preflight fix, historical soak, source capture and folder-build tools | New final-source soak, new bundle, fresh standard-account test and honest release decision |

The latest checked-in V4 summary records 804 backend and 23 frontend passes for its named implementation inventory, not a new run on every later addition. The current tree includes continuation work such as qualification_records.py, fixture_qualification.py and the tab lease. Capture and test this exact tree before carrying those counts forward.

The latest V4 evidence records the extended 23-check live baseline blocked by RAM pressure, native Save unknown, browser admission blocked, no current reasoning pin, no labelled voice trials, no new-source package and no completed current-source soak. These are historical observations of the laptop; this planning session did not measure its current RAM, app installation or model cache.

### Corrections to earlier plans

- V3.6 evidence is present. The original V4 plan's missing-file observation is historical.
- Native cold-launch child binding has succeeded. “Missing owned child” is not the only remaining native problem; Save/window transitions and restored documents matter.
- A new tab inside the proved owned child is implemented and has two focused tests. Review and extend it rather than implementing it again.
- Native record loading and bootstrap registration are present. Complete their proof and promotion path rather than adding duplicate registration.
- The browser runner now defaults to 20 repetitions and alternates structured/text routes. Its existence does not establish 20 successful runs.
- The historical full model score is 19/30 against a 27/30 gate. Later zero-executed unavailable attempts have no measured accuracy.
- The older 7,200-second M7 soak qualifies its old source. It does not qualify the current V4 tree.
- V3/V4 guide numbers and two schema-different 0.1.0 artifacts do not establish different released product versions.

## 3. Implementation sequence

| Stage | Deliverable | Completion dependency |
| --- | --- | --- |
| V4.0 | Current-source inventory, reconciled documentation and passing real baseline | First |
| V4.1A | Proven new-tab ownership and diagnosed Save transition | V4.0; no broad native admission |
| V4.1B | Native evidence, real HTTP/dashboard review and trusted promotion | V4.1A and all native gates |
| V4.2A | Robust browser reports and qualification-record validation | V4.0; independent of Notepad |
| V4.2B | Twenty real fixture successes and production admission | V4.2A plus real resource readiness |
| V4.3 | Installed-model pin, measured interpretation and unchanged benchmark | V4.0; desktop success depends on qualified native capability |
| V4.4 | Labelled reviewed speech and witnessed device behavior | Qualified note path; other intents need separate corpus/verifiers |
| V4.5 | Final regression, soak, frozen qualification and package decision | Selected implementation scope frozen |

For each stage, write the measured problem, intended edits and acceptance cases in a milestone before changing production code. Preserve current locks and prior runtime/package roots. Use a new isolated root for each qualification attempt.

## 4. V4.0 — Refresh evidence and restore an executable baseline

**Inspect/extend:**

| File | Responsibility |
| --- | --- |
| scripts/capture-source-manifest.py | Full implementation/config/contracts/locks and dirty inventory |
| scripts/reconcile-v36-evidence.py | Existing historical reconciliation |
| docs/milestones/V4-progress.md | Append current continuation and actual outcomes |
| docs/supported-workflows.md | Current capability matrix, followed by clearly historical sections |
| backend/tests/live/v3_baseline.py | Existing 23-check real HTTP/SSE baseline |
| README.md, dashboard/README.md | Current navigation, setup and implemented feature descriptions |

**Key logic:**

1. Capture current commit, dirty files and hashes before implementation. Keep the full source manifest and runtime_identity digest separate: the latter currently hashes runtime Python only.
2. Build a source/evidence table naming the exact inventory for each result. Existing private .local reports are not in this clone; checked-in summaries are available, but raw reports must be marked unavailable here.
3. Record current resource availability in the actual Windows session before tests. Preserve the 2 GiB memory guard and 64 MiB mutation disk guard. Diagnose VICTUS-owned overhead or leaks from measurements. Closing unrelated programs belongs to the user; do not lower guards to manufacture success.
4. Run the existing baseline with normal telemetry: auth, exact note bytes, command graph, clarification, original request replay, passive refresh/SSE replay and Stop/no later effect.
5. Correct README/dashboard claims that task screens remain future work or that only note-field voice intake exists. Link the current matrix and relevant milestones. Keep setup instructions, token handling and explicit optional-asset configuration.
6. Fill M0-feasability.md with a current feasibility record: hardware target, implemented paths, Windows-only checks, measured constraints and unresolved capabilities. Keep historical results labelled. Add concise M6/M7/M8 milestone index entries only where useful; their implementation already exists under evaluation/.
7. State the selected V4 scope and unresolved inherited gates explicitly. A narrower usable note candidate can be delivered while full V4 remains incomplete.

**Acceptance:** fresh source-bound 23-check live baseline passes; reads/replay cause no extra effect; native/public capabilities remain unavailable without their evidence; current docs agree with source. Resource-blocked runs are retained as blocked and do not satisfy this exit.

## 5. V4.1A — Complete the existing Notepad tab lease and Save path

**Inspect/extend:**

| File | Responsibility |
| --- | --- |
| backend/victus/adapters/uia/applications.py | ApplicationProfile, UIAWorker.launch, _editor_tabs, _create_empty_editor, _resolve_app |
| backend/victus/adapters/uia/native.py | Native process identity, COM ownership and bounded diagnostics |
| backend/victus/adapters/uia/selectors.py | Exact scoped window/control/runtime-ID matching |
| backend/victus/adapters/uia/actions.py | Value/Invoke, empty-editor checks and immediate final guards |
| config/applications/notepad-win11-11.2607.14.0.json | Current owned-child/new-tab candidate; re-inspect if installation changed |
| backend/victus/workflows/create_notepad_checklist.py | Step ordering, filename commitment and independent Save verification |
| backend/victus/workflows/native_review.py | Single owner and exact-action Save review |
| backend/tests/test_uia_profiles.py, test_notepad_workflow.py | Focused ownership, transition and exact-artifact cases |

### Finish the lease before testing Save repeatedly

The new code invokes AddButton, requires one new tab, retains old tab identities and checks selected tab/window identity on subsequent application resolution. That is useful progress. It is still unqualified and must be exercised against the installed app.

Extend tests for: no new tab, duplicate new tabs, no selected tab, two selected tabs, changed window identity, removed/replaced tab, foreign-process tab, missing/ambiguous container, timeout, cancellation, nonempty new editor and selection change while approval waits. The new editor must be independently proved empty immediately before SetValue. Observing a newly created process or tab does not prove empty content.

Add explicit Stop/deadline checks to any bounded new-tab polling/effect boundary where inspection shows they are absent. New-tab creation is itself an app effect; record it within the launch operation's ledger/diagnostics and preserve an unknown/partial outcome if interrupted. Do not silently hide an extra desktop mutation in a read-only helper.

Retain owned-child process proof, pinned executable, COM thread/worker ownership and no keyboard fallback. Leave pre-existing tabs and unsaved documents intact; cleanup cannot terminate shared or restored user work. Do not change global restoration settings.

### Diagnose the real Save transition

1. Capture source identity and the current installed executable/profile hash.
2. Run one supervised attempt in a new workspace. Record bounded process/window/tab/control identities and safe phase codes before/after menu opening, dialog creation, filename commitment, Save and postcondition reacquisition.
3. Determine whether the same main window survives, the modal hierarchy changes, the tab identity changes, or Save never creates the expected file. These are hypotheses until observed.
4. Fix only the demonstrated boundary. Reacquire changed controls from the still-valid owned editor/document lease; do not solve ambiguity with first-match selection or dynamic titles.
5. Re-read the exact committed path, payload and current target after review and immediately before Save. Preserve expiry, single-use permit and cancellation checks.
6. Independently verify exact bytes, encoding/newlines and the native UI postconditions. The file alone cannot prove that an overwrite dialog is absent or the intended document was saved.
7. If proof fails after possible Save, retain unknown and reconcile the exact requested destination read-only after the owner is quiescent. A missing destination does not prove no other effect occurred and cannot authorize an automatic retry.

**Exit:** one full native workflow succeeds on current source with exact artifact and native UI proof. Only then start repetition/adversarial campaigns. An unresolved first run keeps native registration disabled.

## 6. V4.1B — Qualify native review and complete trusted admission

**Extend existing:** workflows/qualification.py, workflows/qualification_records.py, bootstrap.py, native_review.py, api/routes/workflows.py, tests/test_qualification_records.py and tests/test_native_http_review.py.

The native loader is present and requires >=20 verified runs, all NATIVE_CHECKS, matching runtime/profile/executable and two physical DPI values. A validated native-report producer/promotion command is still needed: the existing generic Notepad repetition report is not that complete native admission record.

**Build:**

1. Add a native qualification-session runner that combines supervised repetitions, actual native negative cases, two intended physical scales, real authenticated HTTP review and dashboard observations. Preserve per-case report identities.
2. Keep CLI/local maintenance promotion separate from public HTTP. Derive checks from validated reports; do not accept a bare dictionary of claimed pass booleans as sufficient evidence.
3. Validate report kind/schema, exact booleans/integers, source identity before/after, profile/executable hashes, run count, unique destinations, expected artifact hashes and case coverage. Validate no-overwrite publication and retain the source reports' exact hashes.
4. Bind review to the selected tab/document lease as well as process/window/control, task/action, tool/policy version, destination, editor hash and expiry. Confirm the current binding actually includes the new tab identity; add it if missing.
5. Prove one active native owner remains through review and another mutation cannot enter. Deny, expiry, disconnect, Stop and restart must not create fresh authority.
6. Enable only the exact installed profile once native and real review gates both pass. Generic tasks, structured workflow submission and text/voice commands must share the same gate.

**Acceptance:** >=20 unique-destination native successes on unchanged source; real two-window/restored/nonempty/stale/missing-control/changed-target cases; denied/expired/reused approval; changed payload/path; destination conflict; Stop during review/Save; restart invalidation; both actual physical display scales; real HTTP/dashboard approve-once Save. Simulated tests supplement these runs.

**Exit:** trusted admission after restart and a new production-path native request succeed. If any required case remains open, native remains unavailable with its accurate reason.

## 7. V4.2A — Finish browser evidence and record validation

**Inspect/extend:** workflows/fixture_qualification.py, fixture_research.py, qualification_records.py, cli.py, tests/test_qualification_records.py, test_research_admission.py and relevant browser tests.

The runner now alternates 20 structured/text requests and checks replay, sources, conflicts, scope, Stop and cleanup. Keep this implementation.

### Measured code-review gaps

| Current behavior | Required change |
| --- | --- |
| Chromium startup/path discovery occurs before the runner's main protected block; final report generation unconditionally reads executable bytes | Always produce a bounded blocked/failed report for missing binary, startup errors and hashing errors; unknown hashes remain null |
| The timeout case treats any exception from a 1 ms launch as a timeout pass | Prove the intended deadline and terminal cleanup; distinguish unavailable dependency, unrelated launch error and actual timeout |
| Cleanup compares all matching browser/driver processes with a global pre-run inventory | Attribute cleanup to VICTUS-owned process identities; unrelated user launches must not authorize termination or create false leak conclusions |
| Qualification uses TestClient with real browser/worker effects and injected trusted wiring | Label it accurately; add separate real loopback HTTP/SSE and production-bootstrap tests after promotion |
| Record checks largely depend on declared booleans and counts | Validate distinct destinations, per-run receipts/artifacts, route coverage, strict types and exact source/report bindings before promotion |
| Native loader has little positive/end-to-end coverage | Test valid native loading, every stale/malformed identity and bootstrap admission/refusal |

Report generation must survive failure and cleanup errors without replacing the primary boundary. Each artifact should bind task/action references, final URLs/text hashes, exact report hash and verified ledger proof. Preserve real resource samples.

Test promotion with valid complete synthetic report structures and isolated artifacts, then mutations: 19 runs, repeated destination, failed receipt, absent artifact, wrong hash, missing text route, missing cleanup, wrong engine/profile, changed runtime, non-boolean checks and existing record. These validate evidence plumbing; real qualification still requires actual runs.

**Exit:** every unsupported prerequisite or interrupted run has a useful report; partial/stale evidence never enables bootstrap; valid matching evidence can be consumed through the intended local workflow.

## 8. V4.2B — Qualify fixture research and prove production operation

1. Confirm real Windows available RAM, disk and matching Chromium/Playwright prerequisites. Preserve normal guards and current locks.
2. Run one smoke attempt, then a fresh 20-run campaign. The existing --repetitions option supports this.
3. Require 20 exact verified reports with unique destinations, distinct final sources and hashes, both routes, identity-preserving replay and owned cleanup. Redirect-a and source-a count as one source.
4. Exercise scope rejection, downloads/popups/uploads restrictions, missing binary, actual timeout, interrupted worker and no new effect after Stop. A previously committed artifact is not claimed to be undone.
5. Run existing adversarial browser probes where they cover freshness, duplicate targets, forbidden redirects and observation isolation. Keep their scope explicit.
6. Promote only the complete current-runtime evidence using the existing local promote-fixture command, then restart.
7. Start an ordinary configured backend, without test-only registry injection. Through a real authenticated socket, prove capability reporting, structured submission, text command, task/SSE replay, exact output and Stop.
8. Repeat the dashboard flow for visible result, unavailable/pressure states, duplicate click, refresh and keyboard Stop.

**Exit:** bundled research is enabled for precisely the qualified fixtures. No arbitrary URL/public-site capability is implied.

Public research is a later scoped increment: define a server-owned HTTPS catalog, destination/redirect policy, bounded observation and claim-to-source verification, then qualify those sites separately. Preserve the existing network mediator's documented compatibility limits. Do not broaden the current source-ID request into arbitrary browsing to make the demo look more capable.

## 9. V4.3 — Pin local reasoning and improve measured failures

**Files:** settings.py, models/{contracts,gateway,ollama}.py, agent/{commands,command_execution,router,context,output_parser,budgets,benchmark}.py, tasks/commands.py and the existing sample/benchmark runners.

1. Inventory actual installed Ollama/runtime/assets on Windows; historical embedding-only results may have changed. Record exact model name/digest, context/output options, runtime version and measured resource use.
2. If no reasoning model exists, record that prerequisite and deliberately prepare a selected local model before testing. Use the existing Qwen3 4B candidate as the historical comparison when available; do not silently select a cloud model or treat embeddings as reasoning. No model installation is part of this planning task.
3. Use one local reasoning model at a time with existing inference-slot coordination. STT stays CPU/int8. Benchmark measured RAM/VRAM and latency on the 16 GB RAM/6 GB GPU target; do not promise that every quantization/context combination fits.
4. Set both command-model name and digest from the verified installed pin. Keep deterministic note/templates usable without inference.
5. Run the six structured-output samples, then diagnose actual command failures. Preserve strict JSON parsing, closed tool catalog, exact confirmed arguments, one repair per decision within shared budget, Stop, clarification and independent verification.
6. Rerun all 30 frozen goals unchanged. Preserve suite hash 1a23540e729f3b62f9e0991fd7c53d6cd6e279a514f45f1e4a697949a273e340 and 27/30 gate. Native prerequisites must genuinely be qualified for native successes.
7. Diagnose the historical two-file F06 failure and any new errors from retained outcomes. Changing benchmarks or dropping desktop goals cannot improve the full score legitimately.
8. Add a separate held-out supported-command phrasing set, including ambiguity, prompt injection, missing values and invalid paths. Report it separately from the 30-goal result.

**Acceptance:** real pinned inference, safe structured output, exact admitted argument preservation, bounded time/resource use, no false success and full benchmark accounting. A run with zero executed goals has no accuracy score. A deterministic note candidate may remain usable while the broader model gate remains open.

**Exit:** reproducible model evidence and correct scope labels. Broad planning qualification requires the original gate; it is not implied by a few successful paraphrases.

## 10. V4.4 — Measure reviewed speech with real user trials

**Extend gaps only:** voice/, api/routes/voice.py, dashboard/src/features/voice/VoicePanel.tsx, evaluation/voice/{README,V3.6-protocol}.md and existing evaluation/device runners.

The supported chain already exists: explicit capture → local English STT → editable transcript → explicit confirmation/clarification → CommandService → shared execution → verified generic spoken status. Save approval remains separate.

1. Predeclare recognition and action thresholds before collection. Existing documents specify 50 quiet + 50 noisy trials but do not provide a full numeric accuracy gate; agree/document one before evaluating rather than inventing a historical requirement.
2. Record 100 consented labelled commands plus existing negative conditions. Keep raw recordings/reference text private and unique intended destinations per trial. Split tuning examples from held-out evaluation.
3. Run recognition evaluation on untouched STT output: WER, intent and exact target by condition. Record manual edits/correction rate separately.
4. Pair each recording with its actual reviewed voice-origin command/task and run the independent read-only action evaluator. Preserve its operator-supplied pairing limitation.
5. The existing action protocol is English note-only. Do not count native/browser trials through a verifier that only understands note artifacts; add explicit labels/verifiers and a separate corpus before broadening it.
6. Witness microphone unplug/reconnect, Stop during actual spoken decoding/review/playback, audible mute/interruption, physical shortcut and real speaker echo suppression/cooldown. Flags and silent test audio do not prove these behaviors.
7. Recheck legacy reviewed-note compatibility, stale revision, duplicate confirm, refresh and Stop throughout.

**Exit:** recognition, corrections, verified actions and physical tests reported separately against predeclared thresholds. Missing human participation remains an open gate. Typed qualification and human audio sessions can progress independently.

Custom wake remains a separate optional experiment: qualified local assets, >=100 held-out positives, >=7,200 seconds realistic negatives, recall >=90% and <=1 false activation/hour plus physical handoff. It is not a prerequisite for reviewed push to talk. Hindi/mixed speech, arbitrary MCP and cloud remain outside this V4 scope unless separately selected and qualified.

## 11. V4.5 — Freeze, soak and qualify the folder package

**Files:** existing source-manifest, tests/live/m7_soak.py, scripts/{build-windows,package-self-test,package-upgrade-rollback}.ps1, packaging/windows/, runtime/release.py, docs/release/README.md.

### Final source and reliability

- Freeze implementation/config/locks/generated contracts after edits. Run focused meaningful tests during work, then final backend regression and dashboard tests/lint/build; verify contracts and source do not drift.
- Keep the original two-hour soak gate: >=7,200 seconds, >=100 verified tasks, >=2 backup/restores, <=20% warmed-parent RSS growth, health p95 <0.5 seconds and no recorded failures on unchanged source.
- Use fresh real telemetry and a final report; preflight refusal, progress and short harness checks do not qualify.
- Inspect owned child/browser processes as well as parent RSS. Add a supplemental workload for enabled commands/browser/native review, with deliberate review participation where necessary. Do not auto-approve Save or call a note-only soak “native reliability.”
- Compare source/config/lock identities before and after every campaign. Record interrupted/blocked cases without replacing history.

### Fix source/frozen qualification before advertising package capabilities

Current runtime_identity deliberately distinguishes source Python hashes from a frozen-v1 digest derived from the release source manifest. The spec conditionally copies qualification JSON into the bundle. Therefore a copied source qualification will fail the frozen identity check; bundling it does not enable the capability.

Design and test a package qualification workflow:

1. Build the immutable candidate and capture its bundle manifest/source identities.
2. Test the actual frozen candidate in an isolated Windows runtime.
3. Produce a frozen-bound record with the same native/browser evidence requirements; do not relabel source records or manually change their digest.
4. Define a supported protected record location and maintenance publication route. Current adjacent-module storage may live under _internal in a bundle, while some runtime data must remain outside immutable resources; settle this deliberately.
5. Keep qualification records outside the implementation-source hash to avoid circular identity, while binding them to immutable candidate identity. If shipping them as bundle resources, define how rebuilding changes identities and repeat the required checks.
6. Test missing/stale source/frozen records, changed bundle/config, native profile/browser dependency drift and capability reporting after restart. Source-mode promotion must never qualify a different frozen build.

### Package and deployment

- Build a new complete onedir bundle with fresh output/work paths and exact source/lock metadata; retain prior bundles.
- Run current frozen self-test and targeted package checks for every advertised capability. The default self-test proves core behavior and missing-asset gates; it does not prove GPU inference or acoustic/native/browser operation automatically.
- Test a fresh standard Windows account/dedicated machine without repository/developer executables on PATH. Use fresh account-owned data; DPAPI portability across accounts is not assumed.
- Keep guide numbering separate from product versions. If creating a release candidate, deliberately version metadata/resources/manifests. A formally released prior version and new candidate are needed for formal cross-version qualification; otherwise report that gate deferred.
- Rehearse actual old executable backup, candidate migration and old executable restore into a new root. Invalidate old approval/intake authority; never downgrade a live database in place.
- Export sanitized results and update the capability matrix. Source, laptop, package, fresh account and public-site evidence remain separate columns.

**Exit:** reproducible package with exact demonstrated scope, current-source reliability, frozen capability evidence and a truthful release decision. Full V4 remains incomplete while selected mandatory gates are open.

## 12. Verification entry points

Run from the actual repository root on Windows using its existing environment. These are future commands, not results from this review. Use a new suffix for every retry. Confirm live prerequisites/profile identity before native work.

### Baseline and regression

```powershell
backend/.venv/Scripts/python.exe scripts/capture-source-manifest.py --output-directory .local/v4r-start-01
backend/.venv/Scripts/python.exe backend/tests/live/v3_baseline.py --data-dir .local/v4r-baseline-01
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_uia_profiles.py backend/tests/test_notepad_workflow.py backend/tests/test_qualification_records.py backend/tests/test_research_admission.py backend/tests/test_native_http_review.py --basetemp=.local/v4r-focused-01 --junitxml=.local/v4r-focused-01.xml
backend/.venv/Scripts/python.exe -m pytest backend/tests --basetemp=.local/v4r-regression-01 --junitxml=.local/v4r-regression-01.xml
npm --prefix dashboard test
npm --prefix dashboard run lint
npm --prefix dashboard run build
```

### Native: first success before repetitions

```powershell
backend/.venv/Scripts/python.exe backend/tests/live/workflow_qualification.py notepad --data-dir .local/v4r-native-one-01 --repetitions 1 --profiles config/applications/notepad-win11-11.2607.14.0.json --profile notepad-win11-11.2607.14.0 --encoding utf-8
```

After a complete verified success, use a new root and --repetitions 20. This does not replace real HTTP/dashboard review or physical-scale evidence.

### Browser: smoke, campaign, then promotion

```powershell
backend/.venv/Scripts/python.exe backend/tests/live/v34_research_qualification.py --output .local/v4r-browser-smoke-01 --repetitions 1
backend/.venv/Scripts/python.exe backend/tests/live/v34_research_qualification.py --output .local/v4r-browser-20-01 --repetitions 20
backend/.venv/Scripts/victus.exe promote-fixture --source .local/v4r-browser-20-01/report.json
```

A one-run report is not promotable. Promotion follows V4.2A validation fixes and a complete matching campaign; the command refuses an existing record. Restart and separately test ordinary production bootstrap. Native promotion is proposed work and has no invented existing command here.

### Local model and voice

Use m3_model_samples.py and m3_30_goal_benchmark.py with the actual installed name and digest. Inspect --help and supply fresh output paths. Never blindly reuse a historical digest.

```powershell
backend/.venv/Scripts/python.exe -m victus.voice.evaluation --manifest C:/private-voice/manifest.json --model C:/local-models/faster-whisper-base.en --output .local/v4r-recognition-01.json
backend/.venv/Scripts/python.exe -m victus.voice.action_evaluation --manifest C:/private-voice/manifest.json --bindings C:/private-voice/reviewed-command-ids.json --data-dir C:/private-voice/runtime --output .local/v4r-actions-01.json
```

These voice paths are examples from the existing protocol. Supply actual consented recordings/model/runtime; no corpus is included.

### Reliability/package

```powershell
backend/.venv/Scripts/python.exe backend/tests/live/m7_soak.py --seconds 7200 --require-ready --fail-fast --output .local/v4r-soak-01
./scripts/build-windows.ps1 -OutputDirectory dist/v4r-candidate-01 -WorkDirectory .local/v4r-build-01 -SourceManifest .local/v4r-final-source-01/source.json
./scripts/package-self-test.ps1 -Bundle dist/v4r-candidate-01/Victus -OutputDirectory .local/v4r-package-check-01
```

Capture .local/v4r-final-source-01 before building after contracts stabilize. The build requires the documented pinned packaging environment. Use package-upgrade-rollback.ps1 with actual PriorBundle, CandidateBundle and fresh OutputDirectory paths; no previous release is assumed to exist.

## 13. Definition of done and first implementation handoff

First handoff:

1. Capture the current tree and run the fresh baseline.
2. Verify/extend the implemented Notepad tab lease, reproduce one Save boundary and make the smallest evidence-supported correction.
3. Harden qualification reports/record tests, including failure reporting and frozen identity.
4. Finish browser campaign and ordinary production admission independently when resource conditions allow.
5. Report concrete changed files, exact source identity, command results and unresolved machine/human requirements.

For each stage retain: intended behavior, changed files, full source and runtime identity, fresh data root, case outcomes, artifact/report hashes, manual observations, cleanup result and remaining requirements. Export no raw audio, tokens, private text, native trees or personal runtime logs.

V4 completion requires all selected gates to pass with matching evidence. If choosing a smaller candidate, name that scope and keep inherited unfinished requirements explicit. A correct blocked negative case is valuable evidence; a resource-blocked positive workflow is not a completed requested capability.
