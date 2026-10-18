# V3.0 / V3.1 — Baseline and native Notepad qualification

Started: 2026-10-18, Asia/Calcutta. This record precedes V3 production edits.

## Scope and preserved starting point

Implement only V3.0 and V3.1. Preserve the uncommitted V2.1–V2.5 work, existing
runtime data, dependency locks, original note path and disabled native HTTP gate.
Git base is `64a0a22127a2d450a8d8bb4047cf76cae0cc4995`; the dirty inventory and
file-by-file source/config/contracts/lock manifest will be captured under a fresh
`.local/v30-*` root before production changes. A final manifest will bind new
qualification results to their exact tested bytes.

Reviewed V2.4/V2.5 milestone documents and `docs/release/v2.4-notepad-evidence.json`
and `v2.5-workflow-evidence.json`. Their 688/727 backend counts and 20 frontend
tests are historical. This milestone claims no new test result yet.

## Runtime roots and capability states

- All new `.local/v30-*` and `.local/v31-*` roots are isolated qualification data.
  Earlier `.local/v24-*`, `.local/v25-*`, package-check roots and `backend/.local-tests`
  are prior test evidence and will be preserved.
- Production resolves `VICTUS_DATA_DIR`, otherwise `%LOCALAPPDATA%/VICTUS`.
  The environment-resolved path will be recorded privately without reading its
  documents or choosing it for a run. No real user runtime is selected for testing.
- Workspace note: implemented and enabled in default bootstrap, conditional on
  authentication, Stop and normal resource pressure guards.
- Queue, durable replay, authenticated task snapshots and Stop: implemented;
  current regression verification pending.
- Installed native Notepad candidate: implemented, awaiting native qualification,
  unavailable through production HTTP; review integration remains a separate gate.
- Browser/model/voice modules: implemented; broader task admission and target/device
  qualification are separate from the default note capability.
- Wake/cloud/MCP: optional, disabled in default configuration. Enabling optional
  notes does not qualify arbitrary MCP tools. Resource pressure is a temporary
  admission block, not evidence that a capability is absent.
- Existing M9 bundle: historical source only; no V3 package claim.

## V3.1 implementation and verification plan

Inspect the existing UIA application/process lease, selectors, actions, native
bindings and checklist workflow. Add bounded phase diagnostics with operation
names, opaque identities, timings and safe error codes; exclude text, credentials,
raw control trees and exception messages. Reproduce one supervised native run
under a fresh root, compare with isolated Save evidence and change only a measured
gap. Preserve exact ownership, empty-editor proof, target revalidation, filename,
encoding, byte and actionable-editor postconditions. Unknown Save is never retried.

Run focused UIA/workflow/dispatcher/approval contracts and the original note/API/
events/Stop baseline with normal memory guards. One successful supervised native
run must precede 20 repetitions and physical display/adversarial qualification.
If the first run fails, keep native disabled and document the exact boundary.
No global Notepad settings, title-only targeting or closing unrelated apps.

Results and final source identity will be appended after execution.

## Captured baseline and exact V3 changes

Initial inventory: `.local/v30-start-01/source.json`, 252 files, source hash
`780ad7bd82ab730da611df6ed99f8014922ca1edca5ec3ec6e1b44ec6a8b7d7e`.
The sibling `dirty-status.txt` records all pre-existing edits/untracked files.
`runtime-roots.json` records the environment default
`C:\Users\HP\AppData\Local\VICTUS`, no configured override and no selected user
runtime. Merely resolving that default is not permission to inspect its contents.

Final regression-start inventory: `.local/v31-tested-source-01/source.json`,
256 files, source hash
`4f806da7a418c4885d62eb0f046b11add45994c2daba0c0f4563dc02c767395f`.
It covers production and test source, config, generated API contracts, backend
and dashboard lockfiles, frontend build configuration, scripts and packaging.
Docs, build outputs, dependencies, runtime databases, environment files and
private evidence are outside that source fingerprint. All existing implementation
edits are included, not attributed to this stage.

Only these implementation/test/script files differ from the captured start:

| File | V3 change |
|---|---|
| `backend/victus/workflows/diagnostics.py` | New private JSONL phase recorder; maximum 256 records; safe codes, elapsed time, task/process/opaque target identities; flush before entering an operation |
| `backend/victus/workflows/create_notepad_checklist.py` | Optional execute/verify diagnostics; filename/Save subphases; immediate editor readback after filename preparation; explicit Save postcondition diagnostic |
| `backend/victus/workflows/qualification.py` | Enable diagnostics for supervised Notepad only; refuse reused roots; expose safe phase summary; stop repetitions after the first unverified native run |
| `backend/tests/test_workflow_diagnostics.py` | Bounds/privacy/exception/async-failure/no-overwrite and native stop-on-failure contracts |
| `backend/tests/test_notepad_workflow.py` | Changed-editor-during-filename guard and diagnosed exact-output workflow checks |
| `backend/tests/live/v3_baseline.py` | Explicit real loopback HTTP/SSE baseline; random transient token, fresh isolated data, normal memory safeguards, sanitized result |
| `scripts/capture-source-manifest.py` | Reusable fresh inventory/manifest/runtime-root capture |

`backend/uv.lock`, `backend/pyproject.toml`, dashboard dependency files and generated
contracts match the captured starting bytes. Earlier V2 generated-client edits
relative to Git HEAD remain intact. No dependency upgrade, native registration,
schema migration or user runtime modification was introduced.

Diagnostics are observations: `returned` means a handler returned, not that its
effect is verified. Only the existing dispatcher/postcondition evidence can mark
an action verified. Private logs never export text, filenames, executable paths,
raw exception messages, COM handles or native trees. They remain under the
explicit qualification root; the exported evidence contains only summaries.

## Native evidence and stopping boundary

Installed package inspection confirms Notepad `11.2607.14.0`; current executable
SHA-256 is `03745e9e21684c0e6d9fdc50d91caa0935f4baf50f626c11987ab7d6991d58d1`,
matching the existing candidate. No profile selector, ownership or keyboard policy
was relaxed.

- `.local/v31-reproduce-01`: original source supervised run returned unknown.
  Launch was verified, then editor inspection became unknown; no text or Save
  step was dispatched. No requested artifact was produced.
- `.local/v31-diagnostic-01`: diagnosed launch failed with
  `OWNED_CHILD_UNAVAILABLE` after 5109 ms, before control inspection/input.
- `.local/v31-final-native-01`: the native runner's final diagnosed run returned
  unknown at `uia.launch_profile.execute`, with the same `OWNED_CHILD_UNAVAILABLE`
  code after 5109 ms. It recorded 2 phase records, stopped after that one failed
  run and produced no requested artifact. No text-write or Save phase was entered.

The installed app's reused background process does not provide the new owned child
required by this candidate. This establishes the current launch-ownership blocker;
it does not establish the cause of the earlier editor failure or uncertain Save.
The V2.4 isolated filename-host Save and V2.5 uncertain supervised Save remain
historical evidence. The current blocked launch cannot qualify their behavior.
Test-created windows are left for inspection; no unrelated documents/settings or
Notepad processes were closed to manufacture a successful run.

The required first successful supervised run has not passed. Therefore **20 native
successes, native two-window/nonempty/stale/missing-control/approval/Stop cases and
physical DPI qualification were not attempted as a passing qualification matrix**.
Existing deterministic cases remain separate. Native HTTP admission remains
disabled, and exact target-bound HTTP review is still a separate V3.2 prerequisite.

## Reproduction commands

Run from the repository root; use a new output/data directory on each repetition.

```powershell
backend/.venv/Scripts/python.exe scripts/capture-source-manifest.py --output-directory .local/v3-new-source-capture
backend/.venv/Scripts/python.exe backend/tests/live/v3_baseline.py --data-dir .local/v3-new-api-check
backend/.venv/Scripts/python.exe -m pytest backend/tests --basetemp=.local/v3-new-regression --junitxml=.local/v3-new-regression.xml
backend/.venv/Scripts/python.exe backend/tests/live/workflow_qualification.py notepad --data-dir .local/v3-new-native-check --repetitions 1 --profiles config/applications/notepad-win11-11.2607.14.0.json --profile notepad-win11-11.2607.14.0 --encoding utf-8
```

The native command opens a real application, intentionally blocks unsafe reuse,
and leaves opened windows intact. Inspect its JSON status and private phase log.
No automatic retry can promote an unknown Save to success.

## Final verification and status

| Check | New result | Evidence |
|---|---|---|
| Full backend regression on the frozen V3 source | **735 passed**, 0 failures/errors/skips; **328.634 s** | `.local/v31-regression-01.xml` (private hostname-bearing XML) |
| Real source loopback HTTP/SSE baseline | **14/14 passed** | `.local/v30-final-source-api-01/report.json` |
| Selected lint for every V3 production/test/script change | Passed | Final command output |
| Source inventory before versus after verification | Identical 256-file inventory and source hash | `.local/v31-tested-source-01/source.json`, `.local/v31-after-verification-01/source.json` |
| Native supervised qualification | Unknown at launch; **0/1 verified** | `.local/v31-final-native-01/notepad-qualification.json` and private phase log |
| Dependency/contract preservation | Starting lock, dependency and generated-contract bytes retained | Starting/final manifests |

The 14 real HTTP/SSE checks cover authenticated health and enabled note scope,
unauthenticated health/events rejection, gated native admission without a task,
note admission and exact bytes, duplicate identity without another effect,
authenticated/read-only task snapshot, ordered events and snapshot, cursor replay
without resubmission, Stop latch and no later write. Available RAM at the final
smoke start was 3,029,159,936 bytes; production's 2 GiB guard remained enabled.
The transient API token was not logged or saved in evidence. The isolated source
server was stopped after the check.

The final suite includes 6 diagnostic contracts and 34 simulated checklist tests,
including the two new workflow cases; 20 simulated repetitions are still simulated.
Existing UIA, exact-action approval, dispatcher, API, recovery and Stop cases passed
in the complete run. Production and profile bytes were unchanged after the final
native attempt; later additions before the frozen suite were tests and inventory
tooling. The final suite and final loopback check use the recorded final inventory.

A development selected run recorded 204 passes and one deadline-fixture failure:
the 0.5-second `live-handle` dispatcher test expired before entering its adapter
while other checks were running. No dispatcher rule was relaxed. That case passed
in the final full regression; the development result is not counted as a pass.
Earlier development checks/results do not replace the final source-bound suite.

Implemented: **V3.0 baseline complete**, V3.1 phase diagnostics, Save guard and
qualification-runner changes complete.

Verified with deterministic tests: **735 passed** and selected lint, on the exact
recorded dirty source. Fixture telemetry is controlled; this is separate from
the real-memory HTTP/SSE smoke.

Verified on this laptop: **14 real loopback HTTP/SSE checks**; installed Notepad
version/hash confirmed; native launch correctly blocked on missing owned child.
No successful native Save, native adversarial/DPI qualification or V3 package is claimed.

Verified on public sites: none; outside this scope.

Still pending: **V3.1 native qualification remains blocked** at new-child ownership.
The first successful supervised workflow, 20 successful native repetitions, native
adversarial cases and intended physical display scales remain unqualified. Native
HTTP review wiring is a separate V3.2 gate. Production native admission stays disabled.

Sanitized summary: [V3 evidence](../release/v3.1-native-evidence.json).

## Subsequent V3.2 / V3.3 work

[Native review and checklist dashboard](V3.2-3-native-review-dashboard.md) adds the
bounded worker-owned approval wait, exact-action permit binding and pre-Invoke
revalidation, persisted waiting/approval snapshots, separate qualification gates,
read-only workflow capabilities and a typed checklist form. Production native
registration remains disabled because the V3.1 native blocker is unresolved.
Current review correctness is demonstrated with simulated UIA only. The new
milestone and its sanitized evidence record current source identity and results;
the V3.0/V3.1 fingerprint and counts above remain historical.

## Subsequent V3.4 / V3.5 work

[Bounded fixture research and text commands](V3.4-5-browser-commands.md) adds strict
server-scoped research admission and protected, durable text-command clarification
through the existing queue and graph. Default note commands are available subject
to resource pressure. Native checklist, fixture research, public-web research and
local reasoning retain explicit gates. The new live fixture attempt was blocked
by memory pressure; the unchanged full 30-goal rerun could not execute because
the reasoning model was unavailable. The historical 19/30 is not a new result,
and its 27/30 qualification gate remains unmet.

## Subsequent V3.6 work

[Reviewed voice and release qualification](V3.6-reviewed-voice-release.md) routes
confirmed speech through the shared command service, adds explicit clarification,
keeps pending review details immutable on uncertain retries and speaks only
generic verified final status. Current source validation passed 791 backend and
23 frontend tests, strengthened voice browser contracts and preserved legacy note
review. A fresh folder package passed 21 self-tests and an actual schema-7-to-8
prior-artifact rehearsal passed eight checks. Neither that same-product-version
pair nor real-device component checks establish fresh-account, acoustic or formal
release qualification. The final reliability run and remaining gates are in its
own evidence record; V3.0–V3.5 counts above remain historical.
