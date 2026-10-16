# M3 section 7A: model gateway and strict decisions

The provider boundary, gateway and output parser are implemented. Live model-path
qualification is **pending**, because this environment has no Ollama executable or
listening service at `127.0.0.1:11434`. The recorded attempt reports
`MODEL_UNAVAILABLE`, zero inference requests, zero samples and `qualified: false`.
No exact digest is invented and no model is downloaded automatically.

## Contracts and ownership

- `models/contracts.py`: strict provider request, response, usage, model pin and safe
  error types. A pin requires both the model name and full `sha256:` digest.
- `models/gateway.py`: per-call timeout, task deadline, cancellation, shared request
  and reserved-output-token budgets, and one schema repair for the entire task.
  Share the same `RequestBudget` instance across every gateway/graph branch for a
  task. Reservations are atomic and never refunded for failed or cancelled calls.
- `models/ollama.py`: local-only Ollama HTTP transport and wire models. Uses
  `message.content`, `prompt_eval_count` and `eval_count`; sends `stream: false`,
  temperature 0, bounded context/output, `think: false` and the schema in `format`.
  It rejects partial/truncated output, native tool calls, missing usage, redirects,
  oversized bodies and model/pin mismatches. Environment proxies are disabled.
- `agent/output_parser.py`: consumes the entire JSON answer, rejects duplicate keys,
  non-finite values, extra fields, unknown tools, coercion, invalid arguments and
  unpaired target/observation references. Schemas narrow tools to an explicit catalog.
  Empty catalogs permit only a finish decision. No substring, regex, code-fence,
  Python or shell extraction is used. Code-like text inside a legitimate note argument
  stays literal data; the parser does not execute anything.

The candidate path is **JSON schema output**. Native tool calls and unstructured
fallback are deliberately unsupported. The broken, unused streaming Ollama scaffold
has been replaced; there were no working repository callers to migrate. The wire
shape follows [Ollama chat](https://docs.ollama.com/api/chat) and
[structured output documentation](https://docs.ollama.com/capabilities/structured-outputs).
Those API capabilities do not establish that a particular model passes our samples.

`config/models/qwen3-4b.candidate.json` identifies the prior scaffold's candidate model,
not a qualified deployment pin. It has no digest and is not loaded by the public API.
The gateway requires an explicit `ModelPin`; the public task service does not yet
invoke it. A LangGraph execution loop is outside section 7A.

## Decision shapes

```json
{"decision":"action","action":{"tool":"fs.create_note","arguments":{"filename":"note.txt","text":"ready"}}}
```

```json
{"decision":"finish","status":"blocked","reason":"No approved target exists"}
```

An action decision contains a strict `ActionProposal` subtype. The dispatcher still
owns policy, scope, approvals, cancellation, audit and verification. Model-provided
references are claims and must pass the adapter's freshness/identity checks. A finish
status of `completed` is also a claim; downstream task completion must independently
check promised results. This parser grants no device-control authority.

Only an output schema-validation failure may cause a repair. A generic correction
message reuses the original schema and task messages without echoing malformed model
text. The repair uses a normal request reservation plus the single task-wide repair
slot. A second invalid answer stops. Transport, timeout, pin and cancellation errors
never trigger an automatic retry, alternate provider or alternate output mode.

Cancellation tears down the awaiting HTTP operation and discards late output. It does
not prove that an already submitted Ollama generation stopped on the server. Keep
Ollama local and trusted. Pre/post tag digest checks detect observed tag changes; the
Ollama chat response itself does not cryptographically attest model weights. Do not
mutate installed model tags during a qualified run.

## Live qualification on the target machine

Start the locally installed Ollama service and install the deliberately chosen model
separately. From `backend`, use a fresh output path:

```bash
uv run python tests/live/m3_model_samples.py --model qwen3:4b --output /absolute/new/model-samples.json
```

The runner pins the uniquely matching installed tag's digest for all six artificial
samples. To require an already reviewed digest, add `--digest sha256:<64 hex digits>`.
It tests simple/escaped action arguments, completed/blocked finish decisions and
unsupported shell/browser operations. It invokes **no tools**, and uses one shared
12-request/6144-output-token/300-second budget with at most one repair overall.
Check `qualified`, every expected decision, requests, usage and the exact reported pin.
A failed run must not be treated as native-tool-call qualification. Re-run after a model,
provider, schema, tool-catalog or option change. These six samples qualify only their
narrow structured path, not arbitrary planning or task-completion accuracy.

## Verification

- 65 fake-response/parser/gateway tests pass, covering strict decisions, exact Ollama
  payloads, usage, model/tag drift, HTTP and malformed responses, output bounds,
  truncation, unsupported native calls, concurrent shared budgets, one global repair,
  deadlines, event cancellation, task cancellation and safe error messages.
- Full Python regression suite: 307 passed, one existing Starlette deprecation warning.
- Ruff passes for all changed Python files.
- [Live attempt evidence](evidence/M3-7A-live-model.json): blocked, zero live samples.
  The requirement to choose a path proven by an exact pinned model remains outstanding.
