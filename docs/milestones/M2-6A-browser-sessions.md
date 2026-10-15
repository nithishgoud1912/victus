# M2 / 6A — Browser session ownership

Section 6A of the VICTUS v1 implementation roadmap is implemented in
`backend/victus/adapters/playwright/session.py`.

## Contract

- `await BrowserSession.start()` launches VICTUS-owned Chromium and one context.
  It does not attach to an existing browser. Repeated starts are serialized and
  do not launch duplicate browsers.
- `await BrowserSession.new_page()` returns a frozen `PageReference` containing
  opaque session and page IDs. It does not navigate or return a live `Page`.
- `await BrowserSession.close()` invalidates references, closes the context,
  closes the explicitly launched browser when applicable, and stops Playwright.
  Cleanup continues if context closure fails. Repeated close is harmless.
- `async with BrowserSession() as session:` owns the same lifecycle and closes
  resources when the block exits, including exceptional exits.
- Construction launches nothing. First use binds ownership to the process ID,
  thread ID and running event loop. All subsequent use must remain there.
  The session cannot be pickled. A closed session can be restarted on its original
  loop; old references remain invalid.
- The adapter retains its pages internally and forgets closed pages. Internal
  adapters may use `_resolve_page()` only on the owner loop. Never put its result
  in tool responses, queues or process messages. This page identity is separate
  from the observation/element target references planned for 6B.

Create the session **inside** a future browser worker. A parent may send typed
operation requests and `PageReference` data to that worker; the worker resolves
references and runs each operation locally. Do not create a session in the API
process and send it to a child, or wrap each browser call in a new `asyncio.run()`.
The existing per-action filesystem worker is unchanged. Browser tool stubs remain
stubs until observation, scope checks and verifiers are implemented.

## Ephemeral and persistent modes

Default sessions use a fresh, nonpersistent context. Supplying `data_dir` alone
still uses this default. No cookie files, screenshots or traces are written by
this adapter. Browser-managed temporary files are handled by Playwright.

Persistent login state requires explicit application configuration:

```python
from victus.adapters.playwright.session import BrowserSession

# Run this block inside the browser worker's single asyncio event loop.
async with BrowserSession(
    data_dir=settings.data_dir,
    profile_name="research",
    headless=False,
) as session:
    page_reference = await session.new_page()
```

The profile is derived as `<VICTUS data>/browser-profiles/research`. Profile names
allow only lowercase letters, digits, underscores and hyphens (1–64 characters,
starting with a letter or digit). The adapter rejects profile path traversal and
links escaping the designated directory. An OS file lock prevents two sessions
from concurrently opening the same profile. The lock is released on shutdown or
failed startup. Treat `data_dir` as trusted application configuration, never model
input, and keep it separate from the normal Chrome/Edge user-data directory.
Persistent login data remains on disk after close; use disposable directories in
tests and never commit real profiles.

The default binary is bundled Chromium, with an optional explicit `channel` of
`chromium`, `chrome` or `msedge`. No silent browser fallback occurs. Launch and
page-operation timeouts default to 30 seconds and must be positive and finite.
Downloads are not accepted automatically. Full URL, redirect, popup, upload and
request restrictions belong to 6C; this lifecycle layer is not a safe public
navigation tool by itself.

## Verification

From `backend/`:

```powershell
uv sync --group dev --locked
uv run pytest tests/test_browser_session.py -W error
uv run ruff check victus/adapters/playwright tests/test_browser_session.py tests/live/browser_probe.py
uv run ruff format --check victus/adapters/playwright tests/test_browser_session.py tests/live/browser_probe.py
uv run playwright install chromium
uv run python tests/live/browser_probe.py
# Optional on a machine without a visible desktop:
uv run python tests/live/browser_probe.py --headless
```

The probe uses the real session adapter, a fresh context and local in-memory HTML.
It resolves one accessible button and closes the session; it contacts no public
website and creates no persistent login profile.

Implementation-environment results (Linux, Python 3.12.14, Playwright 1.64.0):

- 25 browser-session unit cases pass with warnings treated as errors. Cases cover
  lifecycle serialization, fresh contexts, opaque/stale/foreign/closed references,
  process/thread/loop ownership, startup failure and cancellation cleanup,
  shutdown failure cleanup, explicit persistence, profile lock contention and
  release, invalid configuration and linked-profile rejection.
- Changed Python files pass Ruff lint and formatting checks.
- All 89 backend tests pass, with one existing Starlette deprecation warning.
  The environment's HTTP proxy variables were removed for this test invocation
  so the existing loopback SSE test could initialize its HTTP client without an
  unrelated missing SOCKS dependency. No production proxy settings were changed.
- Live Chromium qualification is **blocked**: the browser installer downloaded an
  invalid/truncated archive; the probe then reported the missing browser binary.
  Unit tests use mocked Playwright and do not prove real-browser or Windows
  behavior. Run the live probe on the target Windows machine before qualifying
  the milestone. Real cookie persistence also remains to be qualified there.
- Repository-wide Ruff checks report five existing lint issues and 14 existing
  files needing formatting, outside this change. No unrelated formatting changes
  were made.

This implements 6A only. It does not qualify 6B–6E, arbitrary websites, normal
browser profiles, Windows UI Automation or the full M2 release gate.
