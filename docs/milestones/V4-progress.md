# V4 implementation progress

Stage design recorded 19 October 2026 before production edits. Existing dirty
v2/v3 changes, runtime directories and packages are preserved. Guide numbering
does not change product version or qualify capabilities.

## V4.0 evidence reconciliation

Starting inventory: `.local/v40-start-01/source.json`, 287 implementation/config/
contract/lock files, fingerprint
`b3c8a3f6cc25e6d6537f1ea4418c609e7da9e63aa39c0ada3c73ae87b4f1174e`.
The base revision and complete dirty inventory are alongside it. This matches
V3.6's final inventory. No real user runtime is selected.

Measured gap: the planning snapshot is stale. V3.6's evidence JSON exists now;
its package and actual-artifact-pair results must be bound to private reports,
while its soak remains incomplete. Reconciliation must preserve historical
results and never infer a completed soak from progress.

Affected files: this milestone, supported-workflows matrix, sanitized release
evidence and a repeatable read-only reconciliation runner. Acceptance: exact
report hashes, explicit missing evidence, no private payload export, current
normal-policy note/command/clarification/replay/Stop checks.

Fresh baseline `.local/v40-baseline-01/report.json`: all 14 real authenticated
loopback HTTP/SSE checks pass with normal memory policy; exact note bytes,
deduplication, replay/read-only refresh and Stop verified. This runner does not
yet exercise command intake/clarification; those require an added baseline.

## V4.1 ownership diagnosis

Measured gap: `OWNED_CHILD_UNAVAILABLE` does not distinguish direct launch,
delegation/reuse or timing. Before changing ownership policy, extend bounded
private diagnostics in `adapters/uia/{applications,native}.py`,
`workflows/{diagnostics,qualification}.py`, and focused tests. Record pinned
process identities and window handles before/after the actual worker launch,
without titles, editor contents or private paths. Instrumentation must neither
grant authority nor change the existing child requirement or cleanup ownership.
Acceptance: one fresh supervised attempt; observation-only diagnostic tests;
identify the precise boundary and document any required alternative design.
Do not enable native registration without the full native and review gates.

## V4.2 browser qualification

Measure current resources and run the existing real-Chromium qualification in a
fresh root. Preserve the 2 GiB threshold. If admitted, extend qualification to
20 exact reports, process cleanup and structured/text routes. Bind any promoted
record to relevant source identity as well as fixture/engine/binary. A blocked
attempt is not a capability pass and cannot produce a trusted record.

## Remaining stages

V4.3 requires actual runtime/model inventory before selecting a pin; do not
download or substitute a model implicitly. V4.4 requires 100 consented labelled
real recordings and witnessed physical device operations; no supplied corpus
exists. V4.5 requires final regression, unchanged-source two-hour reliability,
fresh package, fresh standard account and a formally versioned release pair.
These requirements remain open until measured; no completion is inferred from
the implementation of evaluation or release tooling.

### Measured follow-up corrections before final regression

The historical test inventory differs only in a live dashboard contract, so
reconciliation will report application, ordinary-test and live-runner identity
separately. The self-test report lacks its own artifact fingerprint; add that
binding to future package reports without rewriting old results.

The soak runner's `--require-ready` currently checks an unstarted supervisor's
empty cache. Add an explicit fresh telemetry readiness check and test low RAM,
unknown telemetry and stale-cache behavior. Its production 2 GiB threshold and
full-duration gates remain unchanged. Native initial nonempty-editor rejection
needs a specific safe diagnostic code rather than generic ValueError.

## Recorded implementation outcomes

Changed implementation inventory, 290 files:
`.local/v4-final-source-01/source.json`, fingerprint
`636ecbec8eeb8413e724f72845674fa3d018cc332c749b73eef5798db1aecbdd`.
The implementation changed 13 paths relative to the captured starting inventory;
dependency locks and generated API contract bytes did not change.

### Evidence reconciliation

`scripts/reconcile-v36-evidence.py --output-directory <new-private-root>` reads
only the named historical reports, hashes exact bytes, validates stored source
inventory digests and writes an allowlisted summary. Missing reports remain
explicit. Tests cover missing reports, untrusted progress qualification flags,
exact-byte hashes, corrupted inventory digests and non-boolean check values.
`.local/v40-reconciled-02/report.json` is exported as
`docs/release/v4-starting-evidence.json`. Raw reports were not overwritten.

The historical JUnit has 791 passes; application and ordinary-test bytes match
V3.6 final source, but the live dashboard runner differs. The package report has
21 true checks and the actual-artifact pair has eight. Candidate release manifest
SHA-256 `92b5f58fa4bbe74413be62c63b15483e2e7861bd98ecd5b9773159d65414257a`
matches the pair report and final historical source. The self-test lacks an
embedded bundle hash; a sibling manifest cannot supply that missing direct
provenance. Future self-test reports now record source and manifest hashes.

### Current live attempts

- Initial `.local/v40-baseline-01`: 14/14 authenticated real HTTP/SSE checks
  passed; available RAM at start 2,251,935,744 bytes. The extended runner adds
  command graph, exact bytes, explicit clarification, stable replay, read-only
  refresh and Stop, for 23 total checks. `.local/v40-baseline-02` was blocked
  before note admission with HTTP 503; RAM at start 1,401,315,328 bytes. It is not
  a command/clarification pass. No new request identity was used to replay an
  uncertain effect; each baseline uses a new isolated workspace.
- Native `.local/v41-native-one-01`: exact installed executable confirmed,
  cold owned-child binding passed, DPI 120, empty editor and entered-text checks
  passed; Save invoked but UI postcondition failed with
  `WINDOW_MISSING_OR_AMBIGUOUS`; expected file absent on read-only inspection.
  Outcome **unknown**, zero passes. `.local/v41-native-one-02`: new child bound,
  initially nonempty editor refused before writing; zero passes. Specific
  `EMPTY_EDITOR_NOT_PROVED` diagnostic code is now implemented. See decision 007
  for observations and requirements for an alternative editor lease. No native
  registration, app setting change, shared-process termination or manual UI
  mutation was performed. No 20-run batch follows an unverified first success.
  These are diagnosis attempts from earlier source in this turn, not final-source
  qualification: separate per-attempt source manifests were not captured. That
  missing binding is explicit and cannot be used for promotion. Future native
  qualification must capture its inventory before and after each batch.
- Browser `.local/v42-browser-one-01`: real Chromium qualification requested,
  admission blocked by `RESOURCE_PRESSURE`; no browser workflow executed. Final
  observed available RAM 1,288,593,408 bytes. Fixture/browser/engine hashes are in
  the report. Guard remains 2 GiB. No trusted qualification record was promoted.
- Reasoning: installed Ollama executable exists, endpoint unavailable, inspected
  manifest cache contains only `nomic-embed-text:latest`. No reasoning pin can be
  established from that asset. `.local/v43-model-benchmark-01/report.json`:
  frozen suite hash `1a23540e729f3b62f9e0991fd7c53d6cd6e279a514f45f1e4a697949a273e340`,
  requested 30, executed 0, `MODEL_UNAVAILABLE`, no score. Historical 19/30 is
  unchanged. No model download, service/configuration change or cloud fallback.
  `.local/v43-readiness-01/report.json` separately records actual RAM, 6 GiB GPU
  capacity, available disk, executable hash and unavailable service. This is a
  readiness inventory, not an inference or model correctness result.
- Reliability `.local/v45-soak-01/report.json`: requested 7,200 seconds,
  blocked at fresh real-memory preflight, available RAM 739,549,184 bytes,
  elapsed 0, verified tasks 0. This is not a soak pass. The earlier V3.6 soak
  process was observed still running; it was left untouched. Source changed
  during this work, so that earlier run cannot qualify the current source.

### Scope and unresolved requirements

This delivers the plan's first implementation batch and bounded attempts at its
independent browser/model/reliability gates. **V4 is incomplete.** V4.0's full
current-source command baseline is still blocked by memory. Native ownership on
cold launch is observed, but reliable Save, empty new-editor creation, real
HTTP/dashboard review and all native qualification gates remain unresolved.
Browser runs/source-bound promotion, local inference, 100 consented real spoken
trials, witnessed physical-device tests, final two-hour soak, rebuilt package,
fresh standard account and formal release pair remain open. These were not
replaced with fixtures or enabled by configuration. No public sites were tested.

## Final verification for this increment

- Full final-source regression: **804 backend tests passed**, zero failures,
  errors or skips, 420.09 seconds. Command:
  `backend/.venv/Scripts/python.exe -m pytest backend/tests --basetemp=.local/v4-regression-01 --junitxml=.local/v4-regression-01.xml`.
- **23 dashboard tests**, lint and production build passed. Build regenerated
  the OpenAPI/client contract; the resulting bytes match the starting inventory.
- Changed Python paths passed Ruff; the package self-test PowerShell script
  passed syntax parsing. No frozen self-test of a new-source bundle is claimed.
- `.local/v4-final-source-02/source.json` matches final-source-01 exactly:
  `636ecbec8eeb8413e724f72845674fa3d018cc332c749b73eef5798db1aecbdd`.
  Both dependency locks match the starting inventory. The original plan is
  preserved; its separate hash is recorded in the execution evidence.
- After the test workers exited, `.local/v40-baseline-final-03` again refused
  note admission with HTTP 503; measured starting RAM 558,235,648 bytes. The
  final-source 23-check live baseline remains **resource-blocked**. No pressure
  guard was altered to obtain a passing report.

Sanitized current outcomes, exact report/JUnit hashes and explicit incomplete
gates are in [V4 execution evidence](../release/v4-execution-evidence.json).
Historical reconciliation and current execution remain separate. Existing
runtime roots and package artifacts were preserved; nothing was committed,
published or externally transmitted.

## Full-completion continuation — design before edits

User requested full completion and is available to free RAM and participate in
physical checks. Preserve all existing roots and capture another starting
inventory in `.local/v4-complete-start-01`.

Measured code gaps: browser qualification has no source binding and the existing
live runner covers only two positive reports, not the required twenty; no trusted
native qualification loader is wired into bootstrap. Finish strict server-owned
record loading with source/profile/engine/binary binding and tests for missing,
stale, malformed and insufficient evidence. Add a repeatable promotion tool that
only accepts complete matching reports and refuses overwrite. Keep records absent
until all required live evidence exists. Extend the actual browser runner with
20 unique destinations, both command routes, cleanup observations and exact
post-Stop evidence; a partial run cannot qualify.

Native follow-up: capture source around each attempt, diagnose exact Save and
new-editor transitions before selecting a fix, and preserve nonempty sessions.
Physical voice: predeclare thresholds, prepare the real capture/review session
and retain recording/session bindings. Human observations remain necessary.

## PR implementation continuation — tests intentionally deferred

The branch `codex/v4-implementation-handoff` continues the checked-in V4 code.
It adds worker-local native Stop guards and tab/window-bound Save review,
report-backed schema-2 fixture/native promotion, native session preparation and
assembly, owned-descendant browser observation, robust browser failure reports,
external frozen-bundle qualification, local readiness inventory and predeclared
English-note voice qualification aggregation. Root/dashboard/M0 documentation is
updated. The original V4 plan and historical reports are preserved.

The user explicitly requested skipping tests. **No application tests, live
qualification, inference, voice/device session, soak or package build was run.**
Only Python syntax and Git whitespace were inspected. No source/frozen/native/
browser qualification record was installed. Schema-1 records are deliberately
not admitted by schema-2 validation; matching fresh evidence is required.

The exact unrun checks, commands, affected files and incomplete target-machine/
human requirements are in [V4 tests and incomplete work](../V4-TESTS-AND-INCOMPLETE.md).
Actual installed Notepad Save diagnosis still requires Windows observations;
this change does not claim a speculative selector change fixed that failure.
The 804/23 historical result does not validate this continuation. V4 remains an
unqualified implementation candidate until its selected outstanding gates pass.


## Clarified test policy and Linux validation follow-up

The user clarified that only Windows-environment checks should be skipped.
Portable Linux validation now supersedes the initial all-tests-skipped statement.
Backend regression, new evidence/voice/process/Stop tests, pinned-Node frontend
checks, real HTTP/SSE/dashboard flows, explicit alternate-Chromium fixture cases,
20 supervised browser repetitions and a short reliability smoke were executed.
Live model runners were attempted and blocked by missing local inference.

The detailed test counts, fixes, failed full runs, isolated reruns and remaining
Windows/non-Windows gates are recorded in
[V4 tests and incomplete work](../V4-TESTS-AND-INCOMPLETE.md) and its linked
sanitized Linux summary. Do not replace failed full-run outcomes with isolated
passes. No graph/no-replay assertion or production resource safeguard was relaxed.
The exact pinned Chromium installer failed; the identified alternate engine is
regression evidence only. No qualification record was promoted and no Windows
Save/device/build or full two-hour qualification is claimed.
