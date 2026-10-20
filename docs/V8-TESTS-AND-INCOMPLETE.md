# V8 implementation and test handoff

Base: V7 `7d1c0b72364b3f5ea673f33922f163350bda0c41`.
Implementation branch: `codex/v8-implementation`.

The portable V8 increment is implemented. **Full V8 qualification remains open**:
no local reasoning inference, real acoustic corpus or witnessed Windows session
was available. No capability or qualification record was promoted. V6 remains
`V6_NOT_RECONCILED`; V7 native/browser prerequisites still apply.

## Implemented behavior

- Model readiness uses bounded strict local-provider parsing and requires exactly
  one matching installed name/digest. Duplicate, malformed, oversized, changed or
  unavailable tags return unavailable. Inventory performs no inference/download.
- A separate 20-case command intake contract covers exact literals, hostile text,
  missing values, ambiguous intent, unsupported requests and invalid submissions.
  Initial execution passed 18/20. The two failures exposed plural-file and
  browsing-phrase detection gaps; fixing those patterns passed 20/20 with unchanged
  case expectations. This is a deterministic development contract, not independent
  held-out inference evidence. The original 30-goal benchmark is unchanged.
- Reviewed voice commands retain a server-derived correction indicator inside
  their protected payload. Read-only action evaluation reports correction counts
  and rates separately from recognition and verified-action scores. Older commands
  without provenance remain unmeasured; typed input cannot assert it.
- Voice protocol schema 2 and recognition reports bind exact local STT asset
  bytes. Recognition requires a fresh worker and checks asset drift after trials.
  Protocol preparation without assets remains pending. Old reports must be rerun
  with the new provenance; they cannot silently qualify.
- Aggregation rejects invalid numeric domains, boolean/float sample counts,
  malformed group maps, missing correction measurements and asset mismatches.
  Synthetic tests of evidence validation establish no microphone/acoustic result.

## Portable validation

See [aggregate evidence](release/v8-execution-evidence.json) for final totals,
source identity and report hashes. Backend tests, frontend tests/lint/build/API
regeneration, loopback HTTP/SSE and command/voice/readiness dashboard contracts
were run. Dashboard contracts use alternate Chromium 153 and mocked API fixtures;
they do not qualify the locked Chromium 156 engine or actual audio devices.

Reproduce from the repository root using the locked environment:

```bash
backend/.venv/bin/python -m pytest backend/tests
backend/.venv/bin/ruff check backend
npm --prefix dashboard test
npm --prefix dashboard run lint
npm --prefix dashboard run build
backend/.venv/bin/python -m victus.agent.intake_evaluation --suite evaluation/v8-command-intake-v1.json --output intake-report.json
```

Use pinned Node 24.22.x, fresh output names, and isolated test data. The repository
also provides `backend/tests/live/v3_baseline.py` (`--data-dir`),
`v35_command_dashboard_contract.py`, `v36_voice_dashboard_contract.py` and
`v7_dashboard_contract.py` (each `--output`). Preserve diagnostics outside Git.

## Tests requiring the Windows target

All rows below are **NOT RUN** in this Linux environment. Use the supported
Windows laptop, actual devices and final source. Keep normal resource guards,
current model/STT identities and isolated runtime data. A successful API call or
mocked adapter result is insufficient.

| Test | Procedure and pass evidence |
| --- | --- |
| Physical emergency shortcut | Press Ctrl+Alt+Pause during decoding, review and playback; shared Stop latches, owned work exits, no late transcript/submission/effect appears. Confirm dashboard keyboard Stop separately. |
| SAPI/COM playback | Hear a verified generic result after display acknowledgement. Exercise mute, interrupt and Stop during speech; sound actually ceases, owned COM worker exits, no private payload is spoken. |
| Microphone ownership and reconnect | Start real push-to-talk, reject competing capture, unplug while active, reconnect and explicitly start fresh capture. Old buffers clear, no stale transcript is admitted, ownership is safely released or retained on failed cleanup. |
| Speaker echo and cooldown | Play real assistant speech through speakers. Witness capture suppression and cooldown acoustically; no assistant-speech command/proposal is admitted. Record safe observations without publishing audio. |
| Live STT cancellation | Stop during real local decoding and capture. Reap the owned worker/device, preserve shared model ownership, permit a fresh session only after safe cleanup. |
| Integrated contention | Exercise CPU STT, the exact reasoning pin and admitted notes on target hardware. Measure cold/warm latency, RAM/VRAM peaks, resource-pressure blocks and Stop cleanup; typed notes remain usable when model/device unavailable. |
| Inherited native workflow | Actual Notepad first Save, at least 20 repetitions, exact approval, stale target/session/adverse cases, two physical DPI scales, owned process cleanup and ordinary production admission. See V7 handoff; voice confirmation never approves Save. |
| Inherited Windows recovery | Confirm durable queue/checkpoint recovery, unknown-effect reconciliation and no automatic replay after interrupted effects. Historical V4 I/O/ledger failures remain undiagnosed. |

`backend/tests/live/v36_device_probe.py --output <fresh-directory> --model
<installed-stt-directory>` provides component diagnostics. It does **not** witness
unplug, audibility or echo. Physical protocol fields must be completed by a human
who actually observes all seven `PHYSICAL_CHECKS`, with start/end runtime and STT
identities. Hashes bind files; they do not authenticate a witness.

Frozen executable, fresh Windows account, upgrade/rollback and the final-source
two-hour reliability campaign remain V9 obligations; this increment does not
claim package qualification.

## Missing prerequisites that are not Windows-only

| Gate | Current result and required next run |
| --- | --- |
| Six strict local-model samples | Attempted: `MODEL_UNAVAILABLE`, zero inference samples/requests, no selected pin. Install/select an explicitly approved local name/digest, then run `backend/tests/live/m3_model_samples.py` with its actual `--model`, `--digest` and fresh `--output`. |
| Original frozen benchmark | Attempted: 30 requested, zero executed, 30 unavailable/unscored, no accuracy claimed. Run `backend/tests/live/m3_30_goal_benchmark.py` after model readiness; keep all 30 goals and the 27/30 gate. Native cases currently remain unqualified in the harness; Windows availability alone does not implement/admit their tools. |
| Real voice corpus | Zero quiet/noisy recordings evaluated. Collect consented, independently labelled 50 quiet + 50 noisy English note recordings plus silence/background/assistant-speech negatives. Keep audio/reference text private, freeze labels and thresholds before inference, and use distinct destinations/voice command IDs. |
| Recognition/action qualification | Prepare schema-2 protocol with explicit `--model`; run recognition on untouched output, action verification on actual reviewed voice-origin tasks, then aggregate with witnessed physical evidence. Missing/older provenance is unmeasured, not a pass. |
| Resource envelope | No inference/acoustic latency or peak resource measurements exist. Predeclare limits before the real campaign; cold/warm and concurrent workloads require actual measurements. |
| Exact browser engine | Locked engine installation remains blocked by invalid archives. Alternate-engine UI passes do not waive this prerequisite. |

Original benchmark SHA-256:
`1a23540e729f3b62f9e0991fd7c53d6cd6e279a514f45f1e4a697949a273e340`.
No thresholds, benchmark denominators, dependency locks or public API schemas
were relaxed. Optional wake/MCP/cloud/additional languages remain outside V8.
