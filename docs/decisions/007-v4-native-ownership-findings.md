# V4 native ownership findings and next design boundary

Observed on 19 October 2026; installed Notepad 11.2607.14.0 and SHA-256
`03745e9e21684c0e6d9fdc50d91caa0935f4baf50f626c11987ab7d6991d58d1`
still match the candidate profile. No launch-mode or selector change is justified
by the historical error alone.

## New observations

`.local/v41-native-one-01` records a cold pre-launch inventory with no matching
process/windows, the exact launcher creation identity, a distinct owned child,
and one visible window. The existing child proof succeeded in about 1.3 seconds.
The independently read empty editor and exact entered checklist passed; measured
window DPI was 120. Save invocation returned, but native UI postconditions could
not reacquire a unique main window. No expected file was observed afterward.
The ledger/outcome stays **unknown**, never success or an automatic Save retry.

After that run exited, read-only process and destination checks found no running
Notepad and no expected artifact. A separate fresh-root run
`.local/v41-native-one-02` again established a new child/window, then refused an
initially nonempty editor before entering text. This is consistent with session
restoration but does not prove its cause or the provenance of the restored text.
Do not erase it, disable restoration globally, terminate a shared instance or
modify a user document to make qualification pass. No manual UI effects were
performed. Post-run inspection did not expose a Notepad window to the computer-use
helper, so there is no screenshot-based diagnosis of Save failure.

## Decision

Keep `owned_child`, pinned image/creation identities, unique scoped selectors,
empty-editor checks, single worker/review ownership and unavailable production
registration. Do not increase a timeout or add a broad process-name connection.
The root cause of the historical reused-process failure remains unestablished;
these cold runs demonstrate that it is not the only current boundary.

The implemented diagnostics snapshot process identities and window handles before
launch, after launch, after binding and on failure. They never inspect preexisting
document trees or contents and never turn an observed window into authority.
Counts/truncation and observation failure are explicit; exported evidence contains
only summary findings, not private native inventories.

## Requirements for an alternative editor lease

If a documented app-supported new-editor launch route is identified, first prove
it with pre/post process and window/editor runtime-ID inventories. A process
lease alone cannot prove a newly created document because session restoration can
populate a new process. A new editor lease must bind exactly one newly created,
empty editor plus its window identity, tab/document identity, process creation
identity and profile/executable hash. Existing documents must remain inaccessible.
Revalidate the full lease and exact content/path before every effect, including
after the approval wait. A shared-process lease must never terminate the process
on cleanup; loss or replacement invalidates authority and requires a fresh review.

Before production implementation, capture the failing Save boundary with the
retained diagnostics, inspect the actual dialog/editor identity transitions and
independently reconcile the unknown file effect. Preserve the saved experiment
roots. Full native/adversarial/two-scale and real HTTP/dashboard Save review gates
remain required before any trusted registration.

## Continuation design: a new tab inside the proved owned child

The actual installed UI exposes an `AddButton` and `TabListView`. A new-process
lease does not imply a new document. Extend only the pinned profile with an
explicit new-tab control and tab container. Before invoking Add, inventory tab
runtime identities without reading existing document text. Require exactly one
new tab, all old tabs preserved, the same unique main-window identity and exactly
that new tab selected. Bind this tab/window identity to the application reference
and revalidate it before every effect/read, including Save review. The existing
empty-editor test remains mandatory. Failure cannot select, erase, close or save
an old tab. No shared-process connection is introduced; the owned-child proof
still precedes the new-tab operation. Tests must cover a changed selection,
replacement/removal, duplicate creation and preserved old tabs. This design is
recorded before its production edits and remains unqualified until live tests.
