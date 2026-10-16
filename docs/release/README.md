# Windows release procedure - 0.1.0 candidate

## Build

Use Windows x64, Python 3.12 and the repository's pinned Node version. Prepare
dependencies with `uv sync --project backend --group packaging --all-extras`,
using `UV_PROJECT_ENVIRONMENT` to select `.local/package-venv` for an isolated
build environment. Then run `scripts/build-windows.ps1`. It builds the dashboard,
copies it into `build/windows-staging/dashboard`, draws the small original icon,
freezes the folder bundle and writes a checksummed release manifest.

Output: `dist/windows/Victus/`. Always transfer the whole directory. The
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
schema-6 fixture upgrading to schema 7 and rejection of newer schemas. A real
old-version to new-version upgrade/rollback needs both released binaries and
remains a separate gate until such a release pair exists. DPAPI-protected data
may require its original Windows account; portable encrypted-data migration is
not claimed by copying a database to a fresh account.

## Evidence and public release

Review only the sanitized JSON and workflow matrix for export. Confirm no host
paths, account names, tokens, prompts, transcripts, credentials or browser session
data appear. Keep build/debug logs local. Checksums identify files; an unsigned
manifest does not authenticate the publisher. Signing, installer UX, autostart
opt-in UI and public distribution are not part of this folder-build milestone.
