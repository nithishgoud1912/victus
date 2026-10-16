# Supported workflows - VICTUS 0.1.0 candidate

This matrix describes evidence, not blanket product support. Earlier M7 soak
evidence belongs to its tested revision. Package results will be updated after
the M9 self-test; no fresh-account result is currently available.

| Workflow | Implemented | Deterministic evidence | This laptop | Public sites | Release limit |
|---|---|---|---|---|---|
| Typed workspace note, queue, replay and Stop | Yes | Backend and browser contracts pass | Source/previous live checks; frozen check pending | Not required | Workspace notes only |
| Approval preview, expiry, deny, approve once | Yes | Policy/replay/keyboard fixtures pass | Source UI checks | No new M9 qualification | Exact current approval only |
| Durable memory, forgetting, retention | Yes | SQLite/payload/checkpoint tests pass | Previous M7 checks | Not required | Explicit reviewed memory only |
| Consistent backup and restore | Yes | WAL/checksum/approval invalidation tests pass | Previous M7; packaged check pending | Not required | Offline or quiescent; compatible schema |
| Dashboard from frozen resources | M9 | Path/spec checks | Folder build pending | Not required | Keep entire bundle |
| Offline migration and rollback | M9 | v6 fixture -> v7, future schema rejection | Packaged same-version rehearsal pending | Not required | Real cross-version pair still pending |
| Native browser/UIA control | Yes | Adapter/workflow fixtures | Earlier narrow evidence only | No new M9 qualification | Separate engine/app/target qualification |
| Local Ollama reasoning / GPU | Yes | Gateway/parser/budget fixtures | No M9 inference qualification | Not required | Explicit local model and telemetry |
| Push to talk / spoken summaries | Yes | Capture/STT/review/SAPI fixtures | No M9 physical microphone or audible-speech qualification | Not required | Downloaded STT asset; reviewed submit |
| Custom wake word | Gated | Lifecycle/threshold/consent fixtures | Windows library/ONNX spike only | Not required | Model +100 positives +7200s negatives missing |
| Optional narrow MCP note | Yes, off by default | Local server and supervised source task pass | Frozen MCP check pending | Not required | Bundled pinned note server only |
| Optional cloud | Yes, off by default | Consent/timeout/quota fixtures | No live provider request | Not verified | Explicit exact-body consent; no automatic fallback |
| Fresh standard-account deployment | Procedure provided | Not replaceable by fixtures | Pending external account/machine | Not required | Mandatory release gate |

Implemented:
Local core, opt-in integrations, folder-build/release procedure and self-test.
Verified with deterministic tests:
See milestone evidence for exact counts and report locations.
Verified on this laptop:
Source/build results only until M9 packaged evidence is collected.
Verified on public sites:
No new public-site qualification in M9.
Still pending:
Fresh standard account/dedicated machine; real cross-version release pair;
target-specific GPU, browser, microphone, speech and custom-wake qualification.
