# M2 / 6B — Observations and target references

Implements roadmap section 6B on the merged 6A session adapter. This is an adapter
increment, not a new public browser API or a claim that M2 is fully qualified.

## Files and contracts

| File | Responsibility |
| --- | --- |
| `backend/victus/adapters/playwright/observation.py` | `BrowserObserver.observe(page_ref)` returns a serializable `Observation`: opaque observation ID, URL, title, bounded rendered text and actionable targets. |
| `backend/victus/adapters/playwright/locators.py` | `TargetResolver.resolve_target(ref, observation_id)` checks origin, document freshness, age, unique exact role/name match and the original node's semantic identity. |
| `backend/victus/adapters/playwright/_dom.py` | Worker-local DOM helpers for visible text, node identities and document/mutation stamps. |
| `backend/victus/adapters/playwright/actions.py` | `fill_target()` resolves and pins a checked field, fills it with a finite timeout and invokes independent verification. |
| `backend/victus/tools/verifiers/browser.py` | `verify_field_value()` reads the actual field value and compares it with the expected text, rechecking identity, origin and uniqueness. |

Each public target has `ref`, `role`, `label` and `operations`. IDs contain no CSS
selectors, DOM indexes or content. Dataclass results can be converted with
`dataclasses.asdict()` for a typed operation transport. Live locators, page/node
handles and node identity metadata stay in the worker. `resolve_target()` returns
an internal pinned-node object, which must never be serialized or exposed as a
public tool result. Internal callers must dispose its element handle; the fill
helper does this in `finally`.

Example inside the owning browser worker:

```python
from victus.adapters.playwright.actions import fill_target
from victus.adapters.playwright.locators import TargetResolver
from victus.adapters.playwright.observation import BrowserObserver

# session is already started; page_ref identifies a page on an approved origin.
resolver = TargetResolver(session, allowed_origins={"https://example.com"})
observer = BrowserObserver(resolver)
observation = await observer.observe(page_ref)
# Pass only observation data to the planner. It proposes IDs, not selectors.
name = next(target for target in observation.targets if target.label == "Name")
verified = await fill_target(resolver, name.ref, observation.observation_id, "VICTUS")
# False is unverified, never successful completion. Reobserve before the next action.
```

The resolver must be constructed from **trusted task scope**, not from a model's
chosen URL or proposed risk level. Origins match exactly after scheme/host/default
port normalization. Credentials and opaque/non-HTTP URLs are rejected; no wildcard
or subdomain expansion occurs. This does not intercept requests or redirects:
network-level enforcement remains section 6C.

## Privacy, bounds and supported surface

- Text extraction visits at most 10,000 text nodes and returns at most 4,000
  characters by default (configurable up to 16,000). It excludes hidden,
  transparent, inert and ARIA-hidden content, scripts/styles/templates, input
  values, textarea contents, select contents and editable-container contents.
- Password/hidden inputs and password/OTP autocomplete fields are not advertised.
  Hidden associated/referenced label content is also rejected. Accessible names
  come from Playwright ARIA snapshot headers; field values and snapshot child
  content never enter observation output. Unnamed or oversized names are omitted.
- Titles are capped at 512 characters, labels at 256. URLs over 2,048 characters
  fail observation rather than silently changing the URL. The requested current
  URL and title remain visible; this is not a general secret classifier.
- At most 200 candidate elements are scanned and 40 targets returned by default.
  Bounds are configurable within fixed limits. The registry retains at most 32
  observations by default, evicts oldest records, and replaces the previous
  observation of the same page. Observation has a 15-second overall deadline.
- This increment supports main-frame, light-DOM controls with named native/ARIA
  roles. Native text/email/URL/tel/search/number inputs and textareas support fill
  and value reads. Disabled/readonly fields are omitted. Custom editors, shadow
  DOM and iframe targeting require separate qualification and are not followed.
- Other controls advertise their native operations (click/check/select); this
  increment implements only the guarded fill operation. Advertising an operation
  is neither authorization nor a promise of an already registered tool handler.

Treat all page text as untrusted data. DOM mutation counters and node IDs are
freshness evidence, not a security boundary against hostile page JavaScript.
No observation is written to disk or audit logs by these helpers.

## Freshness and write behavior

Each document has an in-memory identity, mutation counter and observed URL.
DOM mutations and input/change events conservatively stale observations. A new
document invalidates old references even at the same URL. Navigation, expired
observations (default 30 seconds), reobservation, unknown/foreign IDs, duplicate
matches, hidden/disabled nodes, changed semantics and replaced nodes block writes.
The adapter never chooses the first duplicate match or silently reobserves/retries
an old proposed action. The caller must explicitly observe again and decide again.

Resolution checks freshness again after its asynchronous identity checks. Filling
pins that checked DOM node instead of allowing a role locator to retarget a
replacement during Playwright auto-wait. Page scripts may still change a live
page during an operation; this does not make arbitrary sites transactional.
Observation and fill requests through the same resolver are serialized.

After an attempted fill the observation is invalidated, including on failure or
cancellation. Input events generated by filling deliberately change the mutation
counter, so the independent verifier checks the resulting field's identity,
origin, uniqueness and actual value rather than treating that old counter as
postcondition evidence. The verifier returns only a boolean and never returns or
logs actual/expected field contents. Native fill exceptions are exposed as the
safe `BROWSER_FILL_UNCERTAIN` error rather than Playwright logs that may contain
typed text; an attempted uncertain write must not be blindly retried.

The dispatcher still owns validation, task scope, approvals, cancellation, audit,
worker deadlines, ledger transitions and final action/task status. No browser tool
stub is activated by this increment. No raw page/locator or arbitrary selector is
accepted from a model.

## Verification and qualification

From `backend/`:

```powershell
uv sync --group dev --locked
uv run pytest tests/test_browser_observation.py tests/test_browser_session.py -W error
uv run pytest
uv run ruff check victus/adapters/playwright victus/tools/verifiers/browser.py tests/test_browser_observation.py tests/live/browser_observation_probe.py
uv run ruff format --check victus/adapters/playwright victus/tools/verifiers/browser.py tests/test_browser_observation.py tests/live/browser_observation_probe.py
uv run playwright install chromium
uv run python tests/live/browser_observation_probe.py
```

The explicit live probe uses a fresh session, a checked-in HTML fixture and
Playwright route fulfillment at `https://fixture.victus.test`. It never fetches
that hostname: fixture requests are fulfilled locally and other requests aborted.
It checks hidden/password/value exclusion, verified fill, postcondition mismatch,
reobservation, mutations, replacement, duplicate buttons, navigation, same-URL
reload and origin rejection. It is intentionally not auto-collected by pytest.

Implementation results (Linux, Python 3.12.14, pinned Playwright 1.64.0):

- 44 new deterministic tests and the 25 existing session tests pass with warnings
  treated as errors. These use mocked Playwright; they prove adapter contracts,
  guards, failure handling and independent value comparison, not actual DOM or
  accessibility behavior in a browser.
- JavaScript DOM helper functions pass a Node syntax check.
- All 133 backend tests pass with one existing Starlette deprecation warning.
  Proxy environment variables were removed for this local regression invocation
  to avoid the existing loopback SSE test's unrelated missing SOCKS dependency.
- Changed Python files pass lint and formatting checks using pinned Ruff 0.17.1.
  Repository-wide lint still reports the same five pre-existing issues outside
  this change. No unrelated source or formatting fixes were applied.
- **Live DOM/browser qualification is blocked.** The bundled Playwright Node
  binary segfaulted in this environment. Using the installed Node runtime let the
  installer run, but its Chromium headless-shell download returned an invalid
  archive. The real fixture probe then reported a missing browser executable.
  Run the documented probe on the target Windows machine; no live-browser success
  or full M2 gate is claimed here.

No package dependency or lockfile change is required.
