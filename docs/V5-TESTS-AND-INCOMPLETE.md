# V5 implementation — verification and incomplete work

Prepared: 19 October 2026, Asia/Kolkata.
Branch: `codex/v5-implementation`.
Base: `20ef56946d8b253cc12ed02e6ca5002508671ef4`, containing merged PRs #8 and #9.
Plan: [V5 implementation guide](../outputs/VICTUS-v5-Next-Stage-Implementation-Plan.md).

## Implemented in this increment

| Location | Behavior |
| --- | --- |
| `backend/victus/storage/checkpoints.py` | Atomic one-time completion of an existing unfinished node claim; missing or already-complete claims raise instead of silently succeeding or replacing durable results. FULL durability and no-effect-replay behavior are preserved. |
| `backend/victus/runtime/storage_diagnostics.py` | Finite explicit diagnostic in a new isolated root: spawned process commits then hard exits, parent reopens and consumes the journal, checks SQLite integrity/WAL/FULL, preserves partial/interrupted results and safe SQLite error metadata. No user runtime is selected. |
| `backend/victus/cli.py` | `victus storage-check --output NEW_DIRECTORY --repetitions N`, with 1–20 repetitions; never promotes evidence or claims release qualification. |
| `backend/victus/adapters/playwright/installation.py` | Windows/Linux canonical Chromium revision/layout from the installed locked Playwright descriptor and cache configuration, without launching a driver/browser or downloading assets. Missing, linked, relative or unsupported layouts are refused. |
| `backend/victus/workflows/fixture_research.py` | Production browser discovery checks the canonical installed engine against the record's exact path/hash/version instead of assuming every platform uses Windows `.exe`/LOCALAPPDATA. Existing strict schema-2 and source/ledger gates remain. |
| `backend/tests/live/v5_production_research.py` | Real ordinary-bootstrap HTTP/SSE probe: admitted structured/text research, verified sources, replay/cursor/refresh, scope and Stop; separate expected-unavailable negative mode. No injected registry, promotion or asset download. Positive admission remains blocked here. |
| `backend/tests/test_v5_storage.py` | Missing/duplicate/concurrent completion, failed serialization, actual hard-exit recovery, bounded diagnostics, linked output and retained failure cases. |
| `backend/tests/test_v5_browser_installation.py` | Windows/Linux/default/explicit/hermetic cache, malformed/missing/linked installation, and stale record/path/hash/fixture/version refusal. Boundary mocks do not qualify hardware or an engine. |

The journal invariant gap is proven independently by regression tests. It is **not an established cause** of the earlier V4 intermittent SQLite I/O, journal-recovery or missing-ledger observations.

## Measured validation

The final measured summary is [v5-execution-evidence.json](release/v5-execution-evidence.json). Full-source and runtime identities are distinct; each attempt keeps its own exact boundary and report hash. Raw XML, logs, runtime DBs and screenshots remain private under `.local/` or the named temporary diagnostic root.

- Before edits: **86/86** focused budget/graph/Notepad tests passed.
- Before edits: **12/12** real crash/resume scenarios passed across overlay and tmpfs (three iterations of each effect/journal crash on each filesystem). Historical V4 failures were not reproduced or explained.
- After journal changes: **96/96** storage/budget/graph/Notepad tests passed.
- Browser-focused regression: **72/72** passed.
- Explicit storage-check: **5/5 overlay and 5/5 tmpfs** committed hard-exit/reopen checks passed.
- Frontend: **23/23**, lint, API generation and TypeScript/Vite build passed on pinned Node 24.22.0.
- Ordinary production refusal: four real authenticated HTTP checks passed with no matching qualification, and no work was created. The positive-admission attempt wrote **blocked**, not a pass.
- Exact pinned Chromium installer was attempted and failed repeatedly with invalid/truncated archives. Alternate Chromium 153 is not promoted as the pinned engine.
- Readiness/model samples/full benchmark attempted; local reasoning service unavailable, zero inference and no measured accuracy.

Final results on unchanged source:

| Check | Outcome |
| --- | --- |
| Full backend | **911/911 passed**, 0 failures/errors/skips, 97.81 seconds |
| Real HTTP/SSE baseline | **23/23 passed**, actual normal resource policy |
| Real dashboard/API smoke | Passed exact note/readback, duplicate identity, session/reload/logout, private storage and mobile checks; no page errors |
| Real browser adversarial fixtures | **10/10 passed** with explicitly identified alternate Chromium 153.0.8010.0; no engine qualification or promotion |
| Reliability smoke | **60.420 seconds**, 4 verified tasks, 4 memory cycles, 1 restore, 120 health requests, no failures; p95 0.004863 seconds; full two-hour gate remains false |
| Source identity | 307 files, before/after `c2c51729369b8c5fc47cbba8c8476a1258d3b2e169566d89763fb784ac59563c` |
| Runtime identity | `6f02bb172093b68363f1f281ffbcfb03a91b160d5666f43e6be43043d8441c5d` |

Dependency locks and generated contract bytes were preserved. Results from older source remain historical. The admitted branch of the new production research probe could not be executed without matching qualification; its negative pass does not satisfy that positive gate.

## Not completed — portable or non-Windows prerequisites

| Stage | Incomplete / exact next action | Location |
| --- | --- | --- |
| V5.1 / inherited V4 | Earlier intermittent persistence failures remain undiagnosed. Preserve failed roots; compare errors, file lifecycle, crash journal/ledger ordering and supported target behavior if reproduced. A later passing run does not erase them. | `storage/checkpoints.py`, `storage/action_ledger.py`, `agent/graph.py`; `test_agent_budgets_progress.py`, `test_agent_graph.py`, `test_notepad_workflow.py` |
| V5.2 | Install the exact locked Chromium and run one smoke plus complete strict 20-run fixture campaign. The generic 20-run browser report is not promotable fixture evidence. | `workflows/fixture_qualification.py`; `victus qualify-fixture` |
| V5.2 | Promote complete matching evidence locally, restart and execute the positive ordinary-production HTTP/SSE probe. Current positive probe is blocked before work. Dashboard-positive flow also remains open. | `workflows/qualification_records.py`, `bootstrap.py`, `tests/live/v5_production_research.py` |
| V5.4 | Supply deliberately selected local reasoning runtime/model/digest, run structured samples and all frozen 30 goals against 27/30; retain missing tool prerequisites. No model was downloaded or cloud substituted. | `runtime/readiness.py`, `models/`, `agent/benchmark.py`, existing model runners |
| V5.5 | Supply real 50 quiet/50 noisy consented English note recordings plus negatives, predeclared thresholds and real reviewed command/task bindings; measure untouched recognition separately from corrected actions. | `voice/{evaluation,action_evaluation,qualification_session}.py`, `evaluation/voice/V3.6-protocol.md` |
| V5.6 | Full >=7,200-second, >=100-task, >=2-restore reliability qualification remains unmeasured. Short smoke is not a substitute and this duration gate is not a Windows-only skip. | `tests/live/m7_soak.py` |
| V5.6 | Full release decision waits for all advertised capabilities and inherited gates; no qualification was promoted in this increment. | `docs/release/README.md`, current evidence and matrix |

## Windows-dependent checks skipped on Linux

| Stage | Actual target work still required |
| --- | --- |
| V5.1 | Confirm affected durable recovery/crash behavior on the supported Windows filesystem/process implementation. |
| V5.2 | Identity-based descendant observation, actual Windows browser cleanup and unrelated-process preservation; Linux/mocked checks do not satisfy this boundary. |
| V5.3A | Inspect installed Notepad/executable/profile, diagnose one actual Save transition and obtain full exact-byte plus native-UI verification. No speculative selector or timeout change was made without Windows observations. |
| V5.3B | >=20 real native successes, native adverse/review/Stop/restart cases, two physical scales/DPI, real HTTP/dashboard approval, assembly/promotion/restart and new ordinary native request. |
| V5.5 | Witness actual microphone reconnect, decoding/review/playback Stop, audible SAPI mute/interruption, physical shortcut and speaker echo/cooldown. |
| V5.6 | Fresh frozen folder build, frozen-bound per-capability qualification, actual self-test, fresh standard account without developer PATH, DPAPI/account behavior and real prior/candidate migration/new-root rollback. |

Existing native session/promotion, speech protocol and frozen identity/publication tooling are retained. Missing machine/human evidence cannot be implemented as claimed pass flags. Public web, more applications, custom wake, extra languages, arbitrary MCP/cloud, installer/autostart and public distribution remain separate optional scope.

## Reproduction and follow-up commands

Use fresh output names on every repeat. All paths below are examples relative to the repository, except the explicitly absolute qualification directory. Do not point diagnostics at personal runtime data. Linux uses `backend/.venv/bin/`; Windows uses `backend/.venv/Scripts/`.

```bash
backend/.venv/bin/victus storage-check --output .local/v51-storage-new --repetitions 5
backend/.venv/bin/python -m pytest backend/tests/test_v5_storage.py backend/tests/test_agent_budgets_progress.py backend/tests/test_agent_graph.py backend/tests/test_notepad_workflow.py --basetemp=.local/v51-focused-new --junitxml=.local/v51-focused-new.xml
backend/.venv/bin/python -m pytest backend/tests --basetemp=.local/v5-full-new --junitxml=.local/v5-full-new.xml
backend/.venv/bin/python backend/tests/live/v3_baseline.py --data-dir .local/v5-baseline-new
npm --prefix dashboard test
npm --prefix dashboard run lint
npm --prefix dashboard run build
```

Positive production probe after complete matching qualification/promotion and restart:

```powershell
backend/.venv/Scripts/python.exe backend/tests/live/v5_production_research.py --output .local/v52-production-new --qualification-dir C:/private-victus-qualification
```

Use `--expect-unavailable` with a deliberately empty qualification directory to verify the negative boundary; it never counts as admitted research. The browser cache must contain the actual exact engine, and normal resource policy remains active.

```powershell
backend/.venv/Scripts/victus.exe qualify-fixture --repetitions 1 --output .local/v52-fixture-one-new
backend/.venv/Scripts/victus.exe qualify-fixture --repetitions 20 --output .local/v52-fixture-20-new
backend/.venv/Scripts/victus.exe promote-fixture --source .local/v52-fixture-20-new/report.json
backend/.venv/Scripts/python.exe backend/tests/live/m7_soak.py --seconds 7200 --require-ready --fail-fast --output .local/v56-soak-new
```

For native session, real speech protocol, frozen build and fresh-account commands, follow the V5 guide and [Windows release procedure](release/README.md). Complete one verified native Save before repetitions. Never edit source/frozen digests, auto-approve or relax resource guards to bypass these gates.

## Completion statement

The portable implementation increment is reviewable; **full V5 and release qualification remain incomplete** while the listed machine, prerequisite, duration and unresolved reliability gates are open. The historical V4 handoff remains intact. Exact final counts and evidence belong to this increment's sanitized summary.
