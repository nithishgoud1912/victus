# VICTUS v4 — Complete Markdown audit

Prepared: 19 October 2026. Repository: nithishgoud1912/victus. Inspected commit: e87b1050217d342551aa1c43da37e2add276336e.

Coverage: all 48 tracked Markdown files, including the empty M0 record. No dependency or generated external documentation is included. This report separates documented historical evidence from current implementation review; private .local reports were unavailable in this clone.

Companions: [Revised plan](VICTUS-v4-Revised-Next-Stage-Implementation-Plan.md) · [Checklist](VICTUS-v4-Revised-Build-and-Verification-Checklist.md).

## Main conclusions

The repository already contains a V4 plan and a partially implemented V4 continuation. Its next increment should complete ownership/Save and qualification plumbing, then measure real workflows. The existing queue, graph, review, command intake, dashboard and voice chain should be extended.

The checked-in V4 summary records 804 backend and 23 frontend passes for a named inventory. This audit ran no application tests and does not extend those results to later continuation code. Current laptop RAM/model availability cannot be inferred from historical measurements.

## Every Markdown file

| File at inspected revision | Analysis and V4 consequence |
| --- | --- |
| [README.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/README.md) | Navigation is stale: later dashboard, command, voice and V4 implementation exists. Replace early milestone-only orientation with current entry points and explicit capability limits. |
| [dashboard/README.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/dashboard/README.md) | Useful authentication/toolchain/type-generation instructions; opening claim that task/approval screens are future work is obsolete. Update current command/checklist/voice UI descriptions and label old counts. |
| [docs/decisions/001-windows-folder-release.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/decisions/001-windows-folder-release.md) | Retain onedir, normal-user execution, separate runtime data and explicit local assets. A same-account self-test remains narrower than fresh-account/release qualification. |
| [docs/decisions/002-shared-execution-path.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/decisions/002-shared-execution-path.md) | Preserve Dispatcher.dispatch_step as the single effect path, trusted worker authority and exact verification. New workflows must not add a second dispatcher. |
| [docs/decisions/003-task-event-transactions.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/decisions/003-task-event-transactions.md) | Preserve atomic lifecycle events, durable deduplication and read-only replay. Retention bounds request mapping; restart does not auto-resume writes. |
| [docs/decisions/004-stop-and-owner-retention.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/decisions/004-stop-and-owner-retention.md) | Preserve Stop-first cleanup, retained failed ownership and final dispatch barrier. New tab/browser qualification must exercise these boundaries. |
| [docs/decisions/005-notepad-native-profile.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/decisions/005-notepad-native-profile.md) | Historical native selector/filename-host/owned-child design remains relevant. Later tab design and cold-launch findings supersede a launch-only account of current blockers. |
| [docs/decisions/006-gated-checklist-admission.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/decisions/006-gated-checklist-admission.md) | Keep narrow transport and shared gate across generic/narrow routes. Historical absent review wiring is now implemented; native qualification still gates production. |
| [docs/decisions/007-v4-native-ownership-findings.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/decisions/007-v4-native-ownership-findings.md) | Latest native diagnosis: owned cold child and text succeeded, Save remained unknown, later editor nonempty. New-tab continuation design is now partly implemented and needs full qualification. |
| [docs/milestones/9BC-M5-UI.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/9BC-M5-UI.md) | Dashboard task/approval/replay/keyboard/mobile implementation already exists. Extend current controls rather than recreating M5; browser fixtures do not prove hardware. |
| [docs/milestones/M0-feasability.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/M0-feasability.md) | Empty, zero bytes. Create a current feasibility record; no feasibility pass can be inferred from this file. |
| [docs/milestones/M1-5D-5E.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/M1-5D-5E.md) | Foundational queue/SSE/Stop/supervision evidence is historical. Preserve single active worker, finite deadlines and unknown-effect semantics; use current baseline runner. |
| [docs/milestones/M2-6A-browser-sessions.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/M2-6A-browser-sessions.md) | Retain owned ephemeral/persistent session contracts and owner-loop restrictions. Early missing browser installation is historical; current engine must be verified afresh. |
| [docs/milestones/M2-6B-browser-observations.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/M2-6B-browser-observations.md) | Retain bounded visible observations, opaque fresh targets, privacy exclusions and independent value readback. Early blocked probe does not establish present readiness. |
| [docs/milestones/M2-6CD-network-uia.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/M2-6CD-network-uia.md) | Keep request-level scope, DNS/IP validation, bounded transfers and COM/process targeting. Documents important public-site/network compatibility limitations; do not promise arbitrary-site support. |
| [docs/milestones/M2-6E-workflows.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/M2-6E-workflows.md) | Earlier real Linux fixture successes and simulated Notepad runs are different evidence. Preserve source counting/exact bytes; current Windows campaign and engine identity need fresh proof. |
| [docs/milestones/M3-7A-model-gateway.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/M3-7A-model-gateway.md) | Gateway/parser implemented; JSON-schema output and exact pins retained. Initial task-wide repair description is superseded by 7C per-decision repair within global budgets. |
| [docs/milestones/M3-7B-state-graph.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/M3-7B-state-graph.md) | Persistent SQLite graph, journal and no-replay semantics already exist. Earlier budget/startup review descriptions are superseded by later 7C/M4 policies. |
| [docs/milestones/M3-7C-budgets-progress.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/M3-7C-budgets-progress.md) | Current general graph budget policy supersedes 7B defaults: bounded active time, per-decision repair, persistent counters and no-progress stop. Narrow command wrapper has its own smaller bounds. |
| [docs/milestones/M3-7D-routing-context.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/M3-7D-routing-context.md) | Historical real model score 19/30, browser 10/10, desktop 0/10, files 9/10; full gate 27/30 remains open. Preserve frozen suite and diagnose F06; no subset relabelling. |
| [docs/milestones/M4-8A-approval-records.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/M4-8A-approval-records.md) | Durable bound records, protected previews and single-use permits already implemented. Integration progressed in later milestones; do not rebuild stores. |
| [docs/milestones/M4-8B-8C-dispatch-review.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/M4-8B-8C-dispatch-review.md) | Exact dispatcher binding/authenticated review and durable interrupt implemented. Its pending-authority-on-restart behavior is explicitly superseded by 8D. |
| [docs/milestones/M4-8D-reconciliation-recovery.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/M4-8D-reconciliation-recovery.md) | Current restart invalidates authority; read-only reconciliation does not rewrite original unknown history or auto-retry effects. Retain fresh proof/review for any allowed retry. |
| [docs/milestones/M9-packaging-release.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/M9-packaging-release.md) | Historical 17-check onedir package and optional MCP note evidence. Does not qualify later source, native/browser/audio, fresh account or formal versioned releases. |
| [docs/milestones/V2-progress.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/V2-progress.md) | Useful historical architecture/qualification inventory, including empty M0 and documentation gaps. Its note-only API/source fingerprint is not the current command-enabled tree. |
| [docs/milestones/V2.1-execution-path.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/V2.1-execution-path.md) | Shared generic execution and trusted worker context already implemented. Retain exact-True verifier, final ledger checks and import-light worker behavior. |
| [docs/milestones/V2.2-durable-tasks.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/V2.2-durable-tasks.md) | Task/event and migration atomicity already fixed without new schema. Preserve replay before destination conflict and startup cancellation/no effect replay. |
| [docs/milestones/V2.3-stop-supervision.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/V2.3-stop-supervision.md) | Stop cleanup, mutation-slot retention and bounded supervisor already hardened. Physical shortcut remains a separate check from synthetic tests. |
| [docs/milestones/V2.4-notepad-qualification.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/V2.4-notepad-qualification.md) | Installed profile and isolated save history explain filename-host choice. No full native workflow qualification; later tab/Save findings must guide current work. |
| [docs/milestones/V2.5-checklist-workflow-api.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/V2.5-checklist-workflow-api.md) | Strict checklist API and simulated effects present. Historical pending review wiring is now implemented; full native Save/repetition/DPI evidence remains missing. |
| [docs/milestones/V3-progress.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/V3-progress.md) | V3 baseline/diagnostics and historical 735-test evidence. Later review/commands/voice exist. Preserve native failure history, but do not treat missing child as sole present blocker. |
| [docs/milestones/V3.2-3-native-review-dashboard.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/V3.2-3-native-review-dashboard.md) | Native review-owner lifecycle, separate gates and checklist UI implemented. Real native qualification is still distinct from simulated 751-test source evidence. |
| [docs/milestones/V3.4-5-browser-commands.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/V3.4-5-browser-commands.md) | Commands, durable clarification and fixture admission implemented. Historical browser/mode availability was resource/model blocked; continuation now adds fuller record/runner code. |
| [docs/milestones/V3.6-reviewed-voice-release.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/V3.6-reviewed-voice-release.md) | Reviewed CommandService speech and separate action evaluator implemented; historical 791-test/21-package/8-pair results. Zero acoustic samples and incomplete new-source release gates remain. |
| [docs/milestones/V4-progress.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/milestones/V4-progress.md) | Primary current progress source: 804/23 recorded increment, resource-blocked positive gates, unknown native Save, unavailable reasoning and explicit incomplete V4. Continuation design is ahead of those result claims. |
| [docs/release/README.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/release/README.md) | Retain onedir/new-root build, normal-user data, offline rollback and fresh-account gate. Update current milestone link and specify source-versus-frozen qualification publication. |
| [docs/supported-workflows.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/docs/supported-workflows.md) | Best consolidated current status, with historical layers below. Keep implementation/enabled/proven dimensions separate; revise current section after new-tab/record continuation is verified. |
| [evaluation/integrations/README.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/evaluation/integrations/README.md) | Wake/MCP/cloud already optional; local tasks do not require them. Preserve narrow bundled MCP and exact-body cloud consent; no automatic fallback. |
| [evaluation/integrations/results-2026-10-17.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/evaluation/integrations/results-2026-10-17.md) | Historical dependency/fixture checks only; no live cloud/wake/audio qualification. Keep outside mandatory V4 core unless explicitly selected. |
| [evaluation/reliability/README.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/evaluation/reliability/README.md) | Existing privacy/retention/backup/resource/soak procedures. Preserve real memory guards and original full-duration metrics; note-only soak cannot qualify new adapters. |
| [evaluation/reliability/results-2026-10-16.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/evaluation/reliability/results-2026-10-16.md) | Actual old 7200.109-second pass, 148 notes, 12 restores, 16 ms p95 and 2.49% parent RSS growth. Valuable historical evidence, not current V4 qualification. |
| [evaluation/voice/README.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/evaluation/voice/README.md) | Capture/STT/review/SAPI bounds and 50+50 evaluation defined. Old note-field-only overview is superseded by general reviewed commands; physical/acoustic proof still missing. |
| [evaluation/voice/V3.6-protocol.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/evaluation/voice/V3.6-protocol.md) | Current English note-only protocol separates recognition and read-only action evidence. Keep operator pairing limitation; broader intents require corresponding labels/verifiers. |
| [experiments/wake-word-training/README.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/experiments/wake-word-training/README.md) | Separate unqualified optional experiment. Preserve provenance, held-out split, >=100 positives/7200 seconds negatives, >=90% recall and <=1 false activation/hour gates. |
| [outputs/VICTUS-v3-Build-and-Verification-Checklist.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/outputs/VICTUS-v3-Build-and-Verification-Checklist.md) | Historical all-open planning checklist; do not infer present absence from unchecked boxes. Current code implements substantial V3 paths. |
| [outputs/VICTUS-v3-Next-Stage-Implementation-Plan.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/outputs/VICTUS-v3-Next-Stage-Implementation-Plan.md) | Formatting model for stage/file/key-logic/acceptance handoff. Preserve structure while avoiding duplicate implementation of commands/dashboard/voice. |
| [outputs/VICTUS-v4-Build-and-Verification-Checklist.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/outputs/VICTUS-v4-Build-and-Verification-Checklist.md) | Original V4 partial status with checked evidence work and open live gates. Some unchecked coding tasks now have continuation implementations requiring fresh verification. |
| [outputs/VICTUS-v4-Next-Stage-Implementation-Plan.md](https://github.com/nithishgoud1912/victus/blob/e87b1050217d342551aa1c43da37e2add276336e/outputs/VICTUS-v4-Next-Stage-Implementation-Plan.md) | Existing V4 plan, retained unchanged. Revise stale missing-evidence and absent-loader/short-runner assumptions using current code; preserve stages and inherited gates. |

## Important precedence and contradictions

| Earlier description | Current interpretation |
| --- | --- |
| Root/dashboard README: task and approval screens are future work | Later M5 and V3 source includes them; update entry documentation |
| M3 7A/7B: one repair task-wide and earlier action limits | 7C defines later general policy; narrow command wrapper has separate smaller limits |
| M4 8C: retain pending review on startup | 8D invalidates old authority; no resumed possible effect |
| V2/V3: native review wiring is pending | V3.2/3 implements it; real native review proof is still pending |
| Original V4: V3.6 evidence missing | Evidence file exists at this commit; retain missing-file statement as historical only |
| Original V4: native loader absent and browser runner only short positive coverage | Current qualification_records.py/bootstrap and 20-run fixture_qualification.py are present |
| Native blocker only OWNED_CHILD_UNAVAILABLE | Cold child has been proved; Save/UI postconditions and restored documents remain unresolved |
| Historical model 19/30 versus zero executed later | 19/30 is a measured old score; zero executed is unavailable and unscored |
| Historical two-hour M7 pass | Source-specific old proof; current V4 still needs its own final run |
| Product 0.1.0 artifacts at schemas 7 and 8 | Actual-artifact rehearsal; formal cross-version release remains separate |

## Current implementation cross-checks

| File or area inspected | Finding | Plan action |
| --- | --- | --- |
| adapters/uia/applications.py and candidate JSON | New-tab control/container, added-tab inventory and selected-tab/window lease already implemented; two focused tests present | Extend lease/Stop/transition coverage and qualify real Save |
| workflows/qualification_records.py and bootstrap.py | Native/fixture record loading, >=20 counts, runtime binding and native bootstrap wiring exist | Harden complete report validation and add native promotion workflow |
| workflows/fixture_qualification.py and live v34 entry | Default 20 runs alternating routes, real Chromium with TestClient and injected trusted registration | Improve error reports, timeout/cleanup attribution, then add ordinary real-socket production tests |
| workflows/fixture_qualification.py failure paths | Startup discovery precedes main guarded block; final executable hashing can raise for missing binary | Guarantee bounded failure reports with unavailable hashes explicit |
| workflows/qualification_records.py runtime_identity and packaging/windows/victus.spec | Source and frozen identities intentionally differ; source qualification JSON may be copied into bundle | Design actual frozen-bound qualification and publication; do not manually rebind source evidence |
| workflows/qualification.py | Generic native repetition report records runtime start/end, but lacks complete native admission-case evidence and physical-scale certification | Build validated aggregate native session/promotion around current runner |
| scripts and CLI | Source capture, qualify-fixture/promote-fixture, build/self-test/actual-pair tools exist | Reuse confirmed commands; proposed native promotion has no existing command yet |

## Review scope and verification

All 48 Markdown files were retrieved at the pinned revision and inspected. Selected production/test/config/release files were read to resolve documentation drift. No production code, dependency locks, runtime settings, public GitHub files or existing plans were changed. Only the three new planning documents were added locally. No Windows/native/audio/model/package qualification was run.

## Source document fingerprints

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| README.md | 1883 | 67df7c70a1c659df1a1c0f0b5d9244656b9b605d8f2be0cbdfec1fe6993a200b |
| dashboard/README.md | 4445 | ef17b50909d03aea0a8ea18b87b668af4f059b47f003265910e3882acf6846f3 |
| docs/decisions/001-windows-folder-release.md | 2386 | fb048e4ef2546c38f7eef1e404dfffcef4f7642028722bdb95479193faa4587d |
| docs/decisions/002-shared-execution-path.md | 3850 | 696f9ce42b40d694f46f475e3397b1185e6aeac01b148e845587b55246e881a1 |
| docs/decisions/003-task-event-transactions.md | 2665 | 4e80a261b009250e47903d2d69a2963ce0ea34eafd1461cbd5e2a6cb4f8b6065 |
| docs/decisions/004-stop-and-owner-retention.md | 2742 | f63729309d26445e6397b954d1079bacdfd14d458cd8a46a1a85e53873cf4b49 |
| docs/decisions/005-notepad-native-profile.md | 2558 | a146a619177031f7b0b38405e5630121c23a90ff37210100afcaaaedee3cbe52 |
| docs/decisions/006-gated-checklist-admission.md | 2098 | 31756b466b405fa7fc2fa899f991c04c855f1e3a49fa1056e7ab9beee907b65f |
| docs/decisions/007-v4-native-ownership-findings.md | 4523 | ef67d5b0a6100ec925438f106e2ea66356eec04d3471be8ae03b828eb730c351 |
| docs/milestones/9BC-M5-UI.md | 3088 | eadc38401ed80e972a1b95d515b931fcd8d5f7f6466e913cf205c29679258b27 |
| docs/milestones/M0-feasability.md | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| docs/milestones/M1-5D-5E.md | 6942 | 659d9098253655beb0cd2e9c42bb118881453e48b40d6899b0f5be3214f855d1 |
| docs/milestones/M2-6A-browser-sessions.md | 6021 | 509d1cebb97b5c3d3620c94fcfb5cad6a2715e5c25961f9ace7041d3febcbbfc |
| docs/milestones/M2-6B-browser-observations.md | 9248 | c440c532ece32e8c80ad00fcac5724663b14f3fbec106ba9190fa37109a1fdeb |
| docs/milestones/M2-6CD-network-uia.md | 13886 | 03f80b3c541f1d5533de6501f75848993b728e2ad1ab707e59c4f45afc598a61 |
| docs/milestones/M2-6E-workflows.md | 6205 | a6c0e1546572d2e45d7b6a9f5aaeb1d725a3f4ebe46637307f6af2980ae451b6 |
| docs/milestones/M3-7A-model-gateway.md | 5819 | 38cb51f6dbd2f6474160f5ff93725c38b74bdd76415ddba8ea5a1f17eeb832fa |
| docs/milestones/M3-7B-state-graph.md | 8587 | 4447153cb26fde3a6737e6cd5053d8359db9f8f92621aba177e33851e31d55b8 |
| docs/milestones/M3-7C-budgets-progress.md | 6588 | 65853da508ddead66a188164df6f17b3ae828ad63cb930ba5d9d75159b007354 |
| docs/milestones/M3-7D-routing-context.md | 7927 | 3aef6cb659fcf0eec95e9e40062e3cdb52488fb994029ee3d1dc028e211fd52c |
| docs/milestones/M4-8A-approval-records.md | 4927 | 1c9bd18ce182b757725688e78127955623a61de9093e359d2d85e8e30e645bb1 |
| docs/milestones/M4-8B-8C-dispatch-review.md | 6908 | 46d110b998bc95c131dd693c855ed6ccce09a8b7a9e502ba9af1fa27c8202497 |
| docs/milestones/M4-8D-reconciliation-recovery.md | 7007 | 06a34aee050ecec4df9f437af067489e2b8b67720172ad9a1a60d88d4b08f094 |
| docs/milestones/M9-packaging-release.md | 5754 | 24d0e88bd4fcd0b9c6c4f3dd81147195702410de419cbf0e11a6d4e191ed24b0 |
| docs/milestones/V2-progress.md | 14551 | b391fd5515e63b4878daa2c35ea500d526d44420fe34e4fc875598710f3adab5 |
| docs/milestones/V2.1-execution-path.md | 7965 | a937c930a4e1848708787c50325fc2091e40c10146b84aafea4f1a375b7a483b |
| docs/milestones/V2.2-durable-tasks.md | 8070 | e552819085baf0a41bb6b59f478f22a142b5e36a714ffe8c5505a2917ea4dfa8 |
| docs/milestones/V2.3-stop-supervision.md | 8761 | 7839b0a563e709f6f6a7a7132a3e8ac6e4acdc2effa36fd736f6fb732c6a188d |
| docs/milestones/V2.4-notepad-qualification.md | 11680 | f94fe67615fb382d87fa88fdcc4633e2ea3ab125e2ae19722c7a15da9fcde599 |
| docs/milestones/V2.5-checklist-workflow-api.md | 11290 | 88e9ef90be2e40bdf44ea1252f063c3bef96b0f0698292c73663015a2d39be0f |
| docs/milestones/V3-progress.md | 14770 | 5ddc6fc8db8c09555752ad131bf05aa3827b434b8e230ab31b56b520aab6e8b4 |
| docs/milestones/V3.2-3-native-review-dashboard.md | 11250 | 88ce866cfb80d0d05b4ce4071ad20060f2a43d4a812c2120658cc40433efa052 |
| docs/milestones/V3.4-5-browser-commands.md | 10718 | bc1a4799c05bf68924386d4a620f953d31fb9aada1459de3e3819301a490a8bf |
| docs/milestones/V3.6-reviewed-voice-release.md | 8567 | 5396d9d6c8aaa195a3995caa38e3f427fbc5c15995cd84d2f67095ae21036b1c |
| docs/milestones/V4-progress.md | 12025 | 969acbe21f5e6c997cfed74465e0702916e7911746b98dd5bf54069c827b5a37 |
| docs/release/README.md | 6566 | 7e53622f3939e786a2e7e2462c54de591fc4335ceefb76283febf48d4703e2ae |
| docs/supported-workflows.md | 20144 | e7f40d2461df638a226fedd7cfa08761b0d8b200a891004455a722b342d9e99f |
| evaluation/integrations/README.md | 5048 | f5c87529d4f7910e32667eb327cd7428b49ce0a139bb7c7525245edef493dc8b |
| evaluation/integrations/results-2026-10-17.md | 2135 | 310208806a6c7f51b297ad6e8d4a0d0f5b420e1386d5afc9fbdb87d5745acfdf |
| evaluation/reliability/README.md | 9283 | a1b216aba6b694f8be8a42ddbd64f3d0d349cf7d0260fddb5161588dad7f7ac9 |
| evaluation/reliability/results-2026-10-16.md | 2707 | 7b146783dd83903520c180a80774fe5a5bf71668429cedb2b19b1e448cd46297 |
| evaluation/voice/README.md | 10093 | d6e0d69883636ecdd23aa595aefdd237e4fa6f496208abcba32a9d0ae08ff812 |
| evaluation/voice/V3.6-protocol.md | 2656 | bda5a02a0f84b3c964c827724531bf767f27dfc7e93dbd53a85c8c39f6f54ea3 |
| experiments/wake-word-training/README.md | 3130 | 85bfe83f5a1decef8f201104230ae10dc9afc9175a5bfdafb739d74ca14b929c |
| outputs/VICTUS-v3-Build-and-Verification-Checklist.md | 4244 | 29c47debc5d310462fe6c80d0eb6a18ba88a4fa6bb67396209c84e85be89824b |
| outputs/VICTUS-v3-Next-Stage-Implementation-Plan.md | 19196 | b592c68ab1b3409d1040d7ee502a016bf19728a9d5bfe2175e7977ec9a3b2698 |
| outputs/VICTUS-v4-Build-and-Verification-Checklist.md | 5426 | dac50718920ded3b7cd97a3906e57bcc14fc3bdd067e0649632845b900f1fbe0 |
| outputs/VICTUS-v4-Next-Stage-Implementation-Plan.md | 24242 | 6e1407a77f340ce2aade242d0484a084d5c9d516a2e7da77d32493ed163e58f9 |
