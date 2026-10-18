# Decision: V2.1 uses the existing step dispatcher for every action

Recorded 2026-10-18. Source version: 0.1.0 with V2.1 changes; this is not a new
qualification claim for the previously built M9 binary.

`ToolRequest` contains only a tool name and argument data. `ActionProposal`
additionally carries opaque planner target/observation references. Neither can
carry task/action IDs, approval state, scopes, permits or a verifier. The narrow
`ActionRequest` remains the note/voice contract. The registry validates generic
requests using each tool's closed strict argument model. Python submissions are
revalidated and snapshotted just like HTTP input.

`Dispatcher.dispatch_step` remains the single effect sequence. Its synchronous
`dispatch` method is a compatibility adapter that creates a trusted worker
context, runs that sequence and translates the bounded result. It no longer
contains its own adapter/verifier path. Deterministic browser/Notepad workflows
and graph planner actions continue to call dispatch_step. No Notepad dispatcher
is introduced.

TaskService/TaskQueue create UUID identities. The queue may prepare a bound action
record before spawning its owner, but **prepared is not dispatch intent**. Only
the shared dispatcher marks dispatching, after strict validation, scope/risk
policy, current target checks, cancellation and any exact permit consumption.
An owned action ID is distinct from a reviewed prepared action ID: it cannot
replace the permit/binding checks for reviewed graph actions.

The parent scheduler owns the cross-process mutation slot for a supervised
worker's full lifetime, so killing a child does not release that slot early.
`WorkerAuthority` and the internal resource-owned parameter are trusted process
metadata, never transport inputs or approval. Standalone supervisor callers use
the same bounded slot acquisition. Worker-local steps acquire the child process's
mutation slot; owner-loop containers hand off to those steps without recursively
locking the parent slot. Separate dispatchers in one owner also serialize against
the shared resource slot. Policy/target validation runs again after waiting and
immediately before intent. Stop remains independent of the slot.

Risk ceilings and scopes are explicitly constructed by trusted service code.
Bootstrap grants only low-risk workspace-file scope. Reviewed local workflow
harnesses can construct a narrower owner context for their declared risk and
domain permits; transport/model fields cannot raise that ceiling. Existing graph
actions above the context ceiling require exact bound permit authority. Generic
browser/desktop stubs are no longer advertised by bootstrap. Qualified workflow
factories still bind only their reviewed operations and native owners.

Verification must return exactly True. Path artifacts must remain inside the
workspace, note output names must match the request, and post-verification bytes
must match the reported hash. Failed proof after possible execution stays
unknown and never retries automatically. The parent accepts success only with a
verified ledger record. Public task events remain queue-owned, preserving replay
behavior; workflow-local steps retain their safe step audit events.

Context construction ensures schema availability but does not run application
restart recovery. Recovery belongs to startup; running it in a child would
incorrectly retire the live task that owns the child. Plain note dispatch also
does not import the graph/planning stack. Graph interruption is recognized from
the already loaded graph exception class and propagated without swallowing it.

Native/COM handlers stay on the owner thread, async browser handlers stay on the
owner loop and the outer supervisor still terminates native hangs. These
boundaries do not qualify native Notepad, model reasoning or public websites.
