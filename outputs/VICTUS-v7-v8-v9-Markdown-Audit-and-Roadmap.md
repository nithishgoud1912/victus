# VICTUS v7 / v8 / v9 — Markdown audit and roadmap

Prepared: 20 October 2026.
Repository: `nithishgoud1912/victus`.
Inspected `main` revision: `10226a45c3b791fa9a7439ce519db24aa9f89100` (merge of PR #10, V5).

## 1. Review boundary and evidence priority

Read/analyzed all **58 tracked Markdown files**, **7,200 lines**, at the inspected revision, including root/dashboard setup, every decision and milestone, release/support matrices, evaluation protocols/results, wake experiment and every V3–V5 output plan/checklist/audit. The inventory below records every source, line count, full content hash and its planning consequence. Generated V7/V8/V9 files are excluded from this starting inventory.

Selected implementation owners and `docs/release/v5-execution-evidence.json` were inspected to distinguish implemented features from unmeasured target behavior. This is documentation/static inspection, not a new code audit, test campaign, machine qualification or release approval. No AGENTS.md was found in the checkout or its workspace parent.

These are proposed implementation stages, not completed work or new validation results. Guide numbers do not change the product version. The inspected repository identifies as a `0.1.0` candidate. No application code, lockfile, generated contract, qualification record or runtime data was changed for this planning request.

**V6 reconciliation is mandatory:** the inspected `main` has merged V5 (PR #10), but no tracked V6 Markdown, V6 remote branch or matching V6 pull request was found. A separate filename search did not resolve a V6 plan. This does not establish that work in another checkout never happened. At implementation start, locate any V6 work, record its actual revision and evidence, and replace overlapping tasks with validation of that work. If unavailable, retain `V6_NOT_RECONCILED`; use the measured V5 baseline below without claiming V6 completion.

The plans split the existing unfinished work into three focused increments: V7 dependable execution, V8 measured local interpretation and reviewed speech, V9 reliability and frozen Windows release. This allocation is a planning decision based on the audit, not an already approved expansion of runtime capabilities.


Priority: actual current implementation plus matching measured evidence; latest V5 handoff; latest V4 continuation; earlier per-revision milestones; historical planning snapshots. An old proposal is not proof a module is still missing. A later passing suite is not a diagnosis of an earlier intermittent failure.

## 2. Current baseline and retained limitations

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


V5 source evidence covers 307 files with SHA-256 `c2c51729369b8c5fc47cbba8c8476a1258d3b2e169566d89763fb784ac59563c`; its runtime SHA-256 is `6f02bb172093b68363f1f281ffbcfb03a91b160d5666f43e6be43043d8441c5d`. These are report identities, distinct from the inspected Git merge SHA and from any future post-planning source inventory. V5 says `release_qualified=false`, no records promoted and no newly enabled capabilities.

## 3. Cross-version roadmap

| Guide | Focus | First batch | Completion boundary |
| --- | --- | --- | --- |
| [V7](VICTUS-v7-Next-Stage-Implementation-Plan.md) | Dependable note/fixture/Notepad execution | V6 reconciliation, current manifest and finite storage diagnosis | Actual exact-engine/profile campaigns and ordinary production HTTP/dashboard admission |
| [V8](VICTUS-v8-Next-Stage-Implementation-Plan.md) | Measured local reasoning and reviewed English speech | Frozen scoring contract and one actual local model pin | Real structured samples, original >=27/30 gate, 50+50 corpus/action results and physical audio |
| [V9](VICTUS-v9-Next-Stage-Implementation-Plan.md) | Reliability and frozen Windows release | Advertised scope and mandatory gate freeze | Current two-hour core plus advertised-workflow evidence, frozen/account/rollback qualification and honest release decision |

V7 browser and native stages can advance independently after the storage/Stop foundation. V8 note-only model/speech preparation can advance while native is blocked; unavailable tools still cannot count as completed goals. V9 package scaffolding can be inspected early, but final proof must bind frozen final bytes. These are dependency rules, not instructions to spawn agents.

## 4. Required corrections to historical interpretation

1. V5 portable regression is green at its tested source; retain the V4 failed runs and unexplained causes alongside it.
2. The V5 atomic journal-completion fix is independently proven; it is not established as the cause of V4 SQLite I/O, journal unknown or missing-ledger observations.
3. Native review/new-tab/session/promotion, browser discovery, readiness and voice aggregation already exist. Advance their missing real evidence instead of recreating them.
4. Alternate Chromium passes do not qualify the locked engine. Negative production admission is not successful research; generic repetitions are not strict fixture-promotion evidence.
5. A model-unavailable attempt is unscored. Preserve historical 19/30 and unchanged 27/30 gate; do not shrink its denominator to admitted note cases.
6. Device component flags and corrected typed tasks do not establish acoustic recognition, reviewed voice origin or actual speaker echo behavior.
7. The historical M7 two-hour pass belongs to its named source. V5's 60-second smoke does not satisfy new final-source reliability.
8. Same-product-version binaries can prove an actual artifact/schema rehearsal while formal cross-version release remains pending.
9. Exact engine/model/corpus blocks and long/manual work are not Windows-only skips. Preserve the clarified policy: run portable implementation checks.
10. Missing V6 material is a reconciliation gate; do not silently treat a chat request as merged code.

## 5. Carry-forward gate ownership

| Open requirement | Owner | Prerequisite / next concrete action |
| --- | --- | --- |
| V6 source/evidence absent in inspected branch | V7.0 | Locate actual checkout/artifact or retain unreconciled state |
| Historical persistence mechanisms unknown | V7.1 | Finite isolated/suite-order diagnosis and supported Windows disposition |
| Exact-engine strict fixture campaign | V7.2 | Install actual locked engine; smoke then >=20 runs |
| Positive ordinary browser admission/UI | V7.2/4 | Matching promotion, ordinary restart and real HTTP/dashboard probe |
| One complete native Save | V7.3A | Observe actual Windows identity/dialog/Save transition |
| Native repetition/adverse/DPI/review | V7.3B | First verified Save, >=20 runs, real human review and two scales |
| Actual local reasoning and original benchmark | V8.1/2 | Installed exact pin, samples, unchanged full suite |
| Real English recognition/action corpus | V8.3 | Exactly 50 quiet +50 noisy plus negatives and real command pairing |
| Physical mic/Stop/shortcut/playback/echo | V8.4 | Human-witnessed actual device session |
| Current-source full reliability | V9.1 | >=7200s, >=100 tasks, >=2 restores and original stability thresholds |
| Frozen-bound workflow/package proof | V9.2/3 | Fresh onedir build and candidate-owned qualification |
| Fresh standard account / account-bound data | V9.4 | New standard account or dedicated machine without developer PATH |
| Actual prior/candidate upgrade/rollback | V9.5 | Retained compatible real bundles; separate formal release-version gate |
| Truthful release status and setup | V9.6 | All declared mandatory gates with matching evidence |

## 6. Complete Markdown inventory and planning treatment

Paths are repository-relative; hashes are SHA-256 of the complete UTF-8 content. This table provides a reproducible review boundary, not qualification of the contents.

| Source | Lines | SHA-256 | Planning treatment |
| --- | ---: | --- | --- |
| [README.md](../README.md) | 52 | `38d21a729075b6c2a0cc5168cf4ed55335dc644b2a418a07cb2a693c3c5191c6` | V7.0/V9.6: current navigation and actual availability; latest handoff takes precedence over older summary wording. |
| [dashboard/README.md](../dashboard/README.md) | 87 | `1b2ea7bdb151e81273fc0d94e165f9ecdd1969c979a29ec0527c53ec1588b95b` | V7.4/V8.5/V9.6: preserve auth/token lifecycle, generated API ownership, read-only refresh and setup; reconcile old test counts. |
| [docs/V4-TESTS-AND-INCOMPLETE.md](../docs/V4-TESTS-AND-INCOMPLETE.md) | 399 | `701c5b14f1c7de6870a67afb91a95944b507fa707ae0889671e7379147fadcab` | V7.1–3/V8/V9: preserve original failures, exact-engine block, target requirements and clarified portable-test policy. |
| [docs/V5-TESTS-AND-INCOMPLETE.md](../docs/V5-TESTS-AND-INCOMPLETE.md) | 109 | `edd7435191f61239c4b4159790ac67d58a808426ad0597e214cfae1b6808218c` | Authoritative latest handoff: V7 execution gaps, V8 model/corpus/physical gaps, V9 full-duration/frozen/account gaps. |
| [docs/decisions/001-windows-folder-release.md](../docs/decisions/001-windows-folder-release.md) | 39 | `fb048e4ef2546c38f7eef1e404dfffcef4f7642028722bdb95479193faa4587d` | V9.2/4/5: onedir, account-owned data, no first-run asset download, offline rollback and truthful release gates. |
| [docs/decisions/002-shared-execution-path.md](../docs/decisions/002-shared-execution-path.md) | 60 | `696f9ce42b40d694f46f475e3397b1185e6aeac01b148e845587b55246e881a1` | V7/V8: retain dispatch_step, strict proposals, trusted context, independent verification and owner-local adapters. |
| [docs/decisions/003-task-event-transactions.md](../docs/decisions/003-task-event-transactions.md) | 43 | `4e80a261b009250e47903d2d69a2963ce0ea34eafd1461cbd5e2a6cb4f8b6065` | V7.1/4: atomic admission/events, request deduplication and no mutation from replay; retained-history boundary persists. |
| [docs/decisions/004-stop-and-owner-retention.md](../docs/decisions/004-stop-and-owner-retention.md) | 43 | `f63729309d26445e6397b954d1079bacdfd14d458cd8a46a1a85e53873cf4b49` | V7/V8/V9: retain Stop latch and failed-cleanup mutation/directory ownership; no automatic unsafe reset. |
| [docs/decisions/005-notepad-native-profile.md](../docs/decisions/005-notepad-native-profile.md) | 39 | `a146a619177031f7b0b38405e5630121c23a90ff37210100afcaaaedee3cbe52` | V7.3A: pinned child lease, exact nested dialog/filename host and empty-editor guard; isolated Save is not full qualification. |
| [docs/decisions/006-gated-checklist-admission.md](../docs/decisions/006-gated-checklist-admission.md) | 34 | `31756b466b405fa7fc2fa899f991c04c855f1e3a49fa1056e7ab9beee907b65f` | V7.3B: same narrow profile gate for structured/generic admission; Save needs exact bytes and native UI. |
| [docs/decisions/007-v4-native-ownership-findings.md](../docs/decisions/007-v4-native-ownership-findings.md) | 73 | `ef67d5b0a6100ec925438f106e2ea66356eec04d3471be8ae03b828eb730c351` | V7.3A/B: retain unknown Save, nonempty restoration and new-tab proof; existing implementation supersedes old proposed work. |
| [docs/milestones/9BC-M5-UI.md](../docs/milestones/9BC-M5-UI.md) | 22 | `eadc38401ed80e972a1b95d515b931fcd8d5f7f6466e913cf205c29679258b27` | V7.4: preserve literal rendering, accessible Stop, review UI and safe reconnect; early deferrals are historical. |
| [docs/milestones/M0-feasability.md](../docs/milestones/M0-feasability.md) | 36 | `2a40c8aea53333c9d6345dd696842c6ab8b0acd1a6c92b1ab62b331d1a6da582` | All versions: local deterministic hierarchy and explicit feasibility/qualification boundaries. |
| [docs/milestones/M1-5D-5E.md](../docs/milestones/M1-5D-5E.md) | 122 | `659d9098253655beb0cd2e9c42bb118881453e48b40d6899b0f5be3214f855d1` | V7.1/4: bounded queue/supervisor/deadlines and independent Stop; physical shortcut is a separate V8 gate. |
| [docs/milestones/M2-6A-browser-sessions.md](../docs/milestones/M2-6A-browser-sessions.md) | 112 | `509d1cebb97b5c3d3620c94fcfb5cad6a2715e5c25961f9ace7041d3febcbbfc` | V7.2: adapter loop/thread/process ownership, dedicated profile locks and explicit ephemeral/persistent scope. |
| [docs/milestones/M2-6B-browser-observations.md](../docs/milestones/M2-6B-browser-observations.md) | 147 | `c440c532ece32e8c80ad00fcac5724663b14f3fbec106ba9190fa37109a1fdeb` | V7.2: bounded visible text/opaque targets, privacy exclusion, semantic freshness and independent readback. |
| [docs/milestones/M2-6CD-network-uia.md](../docs/milestones/M2-6CD-network-uia.md) | 208 | `03f80b3c541f1d5533de6501f75848993b728e2ad1ab707e59c4f45afc598a61` | V7.2/3: request/redirect/private-network mediation, staged transfers, exact UIA profile and unique process-scoped controls. |
| [docs/milestones/M2-6E-workflows.md](../docs/milestones/M2-6E-workflows.md) | 95 | `a6c0e1546572d2e45d7b6a9f5aaeb1d725a3f4ebe46637307f6af2980ae451b6` | V7.2/3: distinct final observed sources versus generated summary; simulated Notepad and browser scaling do not qualify native DPI. |
| [docs/milestones/M3-7A-model-gateway.md](../docs/milestones/M3-7A-model-gateway.md) | 97 | `38cb51f6dbd2f6474160f5ff93725c38b74bdd76415ddba8ea5a1f17eeb832fa` | V8.1: exact pin, JSON-schema path, shared request/token budget and one repair; actual samples still required. |
| [docs/milestones/M3-7B-state-graph.md](../docs/milestones/M3-7B-state-graph.md) | 133 | `4447153cb26fde3a6737e6cd5053d8359db9f8f92621aba177e33851e31d55b8` | V7.1/V8.2: persistent checkpoints, domain-service nodes, exact journal/receipt recovery and no repeated uncertain effect. |
| [docs/milestones/M3-7C-budgets-progress.md](../docs/milestones/M3-7C-budgets-progress.md) | 112 | `65853da508ddead66a188164df6f17b3ae828ad63cb930ba5d9d75159b007354` | V8.2: preserve persisted cumulative budgets and semantic no-progress limits across plans and recovery. |
| [docs/milestones/M3-7D-routing-context.md](../docs/milestones/M3-7D-routing-context.md) | 135 | `3aef6cb659fcf0eec95e9e40062e3cdb52488fb994029ee3d1dc028e211fd52c` | V8.0/2: current routing/context foundation and historical 19/30; frozen 27/30 remains the original gate. |
| [docs/milestones/M4-8A-approval-records.md](../docs/milestones/M4-8A-approval-records.md) | 89 | `1c9bd18ce182b757725688e78127955623a61de9093e359d2d85e8e30e645bb1` | V7.3/V8: exact binding, expiry, single use and restart/Stop authority invalidation. |
| [docs/milestones/M4-8B-8C-dispatch-review.md](../docs/milestones/M4-8B-8C-dispatch-review.md) | 120 | `46d110b998bc95c131dd693c855ed6ccce09a8b7a9e502ba9af1fa27c8202497` | V7.3B/4: reuse real review lifecycle and dispatcher path; do not create parallel approval authority. |
| [docs/milestones/M4-8D-reconciliation-recovery.md](../docs/milestones/M4-8D-reconciliation-recovery.md) | 119 | `06a34aee050ecec4df9f437af067489e2b8b67720172ad9a1a60d88d4b08f094` | V7.1/3/V9.5: independent effect reconciliation, bounded permitted retry and explicit compensation only. |
| [docs/milestones/M9-packaging-release.md](../docs/milestones/M9-packaging-release.md) | 100 | `24d0e88bd4fcd0b9c6c4f3dd81147195702410de419cbf0e11a6d4e191ed24b0` | V9: retain original folder-build resources and evidence boundary; old executable counts do not qualify final source. |
| [docs/milestones/V2-progress.md](../docs/milestones/V2-progress.md) | 198 | `b391fd5515e63b4878daa2c35ea500d526d44420fe34e4fc875598710f3adab5` | Historical architecture/package baseline; later V2/V3/V4/V5 records determine current implementation state. |
| [docs/milestones/V2.1-execution-path.md](../docs/milestones/V2.1-execution-path.md) | 143 | `a937c930a4e1848708787c50325fc2091e40c10146b84aafea4f1a375b7a483b` | V7: shared generic dispatcher already implemented; retain worker-local ownership and verified-parent receipt. |
| [docs/milestones/V2.2-durable-tasks.md](../docs/milestones/V2.2-durable-tasks.md) | 136 | `e552819085baf0a41bb6b59f478f22a142b5e36a714ffe8c5505a2917ea4dfa8` | V7.1/4: atomic task/event/migration transactions and durable deduplication; pending work is not replayed at restart. |
| [docs/milestones/V2.3-stop-supervision.md](../docs/milestones/V2.3-stop-supervision.md) | 147 | `7839b0a563e709f6f6a7a7132a3e8ac6e4acdc2effa36fd736f6fb732c6a188d` | V7/V8: preserve post-intent Stop barrier, finite hard deadlines and retained locks on failed cleanup. |
| [docs/milestones/V2.4-notepad-qualification.md](../docs/milestones/V2.4-notepad-qualification.md) | 181 | `f94fe67615fb382d87fa88fdcc4633e2ea3ab125e2ae19722c7a15da9fcde599` | V7.3: installed-version candidate and earlier native observations; no supervised success inferred from isolated byte save. |
| [docs/milestones/V2.5-checklist-workflow-api.md](../docs/milestones/V2.5-checklist-workflow-api.md) | 169 | `88e9ef90be2e40bdf44ea1252f063c3bef96b0f0698292c73663015a2d39be0f` | V7.3B: checklist transport already exists; qualify actual adapter/review rather than recreate an endpoint. |
| [docs/milestones/V3-progress.md](../docs/milestones/V3-progress.md) | 230 | `5ddc6fc8db8c09555752ad131bf05aa3827b434b8e230ab31b56b520aab6e8b4` | Historical V3 consolidation; later individual V3 stages and V5 handoff supersede baseline counts. |
| [docs/milestones/V3.2-3-native-review-dashboard.md](../docs/milestones/V3.2-3-native-review-dashboard.md) | 157 | `88ce866cfb80d0d05b4ce4071ad20060f2a43d4a812c2120658cc40433efa052` | V7.3B/4: bounded owner-held review and checklist UI are implemented; installed native proof still needed. |
| [docs/milestones/V3.4-5-browser-commands.md](../docs/milestones/V3.4-5-browser-commands.md) | 172 | `bc1a4799c05bf68924386d4a620f953d31fb9aada1459de3e3819301a490a8bf` | V7.2/V8.2: fixture admission and durable text clarification exist; model/capability gates remain separate. |
| [docs/milestones/V3.6-reviewed-voice-release.md](../docs/milestones/V3.6-reviewed-voice-release.md) | 131 | `5396d9d6c8aaa195a3995caa38e3f427fbc5c15995cd84d2f67095ae21036b1c` | V8.3/4/V9: reuse CommandService voice flow; eight device components and same-version artifact pair have narrow scope. |
| [docs/milestones/V4-progress.md](../docs/milestones/V4-progress.md) | 239 | `ecbff9dc9cb16ec801ed41596e09ab60e4941cf09d5395fd0fc44f0238e3a122` | V7/V8/V9: existing native session/promotion/readiness/frozen evidence and voice aggregation are not new missing modules. |
| [docs/milestones/V5-progress.md](../docs/milestones/V5-progress.md) | 68 | `ca0384cf5aa2817ac52b199df25272dec36ed874f97d6786fbe1cc2d81ea3cf9` | Latest merged increment: journal completion and Linux/Windows engine discovery fixed; inherited root causes unestablished. |
| [docs/release/README.md](../docs/release/README.md) | 131 | `39c702764175be231b56ea4fc88b7d727c7b3076328ea04cca88b211a3ad8d77` | V9.2–6: exact build/self-test/account/rollback and external frozen qualification procedure. |
| [docs/supported-workflows.md](../docs/supported-workflows.md) | 254 | `677eb0a1bd97472ca15440505bae538d25130efdefd11b2152c6ce9ecae550a0` | V7.0/4/V8.6/V9.6: current-versus-historical capability matrices; prevent stale historical support claims. |
| [evaluation/integrations/README.md](../evaluation/integrations/README.md) | 83 | `f5c87529d4f7910e32667eb327cd7428b49ce0a139bb7c7525245edef493dc8b` | Optional backlog only: narrow MCP/cloud/wake implementation does not grant default availability or wider tool scope. |
| [evaluation/integrations/results-2026-10-17.md](../evaluation/integrations/results-2026-10-17.md) | 35 | `310208806a6c7f51b297ad6e8d4a0d0f5b420e1386d5afc9fbdb87d5745acfdf` | Historical optional-feature fixture results; no real provider/corpus/handoff qualification inferred. |
| [evaluation/reliability/README.md](../evaluation/reliability/README.md) | 67 | `a1b216aba6b694f8be8a42ddbd64f3d0d349cf7d0260fddb5161588dad7f7ac9` | V9.1: original full wall-clock thresholds and measurement boundary; progress/smoke cannot replace final report. |
| [evaluation/reliability/results-2026-10-16.md](../evaluation/reliability/results-2026-10-16.md) | 39 | `7b146783dd83903520c180a80774fe5a5bf71668429cedb2b19b1e448cd46297` | Historical M7 7200.109-second qualified core run; preserve its source hash and limited parent-RSS/STT scope. |
| [evaluation/voice/README.md](../evaluation/voice/README.md) | 69 | `d6e0d69883636ecdd23aa595aefdd237e4fa6f496208abcba32a9d0ae08ff812` | V8.3/4: local CPU/int8 STT, bounded ephemeral audio, explicit review and exact 50+50 plus negative corpus. |
| [evaluation/voice/V3.6-protocol.md](../evaluation/voice/V3.6-protocol.md) | 37 | `bda5a02a0f84b3c964c827724531bf767f27dfc7e93dbd53a85c8c39f6f54ea3` | V8.3/4: voice-origin command pairing, recognition/action separation and witnessed physical audio. |
| [experiments/wake-word-training/README.md](../experiments/wake-word-training/README.md) | 47 | `85bfe83f5a1decef8f201104230ae10dc9afc9175a5bfdafb739d74ca14b929c` | Separate optional backlog: >=100 held-out positives, >=7200 seconds negatives, >=90% recall, <=1 false activation/hour; no wake work is enabled. |
| [outputs/VICTUS-v3-Build-and-Verification-Checklist.md](../outputs/VICTUS-v3-Build-and-Verification-Checklist.md) | 75 | `46db7b4683944cca1de9216524bb572fb557e3b91445338a28f7ad6760e4a1fd` | Retain historical stage/checkbox state; mirror its checklist structure with new unchecked acceptance gates and actual code/evidence prerequisites. |
| [outputs/VICTUS-v3-Incomplete-Work-and-Tests.md](../outputs/VICTUS-v3-Incomplete-Work-and-Tests.md) | 136 | `b6b8228829e4fc6b964e1ba3dfa087f84cb3551a4f611d68b2409d22ef96d414` | Preserve historical deferred work; later instruction to run portable checks controls future implementation. |
| [outputs/VICTUS-v3-Next-Stage-Implementation-Plan.md](../outputs/VICTUS-v3-Next-Stage-Implementation-Plan.md) | 204 | `de0c6d7f8bb66b510592009dacc0e1768367041383614915b8135bed38d5f307` | Retain guide structure: current state, ordered stages, file responsibilities, key logic, acceptance, commands and handoff; skip already implemented modules. |
| [outputs/VICTUS-v4-Build-and-Verification-Checklist.md](../outputs/VICTUS-v4-Build-and-Verification-Checklist.md) | 79 | `dac50718920ded3b7cd97a3906e57bcc14fc3bdd067e0649632845b900f1fbe0` | Retain historical stage/checkbox state; mirror its checklist structure with new unchecked acceptance gates and actual code/evidence prerequisites. |
| [outputs/VICTUS-v4-Markdown-Audit.md](../outputs/VICTUS-v4-Markdown-Audit.md) | 150 | `975c9e24e94d02d3c85a85485ee128937f38ce0796b8cf9fc41dbc1fcd3e2582` | Historical source audit and original scope; this new exact inventory supersedes its file count. |
| [outputs/VICTUS-v4-Next-Stage-Implementation-Plan.md](../outputs/VICTUS-v4-Next-Stage-Implementation-Plan.md) | 204 | `6e1407a77f340ce2aade242d0484a084d5c9d516a2e7da77d32493ed163e58f9` | Retain guide structure: current state, ordered stages, file responsibilities, key logic, acceptance, commands and handoff; skip already implemented modules. |
| [outputs/VICTUS-v4-Revised-Build-and-Verification-Checklist.md](../outputs/VICTUS-v4-Revised-Build-and-Verification-Checklist.md) | 111 | `d7566627ee8172a56e8628941cb18c53bd6e164dd144d1c656af669facff6f76` | Retain historical stage/checkbox state; mirror its checklist structure with new unchecked acceptance gates and actual code/evidence prerequisites. |
| [outputs/VICTUS-v4-Revised-Next-Stage-Implementation-Plan.md](../outputs/VICTUS-v4-Revised-Next-Stage-Implementation-Plan.md) | 329 | `dcfd2ef6a0e0b9294b2636211e251aa0787fa4ee33713daa928cb4e6dd0e7988` | Retain guide structure: current state, ordered stages, file responsibilities, key logic, acceptance, commands and handoff; skip already implemented modules. |
| [outputs/VICTUS-v5-Baseline-and-Carry-Forward-Review.md](../outputs/VICTUS-v5-Baseline-and-Carry-Forward-Review.md) | 114 | `95bdfee38ba2486567e5a7c6dd89794c6a7ca271b5da19cd2a339d87df626e56` | Retain failed V4 full suites and scope distinctions; V5 measured handoff is newer than this starting snapshot. |
| [outputs/VICTUS-v5-Build-and-Verification-Checklist.md](../outputs/VICTUS-v5-Build-and-Verification-Checklist.md) | 137 | `e90e2a340e58f0039983bd1dfbf3a7131cc476091282fb3d1334d1b021bf308f` | Retain historical stage/checkbox state; mirror its checklist structure with new unchecked acceptance gates and actual code/evidence prerequisites. |
| [outputs/VICTUS-v5-Next-Stage-Implementation-Plan.md](../outputs/VICTUS-v5-Next-Stage-Implementation-Plan.md) | 303 | `04580f5de866fe71af4d30141f5f13cd7f38ca7d1ad88e714d9b0ec98c3b7a14` | Retain guide structure: current state, ordered stages, file responsibilities, key logic, acceptance, commands and handoff; skip already implemented modules. |

## 7. Shared invariants

1. Keep `Dispatcher.dispatch_step` as the effect path. Graph nodes call domain services; adapters retain their own loop/thread/COM ownership.
2. Keep one active task, the existing bounded queue and one mutation owner. Failed cleanup retains ownership and latches Stop.
3. Preserve server-created identities, exact scoped permits, single use, expiry and target/content/path binding. A model, transcript or client cannot grant authority.
4. Preserve durable intent/receipt ordering, FULL SQLite durability, persistent budgets and read-only recovery. A possibly applied effect remains unknown until independently reconciled; never replay it automatically.
5. Keep actual production RAM/disk safeguards, exact locks/contracts and local-only model behavior. Missing assets or resource pressure never triggers cloud fallback.
6. Keep implementation, availability, deterministic proof, laptop proof and frozen-package proof separate. Historical counts and negative-admission passes are not positive workflow qualification.
7. Keep raw audio, transcripts, native trees, tokens, credentials, browser profiles and private runtime logs outside exported evidence.
8. Run portable checks during implementation. Mark only truly Windows-dependent work as Windows-skipped; missing model/engine/corpus and unfinished duration/manual work have separate statuses.

## 8. Deliverables and planning validation

Each version has an implementation plan and unchecked build/verification checklist. Existing guides and production files are preserved. New documents use the earlier file-responsibility/key-logic/acceptance/handoff format without full source listings.

Planning verification: exact tracked Markdown inventory, complete per-source treatment/hash coverage, existence of referenced existing implementation owners, same-version checklist/stage coverage, local Markdown-link targets and `git diff --check`. Application test/hardware/model/soak/package campaigns are future implementation work, not run during this planning request.

Optional public-web catalogs, extra applications, custom wake, Hindi/mixed speech, arbitrary MCP, cloud providers, installer/autostart and public distribution remain a separate backlog. Keep private-by-default/local-first behavior and the currently declared authorization boundaries.
