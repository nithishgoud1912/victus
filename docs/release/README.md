# Windows release procedure - 0.1.0 candidate

Current source milestone: [V4 continuation](../milestones/V4-progress.md).
[Test and incomplete-work handoff](../V4-TESTS-AND-INCOMPLETE.md).
The original `dist/windows/Victus` and its M9 evidence are historical. Rebuilds
must select fresh output/work directories; the build now refuses an existing
output. Keep the complete previous folder for the real old-binary rollback.

## Build

Use Windows x64, Python 3.12 and the repository's pinned Node version. Prepare
dependencies with `uv sync --project backend --group packaging --all-extras`,
using `UV_PROJECT_ENVIRONMENT` to select `.local/package-venv` for an isolated
build environment. Then run `scripts/build-windows.ps1` with new `-OutputDirectory`
and `-WorkDirectory` paths. Pass `-SourceManifest` from the source capture script
to bind the new release manifest to exact source/config/contracts/locks. It builds the dashboard,
copies it into the isolated work folder's staging area, draws the small original icon,
freezes the folder bundle and writes a checksummed release manifest.

Output: `OUTPUT/Victus/`. Always transfer the whole directory. The
application is unsigned and requests normal-user execution. Do not move only
the EXE. No installer, scheduled task or startup registry entry is created.
The build downloads libraries only during explicit dependency preparation;
neither build nor first launch downloads model weights or browser engines.

## First launch

Set `VICTUS_API_TOKEN` to a random secret of at least 32 characters in the launch
terminal, and optionally `VICTUS_DATA_DIR` to a writable user directory. Without
an override the application uses `%LOCALAPPDATA%/VICTUS`. Run `Victus.exe doctor`
for safe prerequisite guidance and `Victus.exe serve` to start the loopback
service. Open `http://127.0.0.1:8765` and connect with the session token. No
microphone stream starts until an explicit voice/wake control is enabled.
The token is not a provider key and must not be copied into release reports.

Ollama/models, matching Playwright Chromium, downloaded STT model and qualified
custom wake assets are separately installed prerequisites. Do not copy browser
profiles, credentials, prompt histories or personal data into the application
directory. Review the supported-workflow matrix before relying on hardware or
third-party interactions.

## Package self-test

Run `scripts/package-self-test.ps1 -Bundle PATH -OutputDirectory NEW_PATH`.
It requires PowerShell 7, a free localhost port 8765 and enough available memory
for the production resource policy. It starts only its own hidden processes,
uses a new isolated data root and restores the caller's environment. It tests
the real frozen entry, dashboard/API authentication, one spawned note worker,
instance lock, dependency messages, Stop, offline backup/migration, restore to a
new directory and restart. It never opens a microphone, performs model inference
or accesses public sites. `report.json` is sanitized; service logs are private
local diagnostics and are not part of an export.

Repeat on a **fresh standard Windows account or dedicated test machine** with
no repository/Python/Node environment on PATH. Copy the complete folder and the
self-test script. Record OS/build, app version, manifest hash, standard-user
execution and the sanitized result. Do not claim this gate from this developer
account or from an unelevated token on an existing administrator account.

## Update, migration and rollback

1. Finish work or press Stop, then shut down the service and its workers. Keep
   the previous application folder. Never update files in an active bundle.
2. Run the **old compatible executable** with `backup --destination NEW_BACKUP`
   against its selected data root. Verify the backup manifest and checksums.
   Offline commands refuse a data root whose instance lock is held.
3. Extract the candidate to a new sibling application directory. Run its self-test
   on isolated data first. Confirm it accepts the backup's schema before using
   real data. `migrate` applies pending bundled SQL; newer schemas are rejected.
4. With all work stopped, choose the candidate and the data directory explicitly,
   run `migrate`, start the candidate and verify the required workflows. Do not
   reuse approvals or resume interrupted side effects automatically.
5. For rollback, stop the candidate completely. Use the old executable's
   `restore --source BACKUP --destination NEW_DATA_ROOT`, select the restored root,
   and start the old application folder. Keep the failed candidate's data for
   diagnosis; do not overwrite it or try to downgrade its schema in place.

The self-test rehearses same-version backup/restart/restore. Source tests cover a
schema-6 fixture upgrading to the current schema 8 and rejection of newer schemas. A real
old-version to new-version upgrade/rollback needs both released binaries and
remains a separate gate until such a release pair exists. DPAPI-protected data
may require its original Windows account; portable encrypted-data migration is
not claimed by copying a database to a fresh account.

`scripts/package-upgrade-rollback.ps1 -PriorBundle OLD -CandidateBundle NEW
-OutputDirectory FRESH` exercises two actual preserved executables on isolated
data: old note/backup, candidate migration and verified command, then old restore
and rollback. Its report distinguishes different artifact/schema identities from
a formally versioned release pair. The current application version remains 0.1.0;
milestone numbers are not product release versions. A same-version artifact pair
does not establish a formal cross-version release pass or fresh-account support.

## Evidence and public release

V4's first implementation batch is tracked in
[`V4-progress.md`](../milestones/V4-progress.md). The
[`v4-starting-evidence.json`](v4-starting-evidence.json) report reconciles exact
historical bytes and identifies provenance gaps. It does not promote any native,
browser, voice or release capability. New package self-test reports include
`source_sha256` and `bundle_manifest_sha256`; older reports without those fields
remain historical and are not retrospectively bound by a sibling manifest.

Review only the sanitized JSON and workflow matrix for export. Confirm no host
paths, account names, tokens, prompts, transcripts, credentials or browser session
data appear. Keep build/debug logs local. Checksums identify files; an unsigned
manifest does not authenticate the publisher. Signing, installer UX, autostart
opt-in UI and public distribution are not part of this folder-build milestone.

## V4 qualification records for a frozen candidate

The latest implementation is untested by request; no new frozen build or release
qualification was performed. Source schema-1 records do not enable this candidate.
Schema-2 promotion validates current reports, artifact hashes and verified ledger
receipts. Frozen runtime identity binds the exact release manifest and verifies
its listed files. Unsigned checksums are integrity metadata, not publisher
attestation or a security boundary against another process of the same account.

The package no longer copies source qualification JSON into immutable resources.
Run the actual candidate's `Victus.exe qualify-fixture` / `promote-fixture`, or
its native preparation/repetition/assembly/promotion workflow. Frozen records
are published exclusively under
`%LOCALAPPDATA%/VICTUS/qualifications/<runtime identity>/`. An explicit absolute
`VICTUS_QUALIFICATION_DIR` chooses a different operator-owned root with the same
runtime subdivision. Source mode retains its previous adjacent-module location
unless this override is configured. Never edit a source digest to enable a bundle.

Qualification is per candidate and account. Restart after promotion and separately
prove normal production HTTP/SSE/dashboard behavior. Changing the bundle/profile/
browser invalidates relevant evidence. Keep raw case reports and audio private;
export only sanitized summaries. Missing records leave capabilities unavailable.
