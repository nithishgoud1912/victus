# VICTUS v8 — Next-stage implementation plan

Prepared: 20 October 2026.
Repository: `nithishgoud1912/victus`.
Inspected branch/revision: `main` / `10226a45c3b791fa9a7439ce519db24aa9f89100`.
Theme: **Measured local reasoning and reviewed voice**.
Companions: [Checklist](VICTUS-v8-Build-and-Verification-Checklist.md) · [Full Markdown audit and cross-version roadmap](VICTUS-v7-v8-v9-Markdown-Audit-and-Roadmap.md).

These are proposed implementation stages, not completed work or new validation results. Guide numbers do not change the product version. The inspected repository identifies as a `0.1.0` candidate. No application code, lockfile, generated contract, qualification record or runtime data was changed for this planning request.

**V6 reconciliation is mandatory:** the inspected `main` has merged V5 (PR #10), but no tracked V6 Markdown, V6 remote branch or matching V6 pull request was found. A separate filename search did not resolve a V6 plan. This does not establish that work in another checkout never happened. At implementation start, locate any V6 work, record its actual revision and evidence, and replace overlapping tasks with validation of that work. If unavailable, retain `V6_NOT_RECONCILED`; use the measured V5 baseline below without claiming V6 completion.

The plans split the existing unfinished work into three focused increments: V7 dependable execution, V8 measured local interpretation and reviewed speech, V9 reliability and frozen Windows release. This allocation is a planning decision based on the audit, not an already approved expansion of runtime capabilities.

## 1. What we are building next

Make supported free-form commands and English push-to-talk useful through the existing bounded command path, with one deliberately pinned local model and real recognition/action measurements.

**Entry:** V7 storage/Stop/note foundation and reconciled V6 state. Model samples and note-only voice work can proceed while a separately gated native/browser path is blocked, but those unavailable tools cannot count as successful benchmark cases.

**Expected end state:** One exact local model has real structured-output and frozen-suite evidence; English reviewed-note speech meets predeclared recognition/action thresholds and witnessed hardware gates. Deterministic notes remain usable without a model. Packaging and release still belong to V9.

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
| V8.0 | Freeze the evaluation contract and capability scope | Reconciled V7 baseline; portable preparation |
| V8.1 | Establish one local model pin and resource envelope | V8.0 plus explicitly installed local runtime/model |
| V8.2 | Improve only measured command/planner failures | V8.1 plus admitted tools relevant to each case |
| V8.3 | Complete real reviewed English speech evaluation | Qualified note path plus consented corpus and local STT assets |
| V8.4 | Witness physical audio, Stop and playback behavior | V8.3 preparation; actual Windows devices and human session |
| V8.5 | Validate integrated local resource behavior and UI | V8.1–V8.4 for advertised paths |
| V8.6 | Record V8 evidence and release input | Selected V8 gates complete |

Design and unchecked acceptance cases belong in the proposed milestone before production edits. Existing code paths are reused unless an observed gap justifies an extension. A newly changed runtime invalidates affected earlier qualification.

## 4. V8.0 — Freeze the evaluation contract and capability scope

**Dependency:** Reconciled V7 baseline; portable preparation.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `backend/victus/agent/benchmark.py; evaluation/m3-30-goals-v1.json` | Original frozen 30-goal task benchmark and 27/30 gate. |
| `evaluation/voice/V3.6-protocol.md; backend/victus/voice/qualification_session.py` | Predeclared recognition/action metrics and physical observations. |
| `Proposed docs/milestones/V8-progress.md; docs/V8-TESTS-AND-INCOMPLETE.md` | Evaluation design, exact asset identities and unchanged held-out scope. |

**Key logic:**

1. Inventory which V7 workflows are actually admitted and which are blocked. Freeze the full benchmark and record its hash before inference; retain unavailable cases in accounting.
2. Define a separate held-out supported-intent phrasing set covering missing values, ambiguity, exact-content preservation, hostile content and unsupported requests. Do not replace or blend the original suite.
3. Predeclare latency/resource measurements and voice numeric thresholds before evaluation. Existing WER/intent/target/action fields are independent; record correction rate separately.
4. Keep the corpus bounded to reviewed English note commands. Native Save review remains a separate action even if a future spoken checklist is supported.

**Acceptance / exit:**

- Unchanged benchmark identity, declared voice thresholds and admitted-tool catalog are recorded before scoring.
- No invented accuracy or model ranking appears without measured inference.

## 5. V8.1 — Establish one local model pin and resource envelope

**Dependency:** V8.0 plus explicitly installed local runtime/model.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `backend/victus/runtime/readiness.py; resources.py; settings.py` | Safe inventory, normal guards and explicit model configuration. |
| `backend/victus/models/contracts.py; ollama.py; gateway.py` | Exact local name/digest, provider wire schema and shared bounded requests. |
| `backend/tests/live/m3_model_samples.py` | Six existing live JSON-schema samples with no effect execution. |

**Key logic:**

1. Inspect actual Ollama tags, unique model name/digest and installed settings. A reachable service or embedding asset does not establish a reasoning model.
2. Deliberately select one already available free local reasoning model. Qwen3 4B is the historical comparison, not a current best-model recommendation. Provisioning assets is a separate explicit preparation step.
3. On the supported target hardware, measure cold/warm latency, context/output settings, current free RAM, peak VRAM and inference ownership. Keep CPU/int8 STT where configured.
4. Run all strict live samples with the exact digest. Keep schema validation, bounded response size, one repair per global task budget, cancellation/deadline and local-only transport.
5. Confirm missing service, pin drift and low resources produce a visible block while deterministic templates still work. No automatic provider/model substitution.

**Acceptance / exit:**

- Actual inference samples pass with reproducible name/digest/settings and resource measurements.
- Stop ends owned inference work and budgets are not reset by repair, recovery or restart.

## 6. V8.2 — Improve only measured command/planner failures

**Dependency:** V8.1 plus admitted tools relevant to each case.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `backend/victus/agent/commands.py; command_execution.py; router.py; context.py` | Strict intents, bounded context and qualification-aware routing. |
| `backend/victus/agent/graph.py; state.py; output_parser.py; budgets.py; progress.py` | Persisted graph/budgets, strict decisions and no-progress recovery. |
| `backend/victus/tasks/commands.py; api/routes/commands.py` | Durable intake/clarification and exact request identity. |

**Key logic:**

1. Run the unchanged 30-goal benchmark before tuning; record all actual failures, blocked cases and unavailable attempts. Investigate historical F06 two-file behavior only against current evidence.
2. Trace failure to intake, context, proposal validation, authority, tool execution or verification. Adjust the responsible layer instead of broadening tool access or forgiving a finish claim.
3. Preserve exact user-confirmed text/filename/source IDs and server-owned scope. Ask durable clarification for missing or ambiguous arguments before scheduling effects.
4. Keep model output limited to closed action/finish schemas. Python, shell, code fences, fabricated targets and page/transcript instructions never become execution authority.
5. Re-run the frozen suite after measured fixes, plus the separate held-out phrasing set. Report training/tuning attempts separately and keep the original denominator/gate.

**Acceptance / exit:**

- At least 27/30 frozen goals achieve independently verified success; full-suite identity is unchanged.
- Held-out ambiguity/unsupported/hostile cases clarify or block without unauthorized effects.
- Zero executed goals is unscored, not a replacement 0/30 accuracy measurement.

## 7. V8.3 — Complete real reviewed English speech evaluation

**Dependency:** Qualified note path plus consented corpus and local STT assets.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `backend/victus/voice/capture.py; stt.py; audio.py; transcript_review.py` | Owned bounded capture, local decoding and explicit transcript confirmation. |
| `backend/victus/voice/evaluation.py; action_evaluation.py; qualification_session.py` | Separate untouched recognition, reviewed action verification and aggregation. |
| `dashboard/src/features/voice/VoicePanel.tsx; evaluation/voice/V3.6-protocol.md` | Existing capture/review/clarification/result interface and human protocol. |

**Key logic:**

1. Use exactly 50 quiet and 50 noisy real labelled English-note recordings plus silence, background and assistant-speech negatives. Freeze labels before inference; keep private audio/text outside Git.
2. Use unique opaque sample IDs and independent destinations. Split tuning from held-out recordings and prevent duplicate audio from masquerading as additional samples.
3. Evaluate WER, intent and exact-target recognition on untouched output. Record correction counts and edits separately from the recognition score.
4. For end-to-end actions, pair each sample with its reviewed voice command ID and verify the successful task, namespace, exact artifact and verified ledger receipt. A typed task or one task reused for several samples is insufficient.
5. Use the existing prepare/evaluate protocol and matching model/runtime/manifest identities. Missing rows or backing reports produce incomplete qualification, not a default pass.

**Acceptance / exit:**

- Both 50-sample conditions meet their predeclared WER/intent/target/action limits; negatives meet the declared limit.
- Every action score has its own valid voice-origin pairing and artifact proof.
- Recognition quality and human-corrected success remain separately visible.

## 8. V8.4 — Witness physical audio, Stop and playback behavior

**Dependency:** V8.3 preparation; actual Windows devices and human session.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `backend/victus/voice/service.py; playback.py; capture.py; stt.py` | Device ownership, interruption, mute and echo cooldown. |
| `backend/victus/runtime/hotkey.py; safety/cancellation.py` | Independent physical emergency shortcut and shared Stop latch. |
| `backend/tests/live/v36_device_probe.py; voice/qualification_session.py` | Component probe plus seven required human-witnessed physical conditions. |

**Key logic:**

1. Witness active microphone unplug/reconnect with no late transcript/submission and a fresh recording after reconnection.
2. Press Stop during spoken decoding, review and playback; check owned worker/device cleanup. Separately witness physical Ctrl+Alt+Pause and keyboard dashboard Stop.
3. Listen to mute/interruption and verify actual speech stops. During real speaker output test capture suppression and the echo cooldown; flags and successful SAPI calls alone are not acoustic evidence.
4. Retain failed device ownership until safe cleanup and prevent competing streams. Record device/driver/model/runtime identity and safe pass/fail observations.
5. Keep voice off by default until explicit local asset/device configuration. Voice confirmation never approves a later native Save.

**Acceptance / exit:**

- All existing PHYSICAL_CHECKS are actually witnessed and identity-bound.
- No late submission, extra effect or retained competing stream follows Stop/error/reconnect.

## 9. V8.5 — Validate integrated local resource behavior and UI

**Dependency:** V8.1–V8.4 for advertised paths.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `backend/victus/runtime/resources.py; runtime/locks.py; voice/service.py; models/gateway.py` | Existing model/device ownership and resource-pressure behavior. |
| `dashboard/src/features/commands/TextCommandForm.tsx; features/voice/VoicePanel.tsx; features/tasks/TaskResult.tsx` | Typed and reviewed-voice state, exact clarification and verified result. |
| `backend/tests/live/v35_command_dashboard_contract.py; v36_voice_dashboard_contract.py` | Existing contract runners plus real admitted-path checks. |

**Key logic:**

1. Measure transitions between cold/warm reasoning, CPU STT and admitted workflows under actual memory pressure. Do not add another model pool or parallel inference scheduler without a measured need.
2. Test service unavailable, model pin change, STT asset drift, device loss, review expiry, duplicate confirm, disconnect/reload and Stop during contention.
3. Keep transcript review and action approval visibly distinct. Speak only the verified generic status after display acknowledgement; private payload reading stays separately controlled.
4. Regenerate API contracts if modified, then check keyboard/mobile/literal hostile text and real command/task identity across reconnect.

**Acceptance / exit:**

- Real local model and voice workloads respect existing guards and retain a usable typed path.
- Duplicate/stale/expired submissions do not create tasks or authority.
- Measure latency and peaks; an unmet declared envelope remains an explicit limitation.

## 10. V8.6 — Record V8 evidence and release input

**Dependency:** Selected V8 gates complete.

**Inspect/extend:**

| File or area | Responsibility |
| --- | --- |
| `Proposed docs/release/v8-execution-evidence.json; docs/V8-TESTS-AND-INCOMPLETE.md` | Exact inference, corpus, action, device and integrated results. |
| `docs/supported-workflows.md; docs/milestones/V8-progress.md` | Per-capability status and V9 input contract. |

**Key logic:**

1. Run focused and final regression after code/contracts stabilize; retain initial failures and all measured benchmark attempts.
2. Publish safe aggregate scores, executed/blocked/unavailable counts, model/STT hashes, source/runtime identity and physical-session scope.
3. Carry optional wake/MCP/cloud/additional languages into a separate backlog. No wake listener, paid API requirement or hidden cloud fallback is added by this plan.

**Acceptance / exit:**

- V8 claims have actual local inference and human/device evidence; missing prerequisites remain open.
- V9 receives an explicit advertised capability list and all inherited release obligations.

## 11. Verification entry points

All commands below are planned follow-ups from the repository root, not checks executed while writing this plan. Use a fresh output name/root on every attempt. Keep existing locks and the pinned project toolchain. On Linux use `backend/.venv/bin/python` and `backend/.venv/bin/victus`; Windows uses `Scripts`. Windows native/audio/package work still requires its target environment.

Existing verification entry points: `backend/tests/live/m3_30_goal_benchmark.py`, `backend/tests/live/m3_model_samples.py`, `victus.exe`. Use current help and isolated test outputs; private machine configuration is omitted from this public guide.


Create the readiness output parent first. Once the exact installed pin has been inspected, supply its actual name and full `sha256:` digest to each runner's `--model` and `--digest`, and use a fresh `--output`. The original suite is `evaluation/m3-30-goals-v1.json`; keep it unchanged.

Existing verification entry points: `victus.voice.action_evaluation`, `victus.voice.evaluation`, `victus.voice.qualification_session`. Use current help and isolated test outputs; private machine configuration is omitted from this public guide.


These voice paths are examples requiring real corpus/assets, actual reviewed sessions and witnessed `physical.json`. The aggregate is read-only and cannot create missing recordings, perform physical observations or submit tasks. Supply all predeclared condition metric fields required by the existing protocol; do not adjust thresholds after scoring.

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

Start with V8.0 and V8.1: freeze the scoring contract, inventory installed local assets and prove the exact structured-output model path.

Create the stage record before code edits. Deliver a reviewable implementation increment, actual checks and `docs/V8-TESTS-AND-INCOMPLETE.md`; no new PR or deployment is created by this planning request.

**Full V8 completion:** One exact local model has real structured-output and frozen-suite evidence; English reviewed-note speech meets predeclared recognition/action thresholds and witnessed hardware gates. Deterministic notes remain usable without a model. Packaging and release still belong to V9.

Public-web expansion, extra applications, arbitrary MCP/cloud, custom wake, additional languages, installer/autostart and public distribution remain separately selected proposals. Completion of this document does not complete or waive any implementation or qualification gate.
