# VICTUS v9 — Build and verification checklist

Prepared: 20 October 2026.
Companion: [V9 implementation plan](VICTUS-v9-Next-Stage-Implementation-Plan.md).
Starting inspected revision: `10226a45c3b791fa9a7439ce519db24aa9f89100`; reconcile any V6/V7/V8 work before execution.

Every box starts unchecked because these are future acceptance checks. An unchecked box can mean revalidation of existing implementation, not missing code. Recorded V5 results remain historical; this planning task ran no application or hardware qualification.

## V9.0 — Freeze release scope and required evidence

Dependency: V7/V8 handoffs; portable preparation.

- [ ] Choose the exact candidate scope based on measured V7/V8 status. A typed-note-only candidate can be separately proposed, but it does not close native/model/speech requirements.
- [ ] Record source commit, dirty files, lock/config/contracts inventory and selected target OS/profile/engine/model/STT prerequisites.
- [ ] Keep guide V9 separate from executable product version. If a version is deliberately changed, update all actual metadata/resource owners consistently and recapture identity.
- [ ] Classify every required gate as passed/current, failed, blocked-prerequisite, Windows-pending, human-pending, duration-pending or not-advertised with retained debt.
- [ ] An unambiguous mandatory gate matrix and advertised capability list exist before final campaigns.
- [ ] No optional integration or omitted capability is implicitly qualified.

## V9.1 — Run final regression and full-duration reliability

Dependency: Frozen final implementation/config/contracts/locks.

- [ ] Run relevant focused checks and final serial full backend/frontend/lint/build/API-generation on the final code. Preserve earlier evidence rather than carrying old counts as new.
- [ ] Capture pre/post manifests and run >=7,200 real wall-clock seconds, >=100 verified tasks, >=2 checksum-verified backup/restores, zero recorded failures, warmed-parent RSS growth <=20% and health p95 <0.5 seconds.
- [ ] Keep actual RAM/disk safeguards. Pressure rejections are reported distinctly from accepted-task failures; blocked preflight or an incomplete progress file is not a completed soak.
- [ ] Inspect owned worker/browser processes in addition to the core parent RSS metric. Report measurement scope and orphan/cleanup findings explicitly.
- [ ] Where browser/native/command paths are advertised, run a supplemental declared workload with their actual adapters. Keep deliberate native review manual; do not auto-approve to accelerate a soak.
- [ ] If source changes, retain the attempt as historical and rerun affected qualification on the new final identity. An old M7 two-hour pass does not qualify V9 bytes.
- [ ] Final report, unchanged source and all original core stability thresholds pass.
- [ ] Every advertised additional workflow has separate current workload and cleanup evidence.

## V9.2 — Build and verify the immutable Windows folder candidate

Dependency: V9.0; build final source after V9.1 identity freeze.

- [ ] Build into fresh output/work directories with the selected source manifest. Preserve previous bundles; do not overwrite an active application folder.
- [ ] Keep executable, _internal resources and release manifest together. Bundle no API tokens, sessions, prompts, models, recordings or personal data.
- [ ] Run the actual frozen self-test with normal policy: authentication, note worker/readback, lock, Stop, dependency messages, backup/migrate/restore and restart.
- [ ] Check source_sha256 and bundle_manifest_sha256 in new self-test evidence and independently verify all listed bundle bytes.
- [ ] Observe graceful shutdown separately from bounded owned-process cleanup; a harness Kill fallback cannot establish that the server exited gracefully.
- [ ] The tested bundle exactly matches its manifest/source record and preserves separate account-owned runtime data.
- [ ] Fresh frozen self-tests pass; package presence alone enables no hardware-dependent capability.

## V9.3 — Qualify capabilities using the actual candidate

Dependency: V9.2 exact bundle plus advertised workflow prerequisites.

- [ ] Use Victus.exe qualification commands for advertised browser/native scope. Never copy or relabel a source qualification digest as frozen evidence.
- [ ] Store frozen records under the existing account-owned qualifications/<runtime identity> location or explicit absolute qualification root. Do not modify immutable bundle resources to promote.
- [ ] For each advertised capability retain actual candidate-bound adapter/asset identities, backing artifacts and verified ledger records; repeat physical/device gates where candidate changes affect their boundary.
- [ ] Restart the ordinary frozen service and test authenticated HTTP/SSE/dashboard admitted paths, exact Save review where enabled, replay, refresh and Stop.
- [ ] In isolated negative copies alter bundle/profile/engine or evidence and confirm refusal. Preserve the actual tested candidate unmodified.
- [ ] Advertised frozen capabilities work after ordinary restart using matching external records.
- [ ] Changed/missing qualification or bundle bytes leave the relevant capability unavailable.
- [ ] No source-test-only override or injected registry supplies production admission.

## V9.4 — Prove fresh standard-account deployment

Dependency: V9.2/V9.3; actual fresh Windows account or dedicated machine.

- [ ] Copy the complete candidate and test script into a fresh standard account or dedicated machine with no repository/Python/Node environment on PATH.
- [ ] Run without elevation, use a fresh writable data root and verify default loopback/authentication, immutable app files, locks and explicit prerequisite messages.
- [ ] Configure only intentionally provided model/browser/STT assets and rerun the advertised capability checks. No first-launch download, autostart or microphone activation is implied.
- [ ] Test intended account-owned protected data. DPAPI content from the developer account is not assumed portable and must fail safely where account binding prevents access.
- [ ] Record OS/build, executable version, bundle/runtime identity and sanitized outcome. An unelevated developer/admin-account session does not replace this gate.
- [ ] Fresh standard-account self-test and advertised-scope checks pass without developer PATH or elevation.
- [ ] Missing assets and foreign-account protected payloads fail safely with no mutation replay.

## V9.5 — Rehearse actual-artifact migration and rollback

Dependency: Retained compatible prior bundle plus exact candidate.

- [ ] Run the old executable on isolated old-version data and produce its own verified offline backup after all owners stop.
- [ ] Use the candidate to migrate a compatible restored copy and create a new verified result. Reject newer schema and held instance locks; preserve transactional migration semantics.
- [ ] Stop the candidate, use the old executable to restore its backup into a new root and verify old operation. Preserve the candidate data for diagnosis.
- [ ] Invalidate old approvals/intakes and prevent automatic replay of interrupted effects. Never downgrade an active database or overwrite the only backup.
- [ ] Report actual binary/hash/schema identities separately from formal released-version identities. The historical schema-7-to-8 pair used product 0.1.0 on both sides; it is not formal cross-version release proof.
- [ ] Both actual executables complete verified backup/migration/new-output/rollback on isolated roots.
- [ ] A formal cross-version pass requires genuinely distinct retained release versions; absent prior release remains explicitly pending.

## V9.6 — Publish evidence and record the release decision

Dependency: All mandatory selected gates; no unresolved hidden failure.

- [ ] Create the final evidence summary from actual reports, with per-capability source/runtime/bundle/asset identities and hashes. Missing private backing files are unavailable, not reconstructed from hashes.
- [ ] Check exports for private host/account paths, tokens, audio/transcripts, browser profiles, prompt content and service logs.
- [ ] Record go/no-go against the predeclared mandatory matrix. Open mandatory gates keep release_qualified false; a proposed narrower scope has its own explicit decision and retained obligations.
- [ ] Deliver the folder candidate, exact setup/self-test/rollback instructions and honest limitations. Preparing a release does not publish it or deploy it.
- [ ] Keep signing/public distribution, installer/autostart, arbitrary applications/public-web scope, extra languages, custom wake and cloud/MCP expansion in separately selected future work.
- [ ] Every support claim maps to current evidence and every open requirement has a next action.
- [ ] No public publication, installer, always-on listening or extra automation scope is performed by this plan.

## Per-stage evidence and completion

- [ ] Record actual source/runtime/config/lock and target identity.
- [ ] Retain commands, all outcomes, report/artifact hashes and cleanup.
- [ ] Separate portable, Windows-only, missing prerequisite, human and duration gates.
- [ ] Update the current capability matrix and exact incomplete-work register.
- [ ] Confirm final advertised claims match current evidence without waiving inherited gates.
