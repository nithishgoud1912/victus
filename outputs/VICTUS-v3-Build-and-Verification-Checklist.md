# VICTUS v3 — Build and verification checklist

> **Consolidated V3 handoff (19 October 2026):** The source implementation is substantially present, but native/browser/model/voice/release qualification remains incomplete. Testing is deliberately deferred for this handoff. See [the exact incomplete work and deferred test register](VICTUS-v3-Incomplete-Work-and-Tests.md). Historical checkboxes and planned commands below are not newly verified completion claims.

Prepared: 18 October 2026. Companion: [Next-stage implementation plan](VICTUS-v3-Next-Stage-Implementation-Plan.md).
All boxes are future work; this checklist does not assert implementation completion.

## V3.0 — Baseline

- [ ] Record dirty source/config/contracts identity and preserve existing edits.
- [ ] Record isolated runtime/evidence roots and current enabled capabilities.
- [ ] Verify original note creation, exact readback, deduplication, replay and Stop.
- [ ] Keep earlier test/package counts labelled as historical.

## V3.1 — Native Notepad

- [ ] Write stage guide before production edits.
- [ ] Measure the failing boundary in one supervised launch/editor/Save run.
- [ ] Prove owned process/window/editor; block ambiguous reuse and nonempty editors.
- [ ] Prove filename commitment, encoding, Save dispatch and exact artifact/UI postconditions.
- [ ] Preserve unknown effects; do not retry uncertain Save automatically.
- [ ] Pass one complete supervised run, then 20 native repetitions.
- [ ] Exercise two windows, stale process, missing controls, existing file and Stop.
- [ ] Test actual intended display scales and record measured DPI.
- [ ] Keep native admission disabled if any required gate remains unresolved.

## V3.2 — Native approval and task-service integration

- [ ] Reuse persistent approval/permit records; document bounded worker review handoff.
- [ ] Bind exact task/action, tool, target, destination, content hash and expiry.
- [ ] Prove approve once, denial, expiry, changed content/target/path and restart invalidation.
- [ ] Revalidate Stop and authority immediately before native Save.
- [ ] Pass authenticated HTTP submit/review/Save/readback through existing task/events path.
- [ ] Preserve deduplication and generic-route capability gates.
- [ ] Enable server registration only after native and review qualification both pass.

## V3.3 — Dashboard

- [ ] Extend existing forms, task views, approval panel and generated contracts.
- [ ] Show unavailable capabilities and specific reasons from server state.
- [ ] Preserve uncertain retry identity and refresh/reconnect behavior.
- [ ] Pass keyboard review/Stop, mobile, safe literal text and reduced-motion checks.

## V3.4 — Browser research

- [ ] Qualify the existing localhost workflow and exact report verifier.
- [ ] Add narrow authenticated admission through the existing queue/dispatcher.
- [ ] Pass scope/redirect/transfer/target/timeout/Stop/deduplication cases.
- [ ] Keep page instructions untrusted and source evidence traceable.
- [ ] Record fixture qualification separately from any later public-site evidence.

## V3.5 — Local text commands

- [ ] Expose only qualified note/checklist/research intents.
- [ ] Clarify missing or ambiguous inputs before effects.
- [ ] Reuse graph, parser, budgets, checkpoints and existing scheduling.
- [ ] Check actual local model readiness and preserve resource safeguards.
- [ ] Require verifier evidence for every promised effect.
- [ ] Report full 30-goal benchmark against its 27/30 gate without removing failures.
- [ ] Add supported-intent/adversarial/timeout/Stop/restart cases.

## V3.6 — Voice and release

- [ ] Submit edited/reviewed transcripts through the same command path.
- [ ] Test real microphone/disconnect/assistant-speech/cancellation behavior.
- [ ] Measure 50 quiet and 50 noisy labelled commands and end-to-end outcomes.
- [ ] Keep wake and optional integrations behind their own gates.
- [ ] Run final regression, frontend build/lint/contracts and current-source soak.
- [ ] Rebuild and self-test the folder package; record exact source/bundle identity.
- [ ] Complete fresh standard-account and real cross-version upgrade/rollback gates.
- [ ] Update supported-workflow matrix with implemented, deterministic, laptop, public-site and pending evidence separately.

## Per-stage evidence

Record exact changed files, tested revision/content manifest, command and result, runtime root, artifact hashes, observed side effects, manual interventions and remaining limitations. Export sanitized evidence only. A blocked safety case is a correct blocked result; it does not count as a successful requested workflow.
