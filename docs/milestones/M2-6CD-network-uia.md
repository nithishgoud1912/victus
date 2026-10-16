# M2 / 6C and 6D — Scoped network, file transfers and Windows profiles

These adapters extend the merged 6A/6B code. They do not activate browser or
desktop tool stubs, introduce unrestricted shell execution, or claim the full M2
qualification gate. The dispatcher still owns action authorization, cancellation,
audit, worker supervision and ledger/final status. Application workflows and their
postconditions belong to 6E.

## 6C Network mediation

`adapters/playwright/network.py` defines immutable `WebScope` and `WebRequest`
contracts and a worker-local `NetworkGuard`. Install a guard through
`BrowserSession(network_guard=guard)` before creating a page. Without a guard,
sessions deny HTTP and WebSocket routing by default. All contexts block service
workers. Scoped networking deliberately requires an ephemeral context; persistent
profiles are not accepted in this mode, to avoid restoring active pages before
restrictions are installed.

```python
from victus.adapters.playwright.network import NetworkGuard, WebScope
from victus.adapters.playwright.session import BrowserSession

# Build these from the current task's trusted scope and dispatcher policy.
scope = WebScope(task_id=task_id, origins=frozenset({"https://example.com"}))
guard = NetworkGuard(scope, authorize=authorize_request)
async with BrowserSession(network_guard=guard) as session:
    page_ref = await session.new_page()
    await session.navigate(page_ref, "https://example.com/reviewed-page")
```

`authorize_request(WebRequest) -> bool` is mandatory trusted policy code, never a
model-selected flag. Every HTTP request needs authorization after scope checks,
including GET, subresources and upload requests. Policy receives task ID, exact
URL, method, resource type and a SHA-256 body digest. It must match the expected
operation/permit; neither GET nor an in-scope origin means an action is safe.
Returning anything other than literal `True` denies the request.

- Initial navigation, requests and redirect destinations require exact approved
  HTTP(S) origins. File/data/javascript URLs, credentials, malformed URLs and
  unexpected origins are rejected by the adapter entry point.
- DNS resolution has a deadline. Every returned address is checked. Loopback and
  non-global addresses require separately reviewed **exact IPs**; no blanket LAN
  exception exists. Link-local, multicast, unspecified/reserved and known cloud
  metadata addresses are denied even if listed as exceptions. Metadata hostnames
  and AWS IPv6/Azure/Alibaba metadata addresses are explicitly denied.
- HTTP is mediated through HTTPX to a validated numeric IP while preserving Host
  and TLS server name/certificate validation. No browser DNS second lookup occurs
  for these requests. Proxy environment settings, transport retries and connection
  reuse are disabled. This avoids DNS rebinding between validation and connection
  and avoids sharing a TLS connection between two hostnames at the same IP.
- Redirect responses are not handed back unchecked to Chromium. Explicit safe
  navigation follows a bounded sequence of freshly validated/authorized GET/HEAD
  requests and detects loops. Requests with bodies are never replayed. Resource,
  form and site-initiated redirects fail closed and need a new dispatcher decision.
- Popups are denied by default, including their first HTTP request. If explicitly
  enabled, the same request rules apply. Out-of-scope committed documents close
  the owned page. WebSockets and browser-native/blob exports are denied.
- Per-request/response bytes and DNS/network/navigation deadlines are bounded.
  Encoded responses and multiple Set-Cookie responses currently fail closed rather
  than silently changing decoding/cookie semantics. These restrictions can make
  some real sites unsupported; arbitrary-site compatibility is not qualified.

This is an HTTP adapter, not an OS egress firewall. Do not expose raw Page/CDP,
custom routes, context.request or other networking APIs to a model; trusted fixture
probes may override routes deliberately. Browser background/non-HTTP protocols and
Chromium lifecycle behavior need target-machine qualification/OS isolation before
claiming protection against arbitrary hostile sites. No such release claim is
made here. HTTPX's SNI transport extension is covered by tests against the pinned
HTTPX/HTTPCore versions and must be requalified on dependency updates.

## Downloads and uploads

`downloads.py` stages bounded bytes under `<VICTUS data>/download-staging/` using
opaque, exclusively created filenames; server filenames are ignored. Staging
receipts bind task, content hash and byte count. An authorized attachment response
is intercepted into staging and the browser download request is aborted. Other
native/blob exports are cancelled. No download is automatically opened or moved.

```python
staging = DownloadStaging(data_dir, task_id, destination_roots=(approved_output_root,))
guard = NetworkGuard(scope_with_download_permission, authorize=authorize_request, staging=staging)
# After a trusted policy/UI review of the receipt and exact destination:
permit = staging.approve_release(receipt, approved_output_root / "chosen-name.txt")
output = staging.release(permit)
```

Release permits are single-use, expire after 60 seconds and bind the exact receipt
and destination. Bytes are rehashed before release. Destinations must be concrete
new files directly under preapproved roots; traversal, linked/existing targets,
Windows device names and alternate-data-stream syntax are rejected. Output uses
exclusive creation and never overwrites. Roots must be protected application/user
configuration; this is not isolation from an attacker who controls the filesystem
namespace. Windows ACLs and disk retention are not newly qualified here. Old
staging files survive restart without a permit and are never promoted blindly;
retention/recovery belongs to M7. `discard()` removes an explicitly identified
staged receipt.

`uploads.py` separates a concrete `UploadReview` from an upload preparation permit.
The review lists exact file paths, sizes and hashes plus the exact destination URL.
Only regular files directly under reviewed source roots are accepted (no directory
or wildcard upload). Approval is a trusted policy entry point, never a planner
tool. Permits expire after 60 seconds and are single-use. Files are reread/rehashed
at execution; the adapter passes reviewed byte buffers, not reopenable filesystem
paths, to the pinned file input.

`prepare_input(resolver, ref, observation_id, permit, destination)` requires the
same network task ID, a fresh uniquely resolved native file-input target and a
matching current form action. It invalidates the observation after an attempt.
This prepares the input only: it does not submit or claim a successful upload.
Any script-triggered send/form submission still goes through the request policy;
reviewing files does not authorize arbitrary later requests or redirects. A native
preparation error is uncertain, consumes the permit and is not automatically retried.

Pass the same `UploadReviews` instance as `NetworkGuard(..., uploads=reviews)`.
Input preparation arms a 60-second single-use send capability. The network mediator
parses multipart file parts and checks the exact destination, ordered filenames,
sizes and SHA-256 hashes before connecting, independently of the request authorizer.
Unreviewed parts, substitutions, extra files and replays are blocked. Custom
non-multipart JavaScript upload protocols are not qualified; their request policy
must not grant generic JSON/POST permission without reviewing the actual operation
and body digest.

## 6D Windows profiles and ownership

`adapters/uia/applications.py` defines exact `ApplicationProfile` and
`ControlSelector` contracts, strict JSON configuration loading, process references
and `UIAWorker`. `native.py` owns lazy Windows/pywinauto bindings. There are no
import-time COM connections, launches or desktop inspections.

Construct/start/use/close a worker in **one supervised Windows process and thread**.
It explicitly initializes a COM MTA apartment before importing/connecting UIA and
balances its initialization on close. A conflicting apartment or non-Windows host
fails closed. Worker objects are not picklable; only opaque application/control
references and typed operation data may cross the worker transport. Read trusted
JSON inside the worker instead of passing COM objects from the API/planner.

The example `config/applications/qualified-app.example.json` is deliberately a
placeholder, not an assumed working Notepad profile. Fill in the real installed
executable and selectors observed during M0 qualification. Modern Notepad may
handoff to a different process or expose a different editor tree; this adapter
blocks a failed process binding rather than guessing a replacement window.

- Launch uses only the selected allowlisted absolute `.exe` and fixed profile
  arguments, with `shell=False`. Optional SHA-256 pinning detects an executable
  update and requires profile review.
- Binding records PID, Windows process creation time and executable image path.
  Every resolution checks that identity and liveness. Restart/PID reuse invalidates
  old references; explicitly launch/bind again and resolve new controls.
- `selectors.py` matches the configured window and child automation ID, control
  type and optional exact name under that process. Several possible windows or
  controls are blocked, never reduced to the first match. Reacquisition checks the
  original UIA runtime IDs so replacing a same-named control requires a new reference.
- `actions.py` uses ValuePattern and InvokePattern first. SetValue is verified by
  independent CurrentValue readback. Invoke remains **unverified** until an
  application-specific postcondition is observed. Failed patterns do not trigger
  keyboard retries; only an unsupported pattern may use fallback.
- Keyboard fallback requires both profile permission and an explicit action opt-in.
  Text fallback is limited to qualified empty Edit/Document controls, proved empty
  through TextPattern; it does not replace existing unsaved content. Braces/Ctrl
  syntax is sent as literal UTF-16 Unicode input, never parsed as key commands.
  Invoke fallback supports qualified Button/Hyperlink/MenuItem targets using Enter.
- Foreground HWND, process and focused control are checked before **each** input.
  The native backend checks HWND/process again immediately before SendInput and
  consumes that check, requiring a fresh one for the next key. Windows can change
  focus asynchronously; this minimizes but cannot make global input transactional.
  Lost focus before typing blocks; interruption after partial typing is uncertain.
  Keyboard output remains unverified. Raw private native errors are not exported.
- Closing COM ownership deliberately leaves launched apps open for inspection,
  avoiding loss of unsaved work. Only the just-launched owned process is terminated
  if its initial binding fails; unrelated windows/processes are never terminated.

## Checks and live qualification

From `backend/`:

```powershell
uv sync --group dev --locked
uv run pytest
uv run pytest tests/test_browser_network.py tests/test_browser_transfers.py tests/test_uia_profiles.py tests/test_browser_session.py tests/test_browser_observation.py -W error
uv run ruff check victus/adapters/playwright victus/adapters/uia tests/test_browser_network.py tests/test_browser_transfers.py tests/test_uia_profiles.py tests/test_browser_session.py tests/live/browser_network_probe.py tests/live/uia_profile_probe.py
uv run ruff format --check victus/adapters/playwright victus/adapters/uia tests/test_browser_network.py tests/test_browser_transfers.py tests/test_uia_profiles.py tests/test_browser_session.py tests/live/browser_network_probe.py tests/live/uia_profile_probe.py
uv run playwright install chromium
uv run python tests/live/browser_network_probe.py
# On Windows, after recording and reviewing your actual profile:
uv run python tests/live/uia_profile_probe.py --profiles ../config/applications/your-qualified-profile.json --application your-app --control editor
# Explicit opt-in to a write for qualification; inspect the app afterwards:
uv run python tests/live/uia_profile_probe.py --profiles ../config/applications/your-qualified-profile.json --application your-app --control editor --text "VICTUS qualification"
```

The browser live probe uses only a disposable loopback fixture with an explicit
127.0.0.1 exception. It tests scoped navigation/redirects, a denied consequential
GET, blocked metadata redirect, attachment staging and explicit fixture release.
The Windows probe launches only the supplied profile and performs no text/invoke
operation unless that CLI argument is explicitly supplied. It leaves the app open.

All 206 backend tests pass (one existing Starlette deprecation warning), including
73 added cases for this increment. All 142 focused browser/transfer/UIA cases pass
with warnings treated as errors. Proxy variables were removed for the local full
suite to avoid the existing SSE test's unrelated missing SOCKS dependency. Changed
Python files pass pinned Ruff lint/format checks; five existing repository-wide
lint issues outside this change remain. Deterministic tests use fake
Playwright/UIA boundaries; a separate **real loopback HTTP test** proves numeric-IP
mediation, original Host preservation and ignored proxy settings. Live Chromium
qualification is blocked here by the missing browser executable (the earlier
installer returned an invalid archive). Native UIA/COM/SendInput cannot be qualified
on this Linux host. Run both documented probes on the target Windows machine,
including multiple windows, restarts and foreground stealing, before enabling real
device-control tools. No dependency or lockfile changes are required.
