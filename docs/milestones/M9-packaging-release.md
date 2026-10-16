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

## Planned changes and contracts

- `packaging/windows/victus.spec`: PyInstaller onedir Analysis -> EXE -> COLLECT.
- `packaging/windows/entry.py`: frozen/process-safe CLI entry point.
- `packaging/windows/`: asInvoker manifest, version metadata, small local icon.
- `scripts/build-windows.ps1`: dashboard build -> clean staging -> folder bundle.
- `scripts/package-self-test.ps1`: isolated data root -> sanitized JSON evidence.
- `backend/victus/`: frozen paths, launch/diagnostics and release lifecycle support
  only where the real package requires it. Exact changes will be recorded below.
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

Not run yet. Update this section with commands, exact changed files and reports
after execution; never infer hardware qualification from a successful build.

Implemented:
Milestone specification recorded before production changes.
Verified with deterministic tests:
Prior milestone results above; M9 checks pending.
Verified on this laptop:
M9 packaged checks pending.
Verified on public sites:
None for M9.
Still pending:
Folder build, package self-test, update/rollback checks, sanitized release report,
fresh standard-account or dedicated-machine qualification, target hardware checks.
