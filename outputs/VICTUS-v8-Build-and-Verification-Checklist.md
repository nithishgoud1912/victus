# VICTUS v8 — Build and verification checklist

Prepared: 20 October 2026.
Companion: [V8 implementation plan](VICTUS-v8-Next-Stage-Implementation-Plan.md).
Starting inspected revision: `10226a45c3b791fa9a7439ce519db24aa9f89100`; reconcile any V6/V7/V8 work before execution.

Every box starts unchecked because these are future acceptance checks. An unchecked box can mean revalidation of existing implementation, not missing code. Recorded V5 results remain historical; this planning task ran no application or hardware qualification.

## V8.0 — Freeze the evaluation contract and capability scope

Dependency: Reconciled V7 baseline; portable preparation.

- [ ] Inventory which V7 workflows are actually admitted and which are blocked. Freeze the full benchmark and record its hash before inference; retain unavailable cases in accounting.
- [ ] Define a separate held-out supported-intent phrasing set covering missing values, ambiguity, exact-content preservation, hostile content and unsupported requests. Do not replace or blend the original suite.
- [ ] Predeclare latency/resource measurements and voice numeric thresholds before evaluation. Existing WER/intent/target/action fields are independent; record correction rate separately.
- [ ] Keep the corpus bounded to reviewed English note commands. Native Save review remains a separate action even if a future spoken checklist is supported.
- [ ] Unchanged benchmark identity, declared voice thresholds and admitted-tool catalog are recorded before scoring.
- [ ] No invented accuracy or model ranking appears without measured inference.

## V8.1 — Establish one local model pin and resource envelope

Dependency: V8.0 plus explicitly installed local runtime/model.

- [ ] Inspect actual Ollama tags, unique model name/digest and installed settings. A reachable service or embedding asset does not establish a reasoning model.
- [ ] Deliberately select one already available free local reasoning model. Qwen3 4B is the historical comparison, not a current best-model recommendation. Provisioning assets is a separate explicit preparation step.
- [ ] On the supported target hardware, measure cold/warm latency, context/output settings, current free RAM, peak VRAM and inference ownership. Keep CPU/int8 STT where configured.
- [ ] Run all strict live samples with the exact digest. Keep schema validation, bounded response size, one repair per global task budget, cancellation/deadline and local-only transport.
- [ ] Confirm missing service, pin drift and low resources produce a visible block while deterministic templates still work. No automatic provider/model substitution.
- [ ] Actual inference samples pass with reproducible name/digest/settings and resource measurements.
- [ ] Stop ends owned inference work and budgets are not reset by repair, recovery or restart.

## V8.2 — Improve only measured command/planner failures

Dependency: V8.1 plus admitted tools relevant to each case.

- [ ] Run the unchanged 30-goal benchmark before tuning; record all actual failures, blocked cases and unavailable attempts. Investigate historical F06 two-file behavior only against current evidence.
- [ ] Trace failure to intake, context, proposal validation, authority, tool execution or verification. Adjust the responsible layer instead of broadening tool access or forgiving a finish claim.
- [ ] Preserve exact user-confirmed text/filename/source IDs and server-owned scope. Ask durable clarification for missing or ambiguous arguments before scheduling effects.
- [ ] Keep model output limited to closed action/finish schemas. Python, shell, code fences, fabricated targets and page/transcript instructions never become execution authority.
- [ ] Re-run the frozen suite after measured fixes, plus the separate held-out phrasing set. Report training/tuning attempts separately and keep the original denominator/gate.
- [ ] At least 27/30 frozen goals achieve independently verified success; full-suite identity is unchanged.
- [ ] Held-out ambiguity/unsupported/hostile cases clarify or block without unauthorized effects.
- [ ] Zero executed goals is unscored, not a replacement 0/30 accuracy measurement.

## V8.3 — Complete real reviewed English speech evaluation

Dependency: Qualified note path plus consented corpus and local STT assets.

- [ ] Use exactly 50 quiet and 50 noisy real labelled English-note recordings plus silence, background and assistant-speech negatives. Freeze labels before inference; keep private audio/text outside Git.
- [ ] Use unique opaque sample IDs and independent destinations. Split tuning from held-out recordings and prevent duplicate audio from masquerading as additional samples.
- [ ] Evaluate WER, intent and exact-target recognition on untouched output. Record correction counts and edits separately from the recognition score.
- [ ] For end-to-end actions, pair each sample with its reviewed voice command ID and verify the successful task, namespace, exact artifact and verified ledger receipt. A typed task or one task reused for several samples is insufficient.
- [ ] Use the existing prepare/evaluate protocol and matching model/runtime/manifest identities. Missing rows or backing reports produce incomplete qualification, not a default pass.
- [ ] Both 50-sample conditions meet their predeclared WER/intent/target/action limits; negatives meet the declared limit.
- [ ] Every action score has its own valid voice-origin pairing and artifact proof.
- [ ] Recognition quality and human-corrected success remain separately visible.

## V8.4 — Witness physical audio, Stop and playback behavior

Dependency: V8.3 preparation; actual Windows devices and human session.

- [ ] Witness active microphone unplug/reconnect with no late transcript/submission and a fresh recording after reconnection.
- [ ] Press Stop during spoken decoding, review and playback; check owned worker/device cleanup. Separately witness physical Ctrl+Alt+Pause and keyboard dashboard Stop.
- [ ] Listen to mute/interruption and verify actual speech stops. During real speaker output test capture suppression and the echo cooldown; flags and successful SAPI calls alone are not acoustic evidence.
- [ ] Retain failed device ownership until safe cleanup and prevent competing streams. Record device/driver/model/runtime identity and safe pass/fail observations.
- [ ] Keep voice off by default until explicit local asset/device configuration. Voice confirmation never approves a later native Save.
- [ ] All existing PHYSICAL_CHECKS are actually witnessed and identity-bound.
- [ ] No late submission, extra effect or retained competing stream follows Stop/error/reconnect.

## V8.5 — Validate integrated local resource behavior and UI

Dependency: V8.1–V8.4 for advertised paths.

- [ ] Measure transitions between cold/warm reasoning, CPU STT and admitted workflows under actual memory pressure. Do not add another model pool or parallel inference scheduler without a measured need.
- [ ] Test service unavailable, model pin change, STT asset drift, device loss, review expiry, duplicate confirm, disconnect/reload and Stop during contention.
- [ ] Keep transcript review and action approval visibly distinct. Speak only the verified generic status after display acknowledgement; private payload reading stays separately controlled.
- [ ] Regenerate API contracts if modified, then check keyboard/mobile/literal hostile text and real command/task identity across reconnect.
- [ ] Real local model and voice workloads respect existing guards and retain a usable typed path.
- [ ] Duplicate/stale/expired submissions do not create tasks or authority.
- [ ] Measure latency and peaks; an unmet declared envelope remains an explicit limitation.

## V8.6 — Record V8 evidence and release input

Dependency: Selected V8 gates complete.

- [ ] Run focused and final regression after code/contracts stabilize; retain initial failures and all measured benchmark attempts.
- [ ] Publish safe aggregate scores, executed/blocked/unavailable counts, model/STT hashes, source/runtime identity and physical-session scope.
- [ ] Carry optional wake/MCP/cloud/additional languages into a separate backlog. No wake listener, paid API requirement or hidden cloud fallback is added by this plan.
- [ ] V8 claims have actual local inference and human/device evidence; missing prerequisites remain open.
- [ ] V9 receives an explicit advertised capability list and all inherited release obligations.

## Per-stage evidence and completion

- [ ] Record actual source/runtime/config/lock and target identity.
- [ ] Retain commands, all outcomes, report/artifact hashes and cleanup.
- [ ] Separate portable, Windows-only, missing prerequisite, human and duration gates.
- [ ] Update the current capability matrix and exact incomplete-work register.
- [ ] Confirm final advertised claims match current evidence without waiving inherited gates.

## Implementation follow-up

The portable implementation and current results are recorded in
[the V8 handoff](../docs/V8-TESTS-AND-INCOMPLETE.md). Original acceptance boxes
remain open where real inference, recordings or witnessed Windows evidence is
required. Portable contract passes do not complete those mixed acceptance gates.
