# M9 - Windows folder bundle and release qualification

## Objective

Create a reproducible folder-based Windows application bundle containing the
dashboard and local backend, then test the packaged boundary without borrowing
qualification from source tests or another Windows account.

## Prior working state

Created before M9 production edits. M8 adds opt-in wake, narrow MCP notes and
reviewed cloud transfers. Full backend regression passed 602 tests; final M8
contracts passed 37, voice/integration focused checks passed 91, frontend tests
passed 20, production build and laptop/mobile browser fixtures passed. Real wake
audio and live cloud qualification remain pending. No packaging pipeline or
fresh-account qualification exists in this checkout yet.

## Exact changed files and contracts

- `packaging/windows/victus.spec`: PyInstaller onedir Analysis -> EXE -> COLLECT.
- `packaging/windows/entry.py`: frozen/process-safe CLI entry point.
- `packaging/windows/app.manifest`, `version-info.txt`, `make_icon.py`,
  `victus.ico`, `release_manifest.py`: asInvoker metadata, icon and checksums.
- `scripts/build-windows.ps1`: dashboard build -> clean staging -> folder bundle.
- `scripts/package-self-test.ps1`: isolated data root -> sanitized JSON evidence.
- `backend/victus/runtime/paths.py`, `runtime/release.py`, `cli.py`, `api/app.py`:
  frozen resources, safe prerequisites and offline maintenance commands.
- `backend/victus/adapters/mcp/client.py`: frozen executable server re-entry.
- `backend/victus/storage/migrations.py`: missing resource/newer schema rejection.
- `backend/pyproject.toml`, `backend/uv.lock`: isolated pinned packaging group.
- `backend/tests/test_packaging_release.py`: nine release boundary tests.
- `.gitignore`: milestone/decision/matrix/release docs now eligible for tracking;
  build/runtime artifacts and raw milestone evidence stay excluded.
- `docs/supported-workflows.md`, `docs/decisions/`, release evidence: versioned
  support claims separated by evidence layer.

Inputs: pinned source/dependency manifests, local toolchain, explicit optional
asset paths and isolated test data. Outputs: folder application bundle, dashboard
static staging, file checksums, sanitized test report and explicit pending gates.
No automatic asset downloads, installation autostart or listening are authorized
by installing or launching the package. Credentials and browser sessions are
excluded from release artifacts.

## Commands and expected results

Build: `scripts/build-windows.ps1` should produce an onedir application with its
adjacent support files and dashboard. Self-test: `scripts/package-self-test.ps1`
should validate the frozen entry, auth, data-root selection, instance exclusion,
missing dependency reporting and stopped maintenance/backup/migration/rollback.
Source regression, frontend tests/build and package-specific tests should pass.
Fresh standard-account/machine qualification is a separate manual release gate.

## Actual evidence

The M9 results below are historical and belong to that original folder artifact.
Current source changes and rebuilt candidate qualification are recorded separately
in [V3.6](V3.6-reviewed-voice-release.md). Do not apply M9 package counts to V3 code.

On 2026-10-17, `scripts/build-windows.ps1` exited 0 and produced
`dist/windows/Victus/` with 973 checksummed files. The real PE resources contain
asInvoker (without requireAdministrator), an icon and version metadata.

`scripts/package-self-test.ps1 -OutputDirectory .local/m9-package-check-01`
passed 17/17 checks on this laptop: entry/version, checksums, staged dashboard,
data-root choice, prerequisite messages, default-off listening/autostart, API
auth, dashboard HTTP, instance lock, frozen note worker, Stop, migration,
consistent backup/restore and restart against a new rollback data root.
An isolated repeat with `VICTUS_MCP_NOTES=1` also passed all 17 checks, qualifying
the packaged pinned MCP note path on this laptop. The repeat used an ignored
local copy of the same test script to select that optional adapter.

Full source regression: **616 passed in 263.300 seconds**, 0 errors/failures/skips
(`.local/m9-regression.xml`). Focused release/storage/adapter checks: **62 passed
in 7.93 seconds** (`.local/m9-unit.xml`). Dashboard build/type regeneration passed;
frontend tests/lint passed. Changed-file Ruff passed. The pinned lock verifies
offline with 97 entries.

Source/build revision and exact fingerprint are recorded in
[V2 progress](V2-progress.md). Local build/service/XML outputs can contain host
paths and remain private. Exportable sanitized evidence is
`docs/release/evidence-0.1.0.json`; the workflow matrix is
`docs/supported-workflows.md`. Implementation source is linked above through
exact file paths. The current production/build files match implementation commit
`64a0a22127a2d450a8d8bb4047cf76cae0cc4995`; remaining changes are documentation.

Implemented:
Milestone specification recorded before production changes; folder build,
metadata/icon/checksums, frozen paths/entry, maintenance and self-test implemented.
Verified with deterministic tests:
616 backend tests; release/storage/adapter checks and frontend checks passed.
Verified on this laptop:
Native and opt-in MCP packaged note paths and 17-check self-tests passed;
same-version stopped backup/migration/restore/restart and PE metadata inspected.
Verified on public sites:
None for M9.
Still pending:
Fresh standard-account/dedicated-machine qualification, a real cross-version
release pair for update/rollback, signing/distribution and target hardware checks.
Same-version rehearsal and a v6->v7 source fixture are not cross-version release
qualification. No physical microphone, GPU inference or public-site test ran.
