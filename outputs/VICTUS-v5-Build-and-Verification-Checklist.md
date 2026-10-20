# VICTUS v5 — Build and verification checklist

Prepared: 19 October 2026, Asia/Kolkata.
Companion: [V5 implementation plan](VICTUS-v5-Next-Stage-Implementation-Plan.md).
Starting implementation tree: `c90ba11ce6570eaeb48f65a18b97c2479d8d2231` (PR #8).

Execution update: the portable increment is implemented and measured in [the V5 handoff](../docs/V5-TESTS-AND-INCOMPLETE.md). Checked boxes refer only to the stated portable/scope boundary; pending target qualification remains unchecked.

Unchecked boxes are future work or revalidation, not a claim that the named implementation is absent. Preserve all V4 results and failures. Execute portable checks; skip Windows-dependent checks only when Windows is unavailable. Missing prerequisites and unfinished long/manual sessions remain separately labelled.

## V5.0 — Source baseline and current scope

- [x] Capture actual base, dirty files, full implementation/config/contracts/locks inventory and separate runtime digest.
- [x] Verify the starting relationship to PR #8 and preserve earlier evidence.
- [x] Record raw reports unavailable in another clone without reconstructing their contents.
- [x] Create the V5 milestone design before production edits.
- [x] Reconcile the current capability matrix ahead of historical sections.
- [x] Separate portable, Windows-only, blocked-prerequisite and long-duration/manual checks.
- [x] Preserve pinned toolchain, dependency locks, generated contracts and production resource guards.

## V5.1 — Storage and recovery

- [x] Preserve the failed roots and exact test/report identities.
- [x] Record filesystem/mount, free space/inodes, SQLite version/mode and available error codes.
- [ ] Investigate the serial-run SQLite I/O failure at `CheckpointStore.connect`.
- [ ] Investigate the earlier journal-crash recovery returning unknown.
- [ ] Investigate the earlier missing action during wrong-byte Save verification.
- [x] Use finite diagnostic reruns; retain failures and passing isolated attempts.
- [x] Compare supported local temporary storage and workspace storage where available.
- [ ] Trace DB/WAL/SHM lifetime, saver/worker shutdown and test teardown ownership.
- [ ] Check node journal/action receipt ordering at process-kill boundaries.
- [ ] Document the demonstrated mechanism or explicitly retain the unresolved limitation.
- [ ] Make only the evidence-supported fix; preserve FULL durability and ownership locks.
- [ ] Preserve unknown outcomes and prevent automatic replay of uncertain effects.
- [ ] Add meaningful regression cases for the mechanism found.
- [ ] Pass focused recovery/budget/ledger tests and a final serial full suite.
- [ ] Confirm affected crash/recovery behavior on the supported Windows target.

## V5.2 — Exact-engine fixture research

- [ ] Prepare and identify the exact locked Playwright engine, or retain a documented dependency block.
- [x] Keep Chromium 153 regressions labelled alternate; do not silently change the pin.
- [ ] Use the existing strict fixture runner, not the generic browser report as a promotion substitute.
- [ ] Pass one smoke, then 20 verified unique-destination repetitions on unchanged source.
- [ ] Prove structured/text route coverage, distinct final sources and redirect-alias deduplication.
- [ ] Validate artifact hashes, task/action receipts and report identity before/after.
- [ ] Exercise scope/transfer/target/deadline/interrupt/Stop/conflict boundaries.
- [ ] Preserve useful missing-binary/startup/cleanup failure reports.
- [ ] Prove identity-based process observation and unrelated-browser preservation on Windows.
- [ ] Promote only a complete matching report using existing local maintenance tooling.
- [ ] Restart ordinary production bootstrap without injected qualification sets.
- [ ] Pass real authenticated HTTP/SSE structured/text/replay/result/Stop checks.
- [ ] Pass dashboard result, literal rendering, refresh, duplicate and keyboard checks.
- [x] Refuse changed runtime/engine/fixture/evidence identities.
- [x] Keep public sites unavailable.

## V5.3A — One verified Notepad Save

- [ ] Verify actual installed app/profile/executable identity before opening a native session.
- [ ] Preserve owned-child proof, one new selected tab, old tabs and unique scoped controls.
- [ ] Independently prove the editor is empty immediately before entering text.
- [ ] Capture current Save menu/dialog/filename/window/tab transition evidence.
- [ ] Diagnose and correct only the demonstrated Save/reacquisition boundary.
- [ ] Recheck exact text/path/target/expiry/single-use authority/Stop immediately before Save.
- [ ] Verify exact file bytes/encoding/newlines and native UI postconditions.
- [ ] Keep uncertain results unknown and reconcile read-only after quiescence.
- [ ] Preserve user documents; never terminate a shared process to make cleanup pass.
- [ ] Obtain one fully verified success before repetitions.

## V5.3B — Native campaign and admission

- [ ] Reuse implemented prepare/repetition/assembly/promotion commands.
- [ ] Complete >=20 unique native saves on unchanged source/profile/executable.
- [ ] Complete real multiwindow/restored/nonempty/stale/foreign/replaced/ambiguous-control cases.
- [ ] Complete deny/expiry/reuse/changed text/path/tab/conflict/Stop/restart cases.
- [ ] Record two actual physical scales and measured DPI.
- [ ] Pass real HTTP/dashboard exact Save approval with one mutation owner.
- [ ] Prove refresh/disconnect/duplicate actions create no new authority or extra effect.
- [ ] Assemble retained backing reports; preserve missing-case output and witness limitations.
- [ ] Promote only complete current evidence and restart.
- [ ] Verify a new ordinary production native request and stale-evidence refusal.

## V5.4 — Local reasoning

- [ ] Inventory installed runtime/model name/digest/settings and actual resources.
- [ ] Deliberately select one free local reasoning model; no implicit paid/cloud fallback.
- [x] Preserve deterministic templates without a model and shared inference ownership.
- [ ] Pass real structured-output samples with strict parsing and bounded repair.
- [ ] Diagnose measured command failures, including the historical two-file case where reproducible.
- [ ] Preserve exact confirmed arguments, clarification, budgets, Stop and independent verification.
- [ ] Check the frozen suite hash and execute all 30 goals against the original 27/30 gate.
- [x] Keep missing tool prerequisites in full-suite accounting; zero-executed attempts stay unscored.
- [ ] Report held-out paraphrase/ambiguity/injection results separately.
- [ ] Record latency, RAM/VRAM and the exact reproducible model pin.

## V5.5 — Human speech and physical audio

- [ ] Reuse strict protocol preparation/aggregation and the empty-negative regression tests.
- [ ] Predeclare thresholds and freeze held-out labels before evaluation.
- [ ] Collect 50 quiet and 50 noisy consented English note recordings plus all negative categories.
- [ ] Keep raw recordings/reference text private and separate tuning examples.
- [ ] Report raw STT WER/intent/target and correction rate by condition.
- [ ] Bind real recording/session/reviewed command/task identities to independently verified artifacts.
- [ ] Preserve operator-pairing limitations and unique-recording validation.
- [ ] Witness microphone reconnect, actual decoding/review/playback Stop and physical shortcut.
- [ ] Witness audible mute/interruption and real speaker echo/cooldown behavior.
- [ ] Preserve explicit transcript confirmation and separate consequential Save approval.
- [ ] Keep non-note intents/languages outside the corpus until separately supported and measured.

## V5.6 — Final source, reliability and Windows package

- [ ] Freeze selected implementation/config/contracts/locks and capture pre/post identities.
- [x] Pass final backend/frontend/lint/build checks without suppressing historical failures.
- [ ] Complete >=7,200 seconds, >=100 verified tasks and >=2 backup/restores.
- [ ] Meet <=20% warmed-parent RSS growth, health p95 <0.5 seconds and zero recorded failures.
- [ ] Check owned children and supplemental admitted-workflow workload with real review participation.
- [ ] Confirm target Windows behavior; short or Linux-only evidence cannot qualify the Windows candidate.
- [ ] Build a fresh complete folder candidate and retain old bundles.
- [ ] Pass actual frozen core self-test plus targeted checks for every advertised capability.
- [ ] Qualify native/browser through the actual frozen executable where advertised.
- [ ] Validate existing external account-owned record placement and immutable bundle identity.
- [ ] Refuse stale source/frozen/profile/engine/bundle records; never rewrite digests to admit a package.
- [ ] Test fresh standard Windows account/dedicated machine without developer PATH assumptions.
- [ ] Respect DPAPI/account boundaries and use fresh account-owned data.
- [ ] Distinguish guide version, app version, schema pair and actual artifact pair.
- [ ] Rehearse real old-binary backup, candidate migration and old restore to a new root.
- [ ] Keep formal cross-version gate pending unless actual versioned release artifacts exist.
- [ ] Export sanitized evidence and publish a scope-accurate release decision.

## Per-stage evidence and completion

- [ ] Record problem/design, changed files, commands, source/runtime identity and fresh root.
- [ ] Retain every attempt, hashes, boundary type, observations, cleanup and blockers.
- [ ] Keep raw audio/tokens/prompts/private paths/native inventories/logs out of exported summaries.
- [x] Distinguish implemented, enabled, qualified and temporarily resource-blocked states.
- [x] Keep inherited V4 obligations open until their matching gates pass.
- [x] Record any deliberately narrower candidate scope without calling full V5 complete.
