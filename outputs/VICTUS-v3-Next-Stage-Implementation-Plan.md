# VICTUS v3 — Next-stage implementation plan

Prepared: 18 October 2026, Asia/Calcutta.
Project: `C:\Users\HP\Desktop\Automations\victus`.
This is an implementation guide. No production implementation or live qualification was performed while preparing it.

## 1. What we are building next

Turn the existing execution foundation into a usable, narrowly capable assistant:

1. Finish the remaining native Notepad launch, Save and approval integration.
2. Let the dashboard submit a supported checklist and display its actual progress and result.
3. Admit a bounded browser research workflow through the same task service.
4. Connect the existing local model and LangGraph components to a narrow text-command entry point.
5. Connect reviewed speech to that same command path, then qualify and package the resulting scope.

Example end result: type “Create a Notepad checklist with these three items and save it as study.txt.” VICTUS identifies the supported workflow, confirms any missing details, targets its owned blank editor, shows the exact Save preview, waits for approval, saves once, verifies the destination and contents, and reports the evidence. Unsupported requests produce an explanation or clarification.

The immediate next implementation is **V3.1: finish native ownership/Save and V3.2: connect real approval authority**. Later stages depend on their relevant capability gates.

“v3” names this next guide; it does not change the application's current `0.1.0 candidate` version.

## 2. What is already there

The referenced chat's two pages were reviewed, together with the original roadmap, v2 guide, current source and milestone records. The earlier preference still applies: file responsibilities, key logic and checks, without full source listings.

| Area | Current inspected position | Next action |
| --- | --- | --- |
| Dispatcher, durable queue/events and Stop | V2.1–V2.3 implementation is present | Preserve and regression-check |
| Notepad UIA profile | Installed-version candidate; native workflow unqualified | Diagnose and qualify its owned launch/Save path |
| Checklist transport | `POST /api/workflows/notepad-checklist` exists | Complete native review wiring before enabling |
| Production capability registration | Bootstrap registers the note tool; native admission is gated | Keep server-owned qualification gates |
| Dashboard | Existing note, tasks, approvals, health, voice and memory screens | Extend workflow controls and readiness information |
| Browser research | Workflow and supervised localhost runner exist | Qualify, then add narrow task-service admission |
| Local reasoning | Gateway, strict parser, bounded graph and benchmarks exist | Integrate and qualify against admitted capabilities |
| Voice and packaging | Existing implementation and earlier evidence | Connect narrowly and requalify changed scope |

The latest V2.5 record reports **727 backend tests and 20 frontend tests**, build/lint and a source note/API/Stop check. Those are recorded earlier results, not tests rerun for this plan. An isolated native Save succeeded earlier, but the supervised workflow remains unqualified. The old packaged executable does not establish qualification of the current dirty source tree.

The original v2 guide called task-service admission V2.6 and native qualification V2.7. The repository combined transport work into its V2.5 milestone. Follow the actual remaining behavior, rather than recreating an endpoint to match old numbering.

## 3. Implementation order

| Stage | Deliverable | Dependency |
| --- | --- | --- |
| V3.0 | Current baseline and explicit capability gates | First |
| V3.1 | Stable supervised native Notepad path | V3.0 |
| V3.2 | Exact-action native approval and enabled narrow API | V3.1 plus approval tests |
| V3.3 | Dashboard checklist submission and readiness | V3.2 for native release; disabled UI can precede it |
| V3.4 | Qualified browser research task path | V3.0; independent of native blocking |
| V3.5 | Bounded text-command routing and planning | Only individually qualified tools |
| V3.6 | Reviewed voice commands and release qualification | V3.5 and physical audio checks |

Before each stage, write its milestone guide; inspect existing code; make the smallest extension; run relevant checks; record evidence and remaining gates. Preserve existing uncommitted work.

## 4. V3.0 — Freeze the starting point

**Files:** add `docs/milestones/V3-progress.md`; maintain `docs/supported-workflows.md`; inspect `docs/milestones/V2.4-notepad-qualification.md`, `V2.5-checklist-workflow-api.md` and their evidence JSON.

- Record Git base, dirty-file inventory and a content manifest of the exact tested source, config, generated contracts and lockfiles.
- Record which runtime roots are isolated tests and which, if any, belong to the real user. Use fresh test roots; preserve existing runtime data.
- Separate capability states: implemented, unavailable, awaiting qualification, enabled and temporarily blocked by resource pressure.
- Capture the original note workflow, duplicate-request replay, authenticated snapshots/events and Stop as the regression baseline.
- Keep current dependency locks. Dependency upgrades are separate work unless a measured blocker requires one.

**Exit:** the current supported behavior and all disabled capabilities are explicit. No previous test count is presented as a new run.

## 5. V3.1 — Finish native Notepad qualification

**Inspect/extend:**

| File or folder | Responsibility |
| --- | --- |
| `backend/victus/adapters/uia/applications.py` | Establish and retain exact launch/process/window ownership |
| `backend/victus/adapters/uia/native.py` | Native process leases and UIA interaction |
| `backend/victus/adapters/uia/selectors.py` | Unique scoped editor/dialog/control resolution |
| `backend/victus/adapters/uia/actions.py` | Empty-editor, actionable-target and readback guards |
| `backend/victus/workflows/create_notepad_checklist.py` | Supervised steps, Save postconditions and exact file proof |
| `config/applications/notepad-win11-11.2607.14.0.json` | Existing pinned candidate; re-inspect if installed version changed |
| `backend/tests/live/uia_profile_probe.py`, `workflow_qualification.py` | Native diagnostic and supervised workflow entry points |

**Key logic:**

1. Add bounded phase diagnostics around launch, editor resolution, text write/readback, dialog resolution, filename commitment, Save dispatch and verification. Record stable identifiers, timings and error codes; keep raw native trees private.
2. Reproduce one failed supervised run. Compare the successful isolated filename-host operation with the real worker route. Process reuse and uncertain Save are observed blockers; their root causes are still to be established.
3. Resolve only a proven newly owned process/window/editor. Background process reuse must remain blocked unless a new route independently proves ownership. Do not select an existing document by title, close all Notepads, change global session settings or weaken the empty-editor guard.
4. Keep the observed filename host, encoding and newline rules under verification. Re-read the committed destination and editor immediately before Save; after Save, check exact destination, bytes and UI state.
5. If Save may have happened but proof is missing, retain an unknown effect and reconcile read-only. Do not automatically repeat it.

**Acceptance:** one successful supervised run first, then 20 successful native repetitions with unique destinations. Add two-window, nonempty-editor, stale-process, missing-control, denied/expired Save, existing destination and Stop cases. Verify no wrong-target writes, no overwritten originals and no false success. Test intended physical display scales and record measured DPI; simulated scaling is separate evidence.

If one run still fails, keep the profile disabled and document the exact failing boundary. Browser work can continue independently; native capability stays gated.

## 6. V3.2 — Wire native Save to real approval authority

**Inspect/extend:** `backend/victus/safety/{approvals,permits,previews}.py`, `backend/victus/agent/services.py`, `backend/victus/tools/{desktop,steps,dispatcher}.py`, `backend/victus/workflows/{common,create_notepad_checklist,contracts}.py`, `backend/victus/tasks/service.py`, `backend/victus/api/routes/{approvals,workflows}.py`, and `backend/victus/bootstrap.py`.

Reuse the existing approval records and permit lifecycle. The qualification runner currently constructs local authorization; that is insufficient evidence for a native HTTP user-review flow.

**Required behavior:**

- Prepare the exact Save intent after resolving the owned target and requested payload.
- Bind review to task/action identity, tool/version, profile/target identity, destination, payload hash and expiry.
- Persist a waiting-for-review state and event. Use existing approval routes to approve once or deny.
- Design a bounded worker-owner handoff: keep native references in their owning worker, pass opaque authority identifiers, and prevent a second mutation worker from entering. Document this lifecycle before implementation.
- On approval, revalidate the target, payload, destination, cancellation state and expiry immediately before consuming authority and dispatching Save.
- Target changes, payload changes, timeout, Stop and restart invalidate stale authority. Restart never automatically repeats a possibly applied Save.
- Register the native capability only when both native qualification and end-to-end review wiring pass. A client cannot assert qualification or approval.

**Acceptance:** authenticated submit → queued/running → exact review → approve once → verified artifact. Also prove deny, expiry, reused approval, changed target/text/path, disconnect, restart and Stop. Generic `/api/tasks` must enforce the same gate. An uncertain network response retries the same request identity without another effect.

## 7. V3.3 — Make the checklist usable in the dashboard

**Extend:** `dashboard/src/features/commands/CommandInput.tsx`, `features/tasks/{TaskWorkspace,TaskTimeline,TaskResult}.tsx`, `features/approvals/ApprovalPanel.tsx`, `features/health/HealthPanel.tsx`, `dashboard/src/api/client.ts`, and existing generated API contracts. A separate `ChecklistForm.tsx` is a proposed new component if that keeps the existing note form simple.

- Offer the existing note action and the qualified checklist action as clear choices.
- Accept bounded checklist items and a new `.txt` basename. Resolve trusted profiles server-side; do not expose executable paths or selectors as user configuration.
- Show a clear unavailable reason when native qualification is missing. Add a read-only server capability response if the existing health/transport lacks this detail; do not infer readiness merely from HTTP health.
- Display actual queued, running, review, verified, failed, cancelled and unknown states from persisted backend state/events.
- Show literal preview text, destination, expiry and approval status. Keep Stop available during work and review.
- Preserve request identity on uncertain retries, replay events on reconnect and never submit work on refresh.

**Acceptance:** keyboard-only review/Stop, mobile layout, reduced motion, text rendered safely, expired session, refresh during review, reconnect, duplicate click, unavailable profile and verified result. Extend frontend tests and browser contracts for these behaviors.

## 8. V3.4 — Admit bounded browser research

**Inspect/extend:** `backend/victus/workflows/browser_research.py`, `workflows/qualification.py`, `adapters/playwright/`, `workflows/contracts.py`, `api/routes/workflows.py`, `tasks/service.py` and `bootstrap.py`.

Start with the existing localhost fixture workflow: visit explicitly reviewed source URLs, collect a required count of distinct source observations, and save a new report with source identities and hashes. Preserve what its current verifier actually proves; model-written summaries require separate claim-to-source checks.

- Add a strict browser workflow request only after reviewing the current contract. Reuse the queue, dispatcher, ledger, approvals, Stop and new-destination checks.
- Keep session/profile ownership, network scopes, redirect checks, download/upload restrictions and private-address handling server-owned.
- Distinguish fixture-only support from public-web support. Public use needs a separately reviewed scope and live qualification.
- Treat page content as untrusted observations. It cannot approve actions, change scope or introduce executable instructions.
- Unknown page layouts or missing sources return partial/failed outcomes. Do not fabricate a completed report.

**Acceptance:** required distinct sources and exact report verification; allowed redirect; blocked scope escape; stale target; timeout; cancellation; duplicate request; destination conflict and absent browser prerequisite. Then qualify a small read-only public-site scope separately if that scope is desired.

## 9. V3.5 — Connect bounded natural-language commands

**Inspect/extend:** `backend/victus/agent/{router,graph,state,services,budgets,context,output_parser}.py`, existing graph nodes, `backend/victus/models/`, `tasks/service.py` and API contracts. A narrow `api/routes/commands.py` is proposed only if no existing route serves this purpose. Extend the dashboard command input.

**Flow:** text → validate → determine supported intent → clarify missing values → deterministic workflow or bounded graph → shared dispatch/review → independent verification → result.

- Begin with a deliberately small command set: create a workspace note, create a qualified checklist, and run qualified browser research.
- Deterministic intents use existing workflows. The model proposes within the server-admitted capability set; it does not select arbitrary tool names, executables or shell commands.
- Missing filename, ambiguous application or unclear source scope asks a clarification before effects. Persist clarification identity so resuming cannot duplicate work.
- Reuse the existing graph and checkpoint lifecycle; avoid a second scheduler. Keep request/token/time/action budgets and no-progress limits bounded and durable across review pauses.
- Pin the actual installed local model identifier and record its configuration. Confirm readiness/resource pressure; preserve local-first behavior and existing explicit cloud consent.
- Finish only after every requested effect has verifier evidence. A fluent model response is insufficient.

**Acceptance:** rerun the existing full 30-goal benchmark unchanged. The baseline record reports 19/30, below its 27/30 gate. Keep failed and unavailable categories visible; a smaller supported-intent benchmark may supplement, but cannot replace or relabel, the full result. Add adversarial instructions, invalid model output, planner timeout, ambiguous commands, Stop during planning/review and crash recovery.

## 10. V3.6 — Reviewed voice and release qualification

**Extend only gaps:** `backend/victus/voice/`, `api/routes/voice.py`, `dashboard/src/features/voice/VoicePanel.tsx`, `evaluation/voice/`, existing reliability/packaging scripts and release records.

- Route a reviewed transcript through the same supported text-command path. Keep edit/confirm before task submission.
- Prove microphone ownership, disconnect handling, STT cancellation, Stop and assistant-speech suppression with real devices.
- Run the planned 50 quiet and 50 noisy labelled commands; separately measure recognition and end-to-end correct actions. Do not imply Hindi/mixed-language support without corresponding evidence.
- Speak only an accurate final status; avoid reading private text by default. Voice recognition never acts as Save approval by itself.
- Keep custom wake disabled until its separate model/corpus gates pass. Optional MCP/cloud work remains separately gated.
- Run a fresh reliability soak on the final source, rebuild the folder package and rerun package self-tests. Preserve old package evidence as historical.
- Complete fresh standard-account testing and an actual prior-release upgrade/rollback pair before declaring release qualification.

**Exit:** publish a capability matrix naming exactly what passed in source, on this laptop, in the package and on any public sites. Unqualified optional features remain unavailable.

## 11. Verification commands

Run from the project root. These are proposed commands, not results from this planning session. Select fresh output directories on repeat runs. Native commands operate real windows and belong in a deliberate supervised qualification session.

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_workflow_api.py backend/tests/test_notepad_workflow.py backend/tests/test_uia_profiles.py backend/tests/test_approval_dispatch.py backend/tests/test_approvals.py --basetemp=.local/v3-focused-01
backend/.venv/Scripts/python.exe -m pytest backend/tests --basetemp=.local/v3-regression-01 --junitxml=.local/v3-regression-01.xml
npm --prefix dashboard test
npm --prefix dashboard run lint
npm --prefix dashboard run build
```

Inspect current native runner arguments and installed profile identity first. After that review, the existing one-run entry point is:

```powershell
backend/.venv/Scripts/python.exe backend/tests/live/workflow_qualification.py notepad --data-dir .local/v3-native-one-01 --repetitions 1 --profiles config/applications/notepad-win11-11.2607.14.0.json --profile notepad-win11-11.2607.14.0 --encoding utf-8
```

Only after that succeeds, use a fresh directory and `--repetitions 20`. This runner qualifies the supervised native workflow; separately exercise the HTTP approval path. Inspect structured status and verified output, not just command completion.

The existing browser fixture runner is:

```powershell
backend/.venv/Scripts/python.exe backend/tests/live/workflow_qualification.py browser --data-dir .local/v3-browser-01 --repetitions 1
```

Inspect model benchmark, soak and package script arguments at their respective stages. Run targeted checks after each change, then a complete regression for the final candidate.

## 12. Definition of done and first handoff

For every stage record: files changed and why; exact tested source identity; deterministic results; laptop/native results; public-site results if applicable; remaining gates. Keep raw tokens, user text, machine-specific native trees and private logs out of shared evidence.

**First implementation handoff:** complete V3.0 and V3.1, then V3.2. Preserve the current typed-note path and native admission gate. Deliver a reproducible owned Notepad workflow and exact-action approval evidence before enabling the dashboard's native action. If native ownership or Save remains unresolved, report the specific boundary and keep that capability unavailable while progressing the independent browser stage.

The full next-stage outcome is a small, verified assistant reachable through structured forms, bounded text commands and reviewed speech, with each capability enabled only by its own evidence.
