# Decision: Windows folder bundle, separate user data and honest release gates

Version: 0.1.0 release candidate. Date: 2026-10-17.

Use PyInstaller onedir first. Keep `Victus.exe`, `_internal/` and the release
manifest together. No single-file executable, installer, startup task, Run key,
elevation request or microphone activation is created by the build.

The frozen entry invokes multiprocessing.freeze_support before importing the
application. The selected local MCP server re-enters that executable through a
closed `mcp-note-server` command instead of treating sys.executable as Python.
Its reviewed source hash is included as a small inspectable resource. This
preserves the same bounded transport and Windows Job Object ownership.

Dashboard files and migration SQL are immutable resources inside the bundle.
Databases, artifacts, browser profiles and settings belong under the selected
user data root (default `%LOCALAPPDATA%/VICTUS`), never under the executable.
Build manifests contain relative paths, versions and checksums; they exclude
credentials, browser sessions, model assets and private payloads. A small
faster-whisper VAD asset is runtime library data, not an STT/wake model download.

Ollama and its pinned model, matching browser engine, local STT assets and
qualified custom wake assets are explicit prerequisites. Nothing is downloaded
at first launch. Library presence and prerequisite file checks are not GPU,
browser-control, microphone or wake-accuracy qualification.

Update uses a sibling application folder and a stopped offline backup. Do not
overwrite a running folder or downgrade a live database. Refuse newer schemas.
Rollback selects the prior executable and restores its matching backup into a
new directory. Instance locks protect offline maintenance. Approval authority is
invalidated by restore, and interrupted effects require independent review.

Same-account laptop checks and source fixtures are recorded separately from a
fresh standard-account or dedicated-machine release gate. An unsigned local
candidate is not represented as a publicly qualified release.

Sources: [PyInstaller runtime paths](https://pyinstaller.org/en/stable/runtime-information.html),
[multiprocessing requirements](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html),
[folder spec construction](https://pyinstaller.org/en/stable/spec-files.html).
