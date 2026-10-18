# Decision 006: Gated checklist admission

Date: 2026-10-18. Scope: V2.5 source candidate.

Expose a narrow authenticated `POST /api/workflows/notepad-checklist` transport
with only profile ID, bounded checklist items and a new workspace basename.
Native executable paths, selectors, roots, encoding, keyboard permissions,
approval flags, action IDs and permit tokens are not transport fields.

TaskService admits this request only for server-selected qualified profile IDs
and a registered workflow tool. Bootstrap currently selects none and registers
no native workflow, so the endpoint returns 503 before admission. There is no
environment flag or request flag to bypass qualification. Native target-bound
review integration and successful live workflow qualification remain prerequisites
for future native registration. Existing approval routes/stores/permits remain
unchanged; no blanket HTTP permission is inferred from reviewed local CLI runs.

The generic task route passes this tool through the same profile gate. Both
entry points reuse the existing queue, worker supervisor, dispatcher, task
snapshot, events and Stop. The queue checks a duplicate request ID before its
trusted pre-admission filesystem check, under one admission lock. This preserves
the original task on replay after its output file has been created.

API tests inject only a simulated UIA workflow with a fixture-only scope/risk
configuration. That fixture's reviewed context is not shipped in bootstrap and
does not qualify a native adapter or its HTTP approval wiring.

Save verifies the exact approved destination again, checks cancellation between
filename preparation and native Save, and independently proves expected editor
content, an actionable main window and exact saved bytes. Matching bytes while
an overwrite/modal dialog is still pending cannot become success. A stop after
typing preserves the possible partial effect as unknown. GUI Save As remains
non-atomic: use a private workspace, reject observed competing writers, and never
approve an overwrite dialog or promise exclusive filesystem creation.
