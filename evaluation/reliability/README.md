# M7 memory and reliability

M7 adds explicitly reviewed durable context, linked forgetting, retention, protected task payloads/checkpoints, reviewed diagnostics, verified backups/restores and process-wide resource supervision. It does not load an embedding model, create new action permissions, or add automatic cloud fallback.

## Memory and privacy

The authenticated dashboard's **Memory and diagnostics** section supports reviewed preferences/summaries, editing, forgetting, memory export preview and diagnostic export review. Example planning preferences are `tone=concise`, `language=en`, `date_format=YYYY-MM-DD` and `preferred_editor=notepad`. Other explicit preferences can be retained as context, but they do not become executable authority. Current instructions and application policy always win.

Entries include an ID, type, protected value, human-review provenance, creation/update/confirmation timestamps and optional expiry. SQLite handles ID/type lookup; recall is bounded and expired entries are excluded. The store has a 1,000-entry admission cap. The planner-facing `planning_preferences(task_id)` callback exports only the existing bounded ContextBuilder preference keys and tracks task dependencies. Existing agent integrations can connect it via `preferences=lambda state: services.memory.planning_preferences(state['task_id'])`; no memory is automatically injected as a system instruction.

Forgetting hides the entry and creates a durable deletion job, then purges linked task payloads, approval previews, evidence and complete checkpoint/write/journal rows. A restart retries unfinished deletion jobs. Maintenance waits for task writers to be quiescent and excludes a live graph/checkpointer. Editing replaces the reviewed entry and removes context copies linked to its old value.

User-created workspace outputs are not silently deleted by forgetting memory. Their context references can be removed while the user's files remain. Previously exported memories and older backups can still contain earlier copies; those independent archives require their own deletion decision. Logical deletion and Windows DPAPI protection do not promise forensic erasure or protection against another process running as the same Windows user.

New payloads, checkpoint values, journal results and memory values use the current Windows user's DPAPI identity. Existing payload/journal/JSON checkpoint values are migrated when their stores open. POSIX uses the existing private-file protection contract rather than claiming Windows encryption. Backups containing DPAPI-protected data are intended for restore by the same Windows user; cross-user key migration is outside M7.

## Retention defaults

| Data | Rule |
| --- | --- |
| Preferences and reviewed summaries | Until edited/forgotten or an explicit expiry |
| Graph checkpoints | Seven days after terminal state; pinned terminal threads are retained |
| Task/action metadata | Thirty days after terminal state; pinned tasks are retained |
| Audit events | Thirty days and a 50,000-row cap per event table |
| Evidence files | Session-only by default; seven days when pinned; 250 MiB admission quota |
| Raw task payloads | Short independent expiry: existing argument/output defaults 72 hours, typed text 24 hours; dispatcher payloads explicitly use 24 hours |
| Raw audio | In-memory buffers only, released after transcription/cancellation; not backed up |
| Conversation history | No conversation-history collection is enabled |

Retention runs at startup, session shutdown, every 60 seconds while quiescent, and through authenticated `POST /api/retention/cleanup`. Active writers defer cleanup. Expired payloads are unavailable even before the cleanup pass. Agent observations/evidence payloads are cleared at session end. Legacy terminal records without a retention timestamp receive a conservative timestamp when first observed rather than guessing their age.

Audit task events accept a metadata allowlist; sensitive prompt, goal, transcript, content and argument fields are not persisted through that boundary. Diagnostics use a closed collection of resource counters, rather than trying to scrub arbitrary raw logs. A diagnostic preview is frozen for five minutes and export requires its exact digest plus explicit user review. No credentials, raw prompts, transcript text, device IDs, user paths or memory values are included in the collected diagnostic data.

## Backup and restore

Backups use SQLite's backup API, so committed WAL data is included. Live service backups take a short admission/mutation/checkpointer maintenance window. Only the main database, optional checkpoint database, retained indexed evidence and verified output references are copied. Artifact files must remain within their approved directories, cannot be links/reparse points, and must match their recorded hashes. A manifest records schema versions, sizes and SHA-256 checksums. Browser profiles/sessions, environment/config credentials, raw audio and approval permits are excluded by default.

For an offline backup, stop the service first, then run from the project root:

```powershell
./backend/.venv/Scripts/python.exe -m victus.storage.backups create --source C:/VICTUS-data --destination C:/VICTUS-backups/backup-001
./backend/.venv/Scripts/python.exe -m victus.storage.backups restore --source C:/VICTUS-backups/backup-001 --destination C:/VICTUS-restored-001
```

Choose a new backup directory outside the active data directory. Restore requires a new destination and verifies the listed files before activation. It acquires the destination instance lock before writing, checks schema compatibility, invalidates pending/approved authority, removes permits/previews and marks interrupted task/write effects unknown. Restored agent threads are cancelled. A review marker requires file-root and application-identity revalidation before work resumes. A failed restore is marked and cannot be activated through normal Settings initialization.

Incomplete backup staging directories are not valid archives because they lack a completed manifest/destination publication. Checksums detect accidental damage; they are not a signature proving the identity of an untrusted backup's creator. Do not treat a backup from an unknown source as trusted application state.

## Resource supervision

One process-wide inference slot is shared by reasoning requests and local STT; one mutation slot is shared by execution. The queue keeps its existing maximum of three waiting tasks. Initial context remains 4,096 tokens, and STT remains CPU/int8. New work pauses below 2 GiB available RAM; new mutations also check for at least 64 MiB available disk. Repeated allocation failures latch an inference pause. Pressure never enables a cloud provider.

A background sampler collects available/total RAM and current-process resident memory. Optional NVIDIA telemetry is queried with a timeout and cached; unavailable VRAM readings remain unknown. Read-only health does not perform device/model probes or wait for an inference/mutation slot. Inference timings are bounded to 128 records; STT cold/warm labels track worker model residency, while reasoning labels distinguish first/repeated calls and do not independently prove Ollama residency.

## Tests and soak

Automated tests cover reviewed memory, linked deletion across payload/checkpoint/evidence stores, crash-recoverable forgetting, retention, encrypted-at-rest round trips, WAL backup into a fresh directory, checksum tampering, unavailable destinations, low memory, slot exclusion, diagnostic review and responsive health. Existing worker crash, partial-write, deadline and cancellation tests remain part of the regression suite. Unit tests inject deterministic telemetry; live runs use real host pressure.

The soak harness uses an isolated authenticated local API and disposable workspace. It repeatedly creates verified notes, remembers/recalls/forgets test preferences, performs retention cleanup and checksum-verified backup/restores, optionally transcribes synthetic silence with a downloaded local model, and probes health every half second. It records pressure rejections without bypassing the limits. No physical microphone, browser profile, external submission or real personal memory is used.

```powershell
./backend/.venv/Scripts/python.exe backend/tests/live/m7_soak.py --seconds 7200 --output .local/m7-soak-new --model C:/local-models/faster-whisper-base.en
```

The laptop must remain awake. A shorter `--seconds 30` run validates the harness but **cannot qualify the two-hour requirement**. A qualifying report requires two real wall-clock hours, no recorded failures, at least 100 verified tasks, at least two backup/restores, health p95 below 500 ms, at most 20% growth from warmed resident-memory baseline, and an unchanged backend source hash across the run. Optional STT uses synthetic silence and does not replace M6 acoustic/device qualification.

Reports are written into the chosen output directory: `progress.json` while running and `report.json` after shutdown. The authorized full run `.local/m7-soak-2h/` completed and qualified. See [the measured results](results-2026-10-16.md). Always read qualification from a final report, not an initial progress file.
