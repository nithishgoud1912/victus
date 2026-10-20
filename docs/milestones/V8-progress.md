# V8 — Local reasoning and reviewed voice implementation

Base: pushed V7 implementation (`7d1c0b72364b3f5ea673f33922f163350bda0c41`).
Branch: `codex/v8-implementation`.
Guide: [V8 plan](../../outputs/VICTUS-v8-Next-Stage-Implementation-Plan.md).

## Design before implementation

Preserve the admitted note path, shared dispatcher, exact review, persistent
budgets, Stop and unavailable native/browser gates. V6 remains unreconciled.
Existing V7 target requirements are retained, not waived by a new guide number.

1. Replace ad-hoc model-tag readiness with bounded strict provider parsing and
   exactly one matching installed name/digest. Malformed/ambiguous/changed tags
   return unavailable without exposing provider data or breaking capability reads.
2. Add a separate frozen supported-command phrasing contract and read-only
   evaluator. This measures intake/clarification, executes no effects or inference,
   and never substitutes for the unchanged 30-goal model benchmark or 27/30 gate.
3. Retain a server-derived human-correction indicator in the existing protected
   voice-origin command payload; expose only aggregate correction counts in
   offline action evaluation. Client input cannot assert origin or corrections.
4. Bind new voice qualification sessions and recognition reports to exact local
   STT asset bytes. Missing assets remain a prerequisite block. Recognition,
   reviewed actions, corrections and physical observations stay separate.
5. Validate counts and numeric domains strictly in aggregation. Out-of-range,
   malformed, partial or mismatched evidence cannot qualify; retain an incomplete
   aggregate rather than crash when subordinate reports are invalid.

Run meaningful portable regression and real loopback/UI checks. Real local
inference requires an installed selected pin. Real acoustic trials require
consented recordings. Windows-only UIA/process/SAPI/microphone/hotkey checks and
human-witnessed audio tests will be listed explicitly in the V8 handoff.
No cloud fallback, asset download, automatic listening or qualification promotion
is introduced. Public evidence contains aggregate results only; private diagnostic
paths, recordings, transcripts and environment inventories stay private.

## Implemented and verified

The five planned portable changes are implemented, with two measured intake
phrase fixes. Full regression: 967 backend tests; final-source focused follow-up:
62 tests; frontend: 23 tests plus lint/API generation/build. Ruff passed after
removing one inherited extra import blank line. HTTP/SSE: 23 checks. Dashboard
fixtures: command 9, voice 10, readiness 10; real dashboard/API smoke passed on
alternate Chromium. No locked-engine qualification is inferred.

The first supplementary intake run passed 18/20, retaining both failures. The
same expectations pass 20/20 after plural-file/browsing-intent detection fixes.
The original frozen benchmark bytes and 30-goal denominator remain unchanged.

Live model samples and benchmark were attempted: MODEL_UNAVAILABLE, zero model
requests/inference and zero scored goals. Real recordings and physical witnesses
were unavailable. Full V8 is incomplete until those gates pass; no qualification
records were promoted and no new capability was enabled.

See [test handoff and Windows register](../V8-TESTS-AND-INCOMPLETE.md) and
[aggregate evidence](../release/v8-execution-evidence.json). Raw diagnostics stay
outside tracked source. V9 inherits all unresolved V7/V8 obligations.
