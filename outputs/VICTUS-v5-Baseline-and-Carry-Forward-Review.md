# VICTUS v5 — Baseline and carry-forward review

Prepared: 19 October 2026, Asia/Kolkata.
Companions: [Implementation plan](VICTUS-v5-Next-Stage-Implementation-Plan.md) · [Checklist](VICTUS-v5-Build-and-Verification-Checklist.md).

## 1. Review boundary

This review reads the tracked Markdown inventory in the V4 continuation checkout, the current sanitized validation/status JSON, and selected CLI, checkpoint, qualification and live-runner source. It prepares a plan only: no application code, dependencies, tests, model inference, Windows session, recordings, qualification records or package were changed or executed for this planning request.

Local revision: `8e76938a682020cbd7662a167cc62d570bbd19da`. Published equivalent: `550ee86a28095f3bfbc55e4bb0e9b5230d782b16`. Shared tree: `c90ba11ce6570eaeb48f65a18b97c2479d8d2231`. These are different commit identities with identical file trees; neither is an assertion that PR #8 has merged into main.

The V4 Linux summary is the latest checked-in portable result. Older milestones retain their original named source scope. Private raw reports are not required to exist in another clone, and recorded hashes do not reconstruct missing reports.

## 2. Starting facts and their implications

| Retained fact | V5 implication |
| --- | --- |
| Final backend 875/876, serial, SQLite I/O failure | Investigate storage/environment and ownership before declaring baseline green |
| Earlier expanded suite failed journal-crash recovery; isolated/final cases passed | Retain intermittent observation and determine cause; no softened recovery assertion |
| Initial wrong-byte case had missing ledger action; subsequent runs passed | Investigate separately; do not assume all failures share one cause |
| Frontend 23/23, lint/build and real API baseline 23/23 passed | Extend current interfaces; revalidate affected paths rather than rebuild them |
| Seven UI contracts and real dashboard/API smoke passed | UI/backend fixture evidence is useful but does not qualify Windows hardware |
| Alternate Chromium: 10 cases and final 20 repetitions passed | Preserve regression evidence; exact pinned engine and production admission remain open |
| Earlier browser repetition stopped with QUALIFICATION_FAILED | Keep history; final success does not explain the earlier failure |
| Pinned Chromium 156/build1248 archive installation failed | Non-Windows dependency block; explicit preparation or reviewed dependency decision needed |
| No qualification records promoted | Browser/native production capability cannot be claimed enabled |
| Native Stop/tab review/session/promotion/frozen identity tooling exists | Reuse and test actual workflows; do not list these as missing implementations |
| Latest local model runs executed zero inference | MODEL_UNAVAILABLE is unscored; historical 19/30 is not superseded by 0/30 |
| No supplied real labelled speech session | Synthetic tests cannot supply recognition or physical qualification |
| 30.313-second smoke, 4 tasks, 1 restore, no failures | Full 7,200-second / >=100-task / >=2-restore gate remains open |
| No new frozen Windows/fresh-account qualification | Separate source, installed-machine, package and deployment evidence |

## 3. Requirements preserved from earlier guides

- One shared dispatcher, bounded graph, durable request identity and independently verified outcomes.
- Exact scoped ownership and single-use consequential approval; Stop and unknown outcomes do not grant retry authority.
- Owned child/tab/COM boundaries and no interference with restored or unrelated user documents/processes.
- Runtime/profile/engine/artifact/ledger identity validation and no source-to-frozen digest relabelling.
- Normal resource guards, exact locks/contracts, fresh roots and unchanged-source campaigns.
- Frozen model suite and 27/30 gate; recognition and corrected actions reported separately.
- Full two-hour reliability and real Windows/account/package checks; guide numbering is not release versioning.

## 4. Corrections carried into V5

1. Skip only Windows-dependent checks when Windows is unavailable; continue portable tests.
2. Treat missing exact browser, missing model/corpus and incomplete duration/manual work as distinct unfinished gates.
3. Prefer the latest implementation and source-bound evidence over stale instructions to add already-existing promotion/readiness/session tooling.
4. Keep V4 unfinished rather than implying that a new guide number closes it.
5. Place public-web expansion, other applications, wake/languages/MCP/cloud and installer/autostart behind separately selected future scope.

## 5. Markdown source index

Read 52 tracked Markdown files from the starting checkout. This inventory identifies their use in planning; it does not turn historical claims into current test results.

| Source | Lines | Planning treatment |
| --- | --- | --- |
| [README.md](../README.md) | 50 | Current setup/navigation/capability state; V5.0 reconciliation |
| [dashboard/README.md](../dashboard/README.md) | 87 | Current setup/navigation/capability state; V5.0 reconciliation |
| [docs/V4-TESTS-AND-INCOMPLETE.md](../docs/V4-TESTS-AND-INCOMPLETE.md) | 381 | Current carry-forward gate list; V5.0–V5.6 |
| [docs/decisions/001-windows-folder-release.md](../docs/decisions/001-windows-folder-release.md) | 39 | Preserve architecture/ownership/authority decisions; native decision 007 informs V5.3 |
| [docs/decisions/002-shared-execution-path.md](../docs/decisions/002-shared-execution-path.md) | 60 | Preserve architecture/ownership/authority decisions; native decision 007 informs V5.3 |
| [docs/decisions/003-task-event-transactions.md](../docs/decisions/003-task-event-transactions.md) | 43 | Preserve architecture/ownership/authority decisions; native decision 007 informs V5.3 |
| [docs/decisions/004-stop-and-owner-retention.md](../docs/decisions/004-stop-and-owner-retention.md) | 43 | Preserve architecture/ownership/authority decisions; native decision 007 informs V5.3 |
| [docs/decisions/005-notepad-native-profile.md](../docs/decisions/005-notepad-native-profile.md) | 39 | Preserve architecture/ownership/authority decisions; native decision 007 informs V5.3 |
| [docs/decisions/006-gated-checklist-admission.md](../docs/decisions/006-gated-checklist-admission.md) | 34 | Preserve architecture/ownership/authority decisions; native decision 007 informs V5.3 |
| [docs/decisions/007-v4-native-ownership-findings.md](../docs/decisions/007-v4-native-ownership-findings.md) | 73 | Preserve architecture/ownership/authority decisions; native decision 007 informs V5.3 |
| [docs/milestones/9BC-M5-UI.md](../docs/milestones/9BC-M5-UI.md) | 22 | Historical milestone/foundation context; preserve named revision and scope |
| [docs/milestones/M0-feasability.md](../docs/milestones/M0-feasability.md) | 36 | Historical milestone/foundation context; preserve named revision and scope |
| [docs/milestones/M1-5D-5E.md](../docs/milestones/M1-5D-5E.md) | 122 | Historical milestone/foundation context; preserve named revision and scope |
| [docs/milestones/M2-6A-browser-sessions.md](../docs/milestones/M2-6A-browser-sessions.md) | 112 | Browser/native implementation and admission scope; V5.2/V5.3 |
| [docs/milestones/M2-6B-browser-observations.md](../docs/milestones/M2-6B-browser-observations.md) | 147 | Browser/native implementation and admission scope; V5.2/V5.3 |
| [docs/milestones/M2-6CD-network-uia.md](../docs/milestones/M2-6CD-network-uia.md) | 208 | Browser/native implementation and admission scope; V5.2/V5.3 |
| [docs/milestones/M2-6E-workflows.md](../docs/milestones/M2-6E-workflows.md) | 95 | Browser/native implementation and admission scope; V5.2/V5.3 |
| [docs/milestones/M3-7A-model-gateway.md](../docs/milestones/M3-7A-model-gateway.md) | 97 | Persistent execution, budgets and recovery invariants; V5.1/V5.4 |
| [docs/milestones/M3-7B-state-graph.md](../docs/milestones/M3-7B-state-graph.md) | 133 | Persistent execution, budgets and recovery invariants; V5.1/V5.4 |
| [docs/milestones/M3-7C-budgets-progress.md](../docs/milestones/M3-7C-budgets-progress.md) | 112 | Persistent execution, budgets and recovery invariants; V5.1/V5.4 |
| [docs/milestones/M3-7D-routing-context.md](../docs/milestones/M3-7D-routing-context.md) | 135 | Persistent execution, budgets and recovery invariants; V5.1/V5.4 |
| [docs/milestones/M4-8A-approval-records.md](../docs/milestones/M4-8A-approval-records.md) | 89 | Approval, reconciliation and review boundaries; V5.1/V5.3 |
| [docs/milestones/M4-8B-8C-dispatch-review.md](../docs/milestones/M4-8B-8C-dispatch-review.md) | 120 | Approval, reconciliation and review boundaries; V5.1/V5.3 |
| [docs/milestones/M4-8D-reconciliation-recovery.md](../docs/milestones/M4-8D-reconciliation-recovery.md) | 119 | Approval, reconciliation and review boundaries; V5.1/V5.3 |
| [docs/milestones/M9-packaging-release.md](../docs/milestones/M9-packaging-release.md) | 100 | Folder build, account boundaries and rollback; V5.6 |
| [docs/milestones/V2-progress.md](../docs/milestones/V2-progress.md) | 198 | Historical milestone/foundation context; preserve named revision and scope |
| [docs/milestones/V2.1-execution-path.md](../docs/milestones/V2.1-execution-path.md) | 143 | Historical milestone/foundation context; preserve named revision and scope |
| [docs/milestones/V2.2-durable-tasks.md](../docs/milestones/V2.2-durable-tasks.md) | 136 | Persistent execution, budgets and recovery invariants; V5.1/V5.4 |
| [docs/milestones/V2.3-stop-supervision.md](../docs/milestones/V2.3-stop-supervision.md) | 147 | Persistent execution, budgets and recovery invariants; V5.1/V5.4 |
| [docs/milestones/V2.4-notepad-qualification.md](../docs/milestones/V2.4-notepad-qualification.md) | 181 | Browser/native implementation and admission scope; V5.2/V5.3 |
| [docs/milestones/V2.5-checklist-workflow-api.md](../docs/milestones/V2.5-checklist-workflow-api.md) | 169 | Browser/native implementation and admission scope; V5.2/V5.3 |
| [docs/milestones/V3-progress.md](../docs/milestones/V3-progress.md) | 230 | Historical milestone/foundation context; preserve named revision and scope |
| [docs/milestones/V3.2-3-native-review-dashboard.md](../docs/milestones/V3.2-3-native-review-dashboard.md) | 157 | Approval, reconciliation and review boundaries; V5.1/V5.3 |
| [docs/milestones/V3.4-5-browser-commands.md](../docs/milestones/V3.4-5-browser-commands.md) | 172 | Browser/native implementation and admission scope; V5.2/V5.3 |
| [docs/milestones/V3.6-reviewed-voice-release.md](../docs/milestones/V3.6-reviewed-voice-release.md) | 131 | Existing reviewed-speech protocol and hardware limits; V5.5 |
| [docs/milestones/V4-progress.md](../docs/milestones/V4-progress.md) | 239 | V4 implementation/history; latest portable evidence takes precedence for its own tree |
| [docs/release/README.md](../docs/release/README.md) | 130 | Folder build, account boundaries and rollback; V5.6 |
| [docs/supported-workflows.md](../docs/supported-workflows.md) | 233 | Current setup/navigation/capability state; V5.0 reconciliation |
| [evaluation/integrations/README.md](../evaluation/integrations/README.md) | 83 | Separate optional scope; no new default admission |
| [evaluation/integrations/results-2026-10-17.md](../evaluation/integrations/results-2026-10-17.md) | 35 | Separate optional scope; no new default admission |
| [evaluation/reliability/README.md](../evaluation/reliability/README.md) | 67 | Retain stability gates and historical source scope; V5.6 |
| [evaluation/reliability/results-2026-10-16.md](../evaluation/reliability/results-2026-10-16.md) | 39 | Retain stability gates and historical source scope; V5.6 |
| [evaluation/voice/README.md](../evaluation/voice/README.md) | 69 | Existing reviewed-speech protocol and hardware limits; V5.5 |
| [evaluation/voice/V3.6-protocol.md](../evaluation/voice/V3.6-protocol.md) | 37 | Existing reviewed-speech protocol and hardware limits; V5.5 |
| [experiments/wake-word-training/README.md](../experiments/wake-word-training/README.md) | 47 | Separate optional scope; no new default admission |
| [outputs/VICTUS-v3-Build-and-Verification-Checklist.md](../outputs/VICTUS-v3-Build-and-Verification-Checklist.md) | 73 | Earlier implementation-guide structure; do not recreate completed stages |
| [outputs/VICTUS-v3-Next-Stage-Implementation-Plan.md](../outputs/VICTUS-v3-Next-Stage-Implementation-Plan.md) | 202 | Earlier implementation-guide structure; do not recreate completed stages |
| [outputs/VICTUS-v4-Build-and-Verification-Checklist.md](../outputs/VICTUS-v4-Build-and-Verification-Checklist.md) | 79 | Historical design/numbering; rebase on actual V4 implementation |
| [outputs/VICTUS-v4-Markdown-Audit.md](../outputs/VICTUS-v4-Markdown-Audit.md) | 150 | Historical design/numbering; rebase on actual V4 implementation |
| [outputs/VICTUS-v4-Next-Stage-Implementation-Plan.md](../outputs/VICTUS-v4-Next-Stage-Implementation-Plan.md) | 204 | Historical design/numbering; rebase on actual V4 implementation |
| [outputs/VICTUS-v4-Revised-Build-and-Verification-Checklist.md](../outputs/VICTUS-v4-Revised-Build-and-Verification-Checklist.md) | 111 | Historical design/numbering; rebase on actual V4 implementation |
| [outputs/VICTUS-v4-Revised-Next-Stage-Implementation-Plan.md](../outputs/VICTUS-v4-Revised-Next-Stage-Implementation-Plan.md) | 329 | Historical design/numbering; rebase on actual V4 implementation |

## 6. Proposed output and implementation boundary

The companion plan supplies V5.0–V5.6, file responsibilities, dependencies, key logic, acceptance criteria and existing verification entry points. The checklist mirrors those stages with unchecked future gates. The first implementation batch should diagnose persistence, establish a trustworthy portable baseline and then advance the exact-engine fixture path independently of Windows Notepad work.

Only these planning documents are created for this request. Production changes, additional test campaigns and PR updates belong to a subsequent implementation instruction.
