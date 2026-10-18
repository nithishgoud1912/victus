# V2.0 progress - current baseline

Recorded: 2026-10-17, Asia/Calcutta. Application version: **0.1.0 candidate**.
This baseline inventories the existing implementation; it does not replace it.
Only the V2 section 5 baseline instructions were supplied in this turn. Its
referenced section 2 list was not included, so the actual milestone inventory
below was reviewed instead. Unseen later V2 stages are **unassessed**, not absent.

## Revision and runtime roots

- Git base: `64a0a22127a2d450a8d8bb4047cf76cae0cc4995`.
- Working tree: **documentation changes pending**. The current implementation,
  build scripts, package specification and dependency files match this HEAD;
  M5-M9 implementation is already present in that commit. V2 changes are the
  progress report and updates to release/matrix documentation, not replacements
  of production modules. A separate content fingerprint preserves exact identity
  independently of documentation edits.
- Current production/build source fingerprint: `43d7eee05bf12b9d7fb3f728aa57675ac2cbc5ff188fe43d9c785ae781cc1794`.
  The file-by-file manifest is `.local/v2-baseline-source.json`; no environment
  files, API tokens or runtime payloads are included.
- Project: `C:\Users\HP\Desktop\Automations\victus`.
- Normal product data root: `VICTUS_DATA_DIR` when explicitly configured;
  otherwise `%LOCALAPPDATA%\VICTUS`. The launch environment determines LOCALAPPDATA.
  The restricted tool environment resolves it inside its sandbox account, so it
  must not be silently treated as the ordinary desktop user's production data.
- Current packaged baseline test root:
  `C:\Users\HP\Desktop\Automations\victus\.local\m9-package-check-01\data`.
  Restored rehearsal root is the sibling `rollback-data` directory. These are
  isolated fixtures; no personal runtime root was selected or overwritten.
- Bundle: `dist/windows/Victus/`, including `_internal/` and release manifest.
  Dashboard staging: `build/windows-staging/dashboard/`. Runtime data is outside
  this immutable application folder.

## Files read and architecture preserved

Read `backend/pyproject.toml`, parsed the entire `backend/uv.lock`, and read
`backend/victus/settings.py`, `cli.py`, `api/app.py`, and `bootstrap.py`.

Python supports >=3.11,<3.13 for the core; this Windows build uses 3.12.14.
Lock format 1/revision 3 contains 97 package entries. Key pins: langgraph 1.2.15,
langgraph-checkpoint-sqlite 3.1.2, Playwright 1.64.0 and PyInstaller 6.22.3.
The optional Windows/Python 3.12 wake combination pins openwakeword 0.6.0,
numpy 2.5.4, onnxruntime 1.31.0, scipy 1.18.1 and scikit-learn 1.9.1.

The CLI serves loopback port 8765 and includes doctor, version, offline backup,
restore and migrate commands. Session/API auth stays server-owned. Public task
creation accepts **only `fs.create_note` with strict filename/text arguments**;
the presence of graph/browser/UIA modules does not expose general natural-language
computer control through this API. Services acquire an instance lock, recover
task/approval authority, own the queue and resource limits, and keep voice/wake,
MCP and cloud opt-in. Reload does not submit a task or approve an action.

## Stage inventory

Status vocabulary: **present and verified**, **present but unqualified**,
**incomplete**, **absent**. Verification here always names its evidence layer;
it does not imply general deployment support.

| Stage | Status | Evidence and remaining scope |
|---|---|---|
| M0 feasibility record | Incomplete | `M0-feasability.md` exists but is empty. A completed feasibility record is absent; no replacement was invented. |
| M1 local foundation, queue, events, Stop | Present and verified | Current backend regression plus real packaged note/readback, auth, instance lock and Stop. Scope is the original workspace-note workflow. |
| M2 browser sessions, targets, network/transfers, native UIA | Present but unqualified | Current deterministic contracts; historical local browser fixture runs. Native Notepad 20-run/DPI gate is outstanding; historical browser version mismatch was documented. No current arbitrary/public-site qualification. |
| M3 gateway, graph, budgets, routing/context | Present but unqualified | Current deterministic tests; historical live schema samples 6/6. Frozen 30-goal benchmark scored **19/30**, below the **27/30** gate: browser localhost 10/10, native desktop 0/10, file/mixed 9/10. Do not count the 19/20 subset as a full pass. |
| M4 approvals, permits, reconciliation/recovery | Present and verified | Deterministic expiry/denial/reuse/content-change/Stop/unknown-effect fixtures. This does not qualify arbitrary external submissions; the ordinary note API is narrower. |
| M5 dashboard/accessibility/reconnect | Present and verified | Build, 20 frontend tests, laptop/mobile browser fixtures; packaged dashboard HTTP and authenticated API. Native hardware control remains separate. |
| M6 push to talk, local STT, reviewed submit, SAPI | Present but unqualified | Deterministic ownership/deadline/review/playback tests. Physical microphone/disconnect/assistant-speech cases and 50 quiet +50 noisy labelled commands are still missing. No Hindi/mixed-language claim. |
| M7 memory, retention, backup, resources | Present and verified | Current source regression and packaged backup/restore. Historical M7 two-hour soak passed **7200.109s**, 148 notes, 232 memory cycles, 12 restores, no recorded failures. That soak qualifies its older source hash, not the post-M8/M9 revision. |
| M8 wake | Present but unqualified | Windows package/import/CPU ONNX spike and deterministic lifecycle tests. No qualified custom model, 100 positive clips or 7200 seconds realistic negative audio. Remains off. |
| M8 selected MCP notes | Present and verified | Source native/MCP contracts and supervised subprocess tests; a second isolated packaged run with MCP notes enabled passed all 17 checks. Only the bundled pinned note capability is admitted. |
| M8 optional cloud | Present but unqualified | Exact-body consent, denial, expiry, budgets, timeout/quota and malformed-output fixtures pass. No live provider/key/data transfer was tested. Off by default. |
| M9 folder packaging | Present but unqualified | Folder build and same-account laptop self-test pass, including a frozen note worker and stopped maintenance/restore/restart. Fresh standard account/dedicated machine and real prior-release upgrade/rollback pair remain outstanding. |
| Installer, single-file packaging, autostart installer | Absent | Intentionally not introduced by the folder-build milestone. No startup registration or background listening is installed. |
| V2 section 5 baseline | Present and verified | Requested inventory recorded, existing files retained, and original note path still verified through the packaged executable. |

## Exact command results

| Command | Actual result | Evidence |
|---|---|---|
| `git rev-parse HEAD` | Base revision shown above; dirty tree | Current inspection |
| `backend/.venv/Scripts/python.exe -m pytest backend/tests --basetemp=.local/m9-regression --junitxml=.local/m9-regression.xml` | **616 passed**, 0 failed/errors/skips, **263.300s** | Local XML; keep hostname-bearing raw XML private |
| Focused release/storage/MCP tests | **62 passed in 7.93s** | `.local/m9-unit.xml` |
| `scripts/build-windows.ps1` | Exit 0; onedir EXE + support folder +973 checksummed files | `.local/m9-build.log` (private build paths), bundle manifest |
| `scripts/package-self-test.ps1 -OutputDirectory .local/m9-package-check-01` | Exit 0; **17/17 checks true** | `.local/m9-package-check-01/report.json` |
| Same package self-test with optional MCP notes enabled | Exit 0; **17/17 checks true** | `.local/m9-package-mcp-check/report.json` |
| Dashboard build during packaging | Type generation + production bundle passed | Build log; static staging |
| `npm --prefix dashboard test` and `npm --prefix dashboard run lint` | **20 passed**, lint passed on baseline inspection | Current command output; no frontend source changes in M9 |
| M5-M8 browser contract scripts | Passed on latest dashboard source | `.local/9bc-browser/`, `m6-browser/`, `m7-browser/`, `m8-browser/` reports |
| `uv lock --check --offline --project backend --cache-dir .local/uv-cache` | Exit 0; resolved 97 entries | Current command output |

The packaged self-test verified bundle hashes/version metadata, entry version,
dashboard staging/data paths, explicit prerequisite messages, no autostart or
listening, unauthenticated rejection and authenticated health, dashboard HTTP,
disabled voice without assets, instance exclusion, the frozen worker's exact note
result, Stop before maintenance, schema 7, backup/restore and rollback-root restart.
It did not perform GPU inference, public browsing, physical audio or cross-account
access. Actual free RAM recovered enough for the guarded note operation; the
production 2 GiB threshold was never bypassed.

## Documents reviewed

- `M0-feasability.md` (empty), `M1-5D-5E.md`.
- `M2-6A-browser-sessions.md`, `M2-6B-browser-observations.md`,
  `M2-6CD-network-uia.md`, `M2-6E-workflows.md`.
- `M3-7A-model-gateway.md`, `M3-7B-state-graph.md`,
  `M3-7C-budgets-progress.md`, `M3-7D-routing-context.md`.
- `M4-8A-approval-records.md`, `M4-8B-8C-dispatch-review.md`,
  `M4-8D-reconciliation-recovery.md`, `9BC-M5-UI.md`.
- `M9-packaging-release.md` and the existing M6/M7/M8 evidence under
  `evaluation/voice/`, `evaluation/reliability/`, `evaluation/integrations/`.

Dedicated M6/M7/M8 milestone filenames were missing at inventory time. Their
implementation/evidence exists elsewhere; this is a documentation gap, not an
absent implementation. Earlier milestone counts are historical results and must
not be substituted for the current revision's actual qualification gates.

## Next implementation versus qualification

**Qualification/review needed first:** native Windows app/profile/DPI runs,
the full 30-goal model benchmark, labelled acoustic set and device/echo cases,
wake model/corpus qualification, actual cloud provider behavior if enabled,
fresh standard-account package test and a real cross-version release pair.

**Known incomplete/absent work:** feasibility documentation, missing dedicated
M6/M7/M8 milestone records, consistent detailed health reporting (the normal
health endpoint does not independently prove model/microphone/browser/worker
readiness), and any later V2 features not supplied for assessment. Broad tasks
cannot be enabled merely by relabelling the existing note endpoint. New product
work needs its own reviewed scope rather than replacing these modules wholesale.

Implemented:
Baseline inventory, explicit runtime/test roots, source identity and evidence map.
Verified with deterministic tests:
616 current backend tests and the targeted release/storage/adapter checks.
Verified on this laptop:
Folder build and 17 packaged checks, including original note/readback and Stop.
Verified on public sites:
No new public-site verification. Localhost fixtures are not public-site evidence.
Still pending:
The qualification and documentation gaps listed above; no general “working” or
fully released status is claimed. No project files were replaced because of V2.

## Subsequent V2.1 work

The inventory above records the baseline before V2.1 edits; its source fingerprint
and packaged checks are historical, not a claim that the current working tree
still matches that baseline. See [V2.1 execution path](V2.1-execution-path.md) for
the strict generic task transport, shared dispatcher, trusted identity/resource
context and current verification. Existing note/voice contracts remain intact.
The default registry now contains only the implemented note tool. The existing
M9 executable has not been rebuilt to contain V2.1 changes.

## Subsequent V2.2 work

The [V2.2 task/queue/event qualification](V2.2-durable-tasks.md) inspected the
existing durable admission, request mapping, bounded scheduler and ordered
replay/live path before editing production code. It fixes atomic lifecycle
state/event writes and atomic migration/schema-version writes without changing
tables or schema version. Forty-two focused storage/queue checks and the dashboard
build, 20 frontend tests and Chromium refresh/reconnect contracts passed; all
659 backend tests and the real source dashboard note/session/mobile check also
passed. Source fingerprints and current qualification
belong to that milestone; the baseline inventory and old package remain historical.

## Subsequent V2.3 work

The [V2.3 Stop/ownership milestone](V2.3-stop-supervision.md) preserves existing
cancellation, spawned worker and native owner boundaries. It adds Stop-first
cleanup that continues despite optional faults, retains process/mutation/runtime
ownership after failed cleanup, bounds slot waiting and execution with one
operation budget, and checks Stop after durable intent before adapter entry.
Eighty-eight focused checks and 20 frontend tests/build/lint plus keyboard Stop
browser contracts passed. All 672 backend tests and real source note/session/
reload/mobile checks passed on the final source fingerprint.
Physical global-key qualification remains separate from synthetic backend fixtures.

## Subsequent V2.4 work

The [installed Notepad qualification](V2.4-notepad-qualification.md) adds a pinned
JSON candidate, exact class selectors, bounded direct-child ownership with a
read-only lease, scoped nested Save As lookup and an immediate empty-editor
guard. Native editor/menu/dialog inspection and one isolated exact-byte save
passed. Full supervised native runs remain unverified; background process reuse
blocks without input. The candidate is **present but unqualified** and is not
enabled in bootstrap. See that milestone for current tests and unresolved gates.

## Subsequent V2.5 work

The [workflow/API milestone](V2.5-checklist-workflow-api.md) adds the narrow
authenticated checklist transport, a server-owned profile gate and atomic
pre-admission destination checks that preserve duplicate-request replay. Save
rechecks the approved basename, cancellation immediately before native Save and
the actionable editor as well as exact bytes. The HTTP adapter is tested with
simulated UIA only. Production continues to expose only the original note tool;
native review wiring/profile/workflow qualification remain required before
enabling any HTTP desktop action. Current source note/API/Stop checks passed with
the normal memory safeguard enabled. No native completion claim replaces the
unresolved V2.4 evidence.
