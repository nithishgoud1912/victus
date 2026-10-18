# Decision 004: Stop and failed-cleanup ownership

Date: 2026-10-18. Scope: V2.3 source candidate.

The existing cancellation controller remains the shared task Stop latch and
launch barrier. API Stop and the optional global shortcut invoke Services.stop.
No planner decision is needed to stop work. Spawned workers still receive a
serializable request/authority, construct native objects in their owner, and use
the common dispatcher; a blocked native adapter is interrupted by its parent
process supervisor rather than relying on coroutine cancellation.

Stop now latches before any optional cleanup. Queue stop/close is attempted even
when cloud, voice, shortcut or retention cleanup fails, and independent cleanup
continues after errors. Failed shutdown/startup cleanup retains OS directory
ownership. InstanceLock.retain keeps a strong process-local reference so caller
unwinding or garbage collection cannot silently release a failed owner's lock.
Successful explicit cleanup closes the handle and removes that retained reference.
There is no UI endpoint to clear an unsafe owner.

The supervisor records its exact process before launch. If launch raises after
a PID was assigned, it signals and reaps that same owned process. Every reap
attempt requests cooperative exit before finite join/terminate/kill phases. A
reap failure latches Stop and keeps the process handle plus mutation slot. Both
standalone supervision and queue-owned supervision retain the slot until safe
cleanup; another controller cannot acquire it. Shutdown cannot release the
directory while this owned worker might still act. No PID search or unrelated
process termination is introduced. An unreapable owner requires operator/process
recovery; automatic slot reset or mutation replay is intentionally unavailable.

The task's operation budget now starts when the scheduler selects it. Mutation
slot waiting, durable preparation and supervised execution share the same finite
absolute deadline. Pending queue time is separate. Slot expiry before dispatch
fails without an action/effect. The worker/common step keeps its own tool bounds,
and the parent hard deadline still covers blocked native code.

The dispatcher checks Stop/deadline again after durable dispatch-intent I/O and
immediately before invoking an adapter. A signal arriving during that I/O cannot
cause a new adapter call. Once intent is durable, uncertain outcomes remain
unknown; already written bytes and saved files are never described as undone.

Fixtures cover refused/failed shortcut registration and a callback cleanup error,
including unregistration on the registering thread. They do not press a physical
Ctrl+Alt+Pause key or qualify native Notepad, UIA/DPI, a new executable or a soak.
