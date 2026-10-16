# M8 optional integrations

All optional features default off. Local typed tasks and push to talk do not
depend on MCP, a cloud credential, a wake model or a network connection.

## Wake

See [the experiment guide](../../experiments/wake-word-training/README.md) for the
Windows compatibility result, training/provenance templates and held-out
evaluator. Runtime requires matching SHA-256 checksums for all three ONNX assets,
the tested package versions and a reviewed pilot record bound to the exact
threshold/cooldown configuration. The compatibility spike used a tiny synthetic
Identity model, not a recognition model. No custom asset, labelled positives,
negative audio or microphone accuracy qualification has been supplied.

## Selected MCP capability

Install the `mcp` extra and set `VICTUS_MCP_NOTES=1` before launching. This selects
the bundled `victus-assistant==0.1.0` stdio server for `fs.create_note`. Its launch
command is the current Python executable with `-I -m
victus.adapters.mcp.reference_server --workspace <resolved workspace>`. Server
source has an embedded release SHA-256 pin in `client.py`; changing server code
requires reviewing the new source and updating that pin. No arbitrary package,
remote server, shell command or discovered capability is admitted.

The server is trusted application code, not an OS sandbox for hostile third-party
executables. Discovery admits exactly the reviewed note schema. The registry
keeps the native scope/risk/retry contract; policy is checked on both sides and
the client independently reads the derived local path. Remote output cannot
select paths, permissions or verifiers. No retries follow possible writes.

The MCP protocol is pinned to 2025-11-25. A four-second total deadline includes
startup/discovery/call, with 32 KiB input, 64 KiB output lines, bounded queues and
discarded stderr. The outer worker uses a six-second deadline. Windows Job
Objects kill the child on outer-worker termination; failure to establish that
ownership aborts the adapter. Scope expansion, schema drift, unsolicited messages
and malformed results fail closed. A write interrupted before verification is
handled by the existing runtime as unverified/unknown, never blindly repeated.

## Explicit cloud transfer

Install the existing backend dependencies and configure both
`VICTUS_CLOUD_MODEL` (an explicit OpenRouter model ID) and
`VICTUS_CLOUD_UPSTREAM` (one upstream provider). Use `victus cloud-key` in an
interactive terminal to store the hidden key in Windows Credential Manager.
No key belongs in environment examples, frontend storage, prompts or audit.

The dashboard's separate cloud panel previews the complete serialized request,
recipient/model, SHA-256 and two-minute expiry. Deny sends nothing and performs
no credential lookup. Approve grants one exact body/recipient pair; changes,
expiry, duplicate clicks, refresh, process restart and Stop never renew consent.
Cloud responses render as text and cannot execute tools. This does not switch
ordinary local tasks to cloud or authorize a failure-driven transfer.

The provider uses only `https://openrouter.ai/api/v1/chat/completions`, disables
environment proxies/redirects and upstream fallback, and selects one upstream
with data collection denied and required parameter support. A remote model pin
records configuration identity, **not a verified remote weights digest**. The
provider still sees transferred content; choosing its policies is the operator's
review responsibility. The adapter makes no claim of offline operation.

Every approved request runs through ModelGateway, the inference slot and a
one-request/token/deadline budget. Retries/repairs require a new preview and
consent. Quota, credential, timeout and invalid-output states remain visible;
there is no quota-driven provider fallback. Remote bodies/errors and secrets do
not enter diagnostics. No live cloud request or credential access is part of tests.

## Verification boundaries

`backend/tests/test_optional_integrations.py` covers native/MCP note contracts,
real local subprocess cleanup, malformed output, broader schema/tool rejection,
server drift, cancellation/deadlines, exact/expired/denied/replayed consent,
bounded cloud output, quota/timeout/redirect handling, wake handoff/review and
speech suppression. The default API is checked with all optional features off.
Browser contracts cover keyboard review/Stop, duplicate clicks, reload, literal
preview rendering and laptop/mobile widths. Audio and network fixtures do not
establish real wake accuracy, cloud availability or upstream policy compliance.
The previous M7 soak is historical evidence for its tested revision; it does not
qualify these new M8 changes as a two-hour production run.

Primary references: [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports),
[MCP tool contract](https://modelcontextprotocol.io/specification/2025-11-25/server/tools),
[OpenRouter provider routing](https://openrouter.ai/docs/guides/routing/provider-selection).
