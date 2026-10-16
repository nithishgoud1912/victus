# M2 section 6E: first workflows

Implemented two explicit workflows in `backend/victus/workflows/`. Every application,
browser, content-generation and filesystem step goes through `Dispatcher.dispatch_step`
and the same `ToolRegistry`. Trusted worker-local context supplies reviewed scopes and
argument authorization, cancellation, action budget, deadline, ledger, restricted payload
storage and content-free audit events. Output is bounded JSON; live objects remain in the
adapter. Each step has an independent verifier and no automatic retries. Effects whose
verification fails remain unknown. The existing M1 `WorkerSupervisor` owns the outer
process and terminates native hangs; async cancellation alone cannot stop a native call.

These workflows are explicit local qualification entry points. They are not added to
the F1 HTTP action schema or enabled as unrestricted public tools. The caller must review
the exact profile, item text, source URLs and destination before creating the trusted
context. A scope string alone is not approval for arbitrary arguments.

## Checklist

`create_notepad_checklist.py` launches an allowlisted executable, resolves an empty
editor under its process identity, sets bounded checklist text, independently rereads the
editor, chooses a new destination inside the approved workspace, invokes the profiled
Save As controls, sets and rereads the filename, invokes Save, and independently checks
exact encoded file bytes. No overwrite dialogs are accepted. A short-lived, one-use save
permit binds the destination to the launched application. UI controls stay on the COM
owner thread. Save dialog selectors can use `root_window: "save_dialog"`; disabled main
editors can be read while a modal dialog is open, but writes still require enabled controls.

`config/applications/qualified-app.example.json` is a placeholder, **not a qualified
Notepad profile**. On the target Windows/Notepad build, review the executable, exact
window/editor/menu/dialog IDs, names, control types, encoding and UIA patterns. The
supported route requires Value/Invoke patterns; optional keyboard fallback still requires
the adapter's immediate foreground check. Ambiguous windows block. Existing user work
must not be replaced. Native Save is not an atomic exclusive filesystem operation; use a
private workspace without untrusted concurrent writers. Exact bytes, including CRLF and
BOM, must match the configured encoding.

From `backend`, on a Windows machine with a reviewed profile:

```powershell
uv run python tests/live/workflow_qualification.py notepad --data-dir C:\VictusQualification\run1 --profiles C:\VictusQualification\profiles.json --profile approved-notepad --repetitions 20 --encoding utf-8
```

Use a fresh data directory per qualification. Repeat on each supported physical display
scale with multiple real windows. The runner records a pending physical-DPI gate rather
than inferring qualification from a label. Independent workflow steps capture measured
window DPI in restricted output payloads; review those and the real window configuration.

## Fixture research

`browser_research.py` accepts only explicitly reviewed loopback fixture URLs. Each source
is navigated, observed and independently reread before its snapshot is accepted. The
artifact contains URL, title, bounded visible text, observation reference and text hash.
Repeated observations and redirect aliases count once by final URL. Fragments cannot
create extra sources. Summary generation is a separate dispatcher step; a verified
summary/artifact does not satisfy the promised source count. An insufficient-source
artifact reports failure. Secrets and hidden page data remain excluded by the browser
observer. Public websites require separate scope review and target qualification.

```bash
# From backend; use the default installed pinned browser when available.
uv run python tests/live/workflow_qualification.py browser --data-dir /absolute/fresh/run --repetitions 20
# Optional explicit, absolute executable for a separately identified browser build:
uv run python tests/live/m2_browser_cases.py --browser-executable /absolute/chromium --output /absolute/new/cases.json
```

The real-browser cases cover duplicate buttons, stale fields, redirects and metadata
escape, blocked popups/downloads, dispatcher timeout, and isolation between two pages
at device scale factors 1, 1.25, 1.5 and 2. Redirects now commit an inert, CSP-blocked empty
document before an explicitly authorized next GET; this removes a Chromium abort/error-page
navigation race. Original redirect bodies and Location headers never reach the page.

## Recorded validation (Linux, 2026-10-16)

- Full Python suite: 242 tests passed; one existing Starlette deprecation warning.
- 20 independently supervised **real browser** fixture workflows passed. Every artifact
  verified two observed source URLs and file bytes. Five runs per device scale above,
  with actual `window.devicePixelRatio` recorded.
- 10 real browser adversarial/isolation cases passed.
- 20 separately parameterized **simulated Notepad** workflow tests passed, plus negative
  cases for duplicate windows, nonempty editors and wrong saved bytes. These test the
  real dispatcher/ledger and filesystem, using a fake native backend and simulated DPI.
- Native Windows Notepad: **0 executed / 20 requested**, blocked `WINDOWS_UIA_UNAVAILABLE`.
  Real Windows multiple-window, physical display scaling and 20-run qualification remain
  outstanding. M2 is not fully qualified.
- Browser evidence used explicitly configured Chromium **141.0.7390.37** with pinned
  Python Playwright **1.64.0**, because its expected Chromium 156/build1248 download failed.
  This version combination is reported, not silently substituted. Configured Chromium
  156 and arbitrary public websites remain unqualified.
- Ruff passes on all changed Python files. Repository-wide Ruff has five pre-existing
  findings in unrelated files.

Evidence: [20 browser runs](evidence/M2-6E-browser-20.json),
[adversarial cases](evidence/M2-6E-browser-cases.json),
[native Notepad blocked report](evidence/M2-6E-notepad-native.json),
[example source artifact](evidence/M2-6E-research-example.json).
