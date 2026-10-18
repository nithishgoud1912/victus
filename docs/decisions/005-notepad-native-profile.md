# Decision 005: Installed Notepad ownership and native profile

Date: 2026-10-18. Scope: V2.4 source candidate, Windows Notepad 11.2607.14.0.

Preserve JSON profiles and the shared dispatcher. The installed Store Notepad
launches a separate UI process. A profile may explicitly select `owned_child`
only with a pinned executable hash. Bind only one direct child with the same
image and a creation time no earlier than the live launcher. Recheck ancestry
while the launcher is live, then hold a read-only process handle and revalidate
PID, creation time and image on every operation. A later launcher exit does not
invalidate an already pinned child. Reuse of an existing background process,
unreadable ancestry, multiple children or multiple matching windows blocks.
No search by window title, guessed PID, launch switch or user setting is used.

Windows ancestry follows Microsoft's
[PROCESSENTRY32W](https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/ns-tlhelp32-processentry32w)
and [Process32FirstW](https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/nf-tlhelp32-process32firstw)
contracts. The child lease has query/synchronize rights, no termination right.
Failed binding closes the lease and cleans up only the original Popen launcher.
Normal worker close releases COM/leases without closing user documents.

Exact class constraints supplement control type, automation ID and name. The
observed Save As dialog is a descendant Window beneath a disabled main Window;
resolve it within the same pinned process/main and reacquire references after
transitions. Independent readback remains mandatory. Notepad's RichEdit exposes
CR line endings; opt-in `crlf` normalization changes line endings only. Prove
the editor empty again immediately before writing, including Value pattern writes.

Use Value/Invoke patterns with the observed filename **host ComboBox** rather
than its inner Edit. An isolated host test saved exact requested UTF-8 bytes.
The inner Edit's successful readback did not prove the dialog committed that
path. Pattern completion never substitutes for exact destination/file verification.
The candidate disables keyboard fallback. Experimental filename keyboard code
was removed; no coordinate input is used.

The profile remains unqualified: full supervised runs have not passed and the
final launch safely blocked on background process reuse. It is not registered
in the default task service. A reproducible supported launch/save route and
native adversarial/repetition/DPI evidence are required before enabling it.
