# VICTUS dashboard

This React/TypeScript dashboard provides sessions, notes, supported commands and
clarification, checklist submission/review, task history/results, Stop, reviewed
voice, memory and optional integration controls. The server reports which
capabilities are enabled; a visible form does not enable an unqualified adapter.
See [the current capability matrix](../docs/supported-workflows.md) and
[V7 validation and incomplete work](../docs/V7-TESTS-AND-INCOMPLETE.md).

The bundled research form uses only server-admitted fixture source IDs and a new
JSON report filename. It preserves the exact request on an uncertain response.
Dependency readiness separates qualification from current RAM/disk pressure and
shows the pinned model's availability without claiming measured inference quality.
Unknown task results explain read-only inspection; refreshing does not repeat an effect.

Confirmed voice transcripts use the same command service as typed requests.
Native Save always requires its separate exact-action review. Refresh/reconnect
reads saved state and never submits work. The historical 9A evidence below applies
to its original revision, not every later feature.

## Development

From the project root in PowerShell:

```powershell
./scripts/Install-Node.ps1
. ./scripts/Use-Node.ps1
Set-Location dashboard
npm ci
npm run dev
```

The installer verifies the official download checksum and installs project-local Node 24.22.0 LTS without replacing your system Node. Vite uses exactly `http://127.0.0.1:5173` and refuses to select another port.

In a second terminal, from the project root, start the existing backend environment:

```powershell
$env:VICTUS_DASHBOARD_DEV_ORIGIN = 'http://127.0.0.1:5173'
if (-not $env:VICTUS_API_TOKEN) {
    $env:VICTUS_API_TOKEN = & ./backend/.venv/Scripts/python.exe -c 'import secrets; print(secrets.token_urlsafe(32))'
}
Write-Output $env:VICTUS_API_TOKEN
./backend/.venv/Scripts/victus.exe serve
```

Paste the token from your own terminal into the dashboard. Development keeps it in memory; refreshing requires signing in again. Do not put it in a `VITE_` variable, URL, browser storage or source file. The application does not automatically load `.env` files.

## Production on this computer

Run `npm run build` inside `dashboard`, then start the backend without the development-origin setting:

```powershell
Remove-Item Env:VICTUS_DASHBOARD_DEV_ORIGIN -ErrorAction SilentlyContinue
./backend/.venv/Scripts/victus.exe serve
```

Open `http://127.0.0.1:8765`. Sign-in exchanges the token for a 15-minute HttpOnly, SameSite=Strict cookie and clears the in-memory bearer. Refresh restores the session; logout revokes it. Sessions also end when the backend restarts. Cookies are scoped to `/api`; Secure is disabled for this loopback HTTP deployment. Cookie-authenticated mutations require the exact backend Origin. Only the built index and assets are publicly served; API access still requires authentication.

## API types and checks

```powershell
npm run api:generate
npm test
npm run lint
npm run build
npm audit
```

Build automatically exports the current backend schema and regenerates TypeScript. It needs `backend/.venv` (or an explicit `VICTUS_PYTHON` executable). The offline export does not read a real token, start services or enable public documentation routes. `openapi.json` is outside the public assets. Do not edit `src/api/generated` manually.

`src/api/client.ts` is the sole authenticated browser request function. It uses generated operation types, request IDs, normalized errors, cancellation and bounded timeouts. It never automatically retries a mutation. Future event streaming can use its authenticated stream mode.

The generated Vite TypeScript configuration remains the base. `@hey-api/openapi-ts` supports this template's TypeScript 6; only its type generator is enabled. A narrow dependency override moves its parser's `js-yaml` to patched 4.3.2. The generated lockfile records resolved dependencies.

The official [Vite guide](https://vite.dev/guide/) was checked before scaffolding: it requires Node 20.19+ or 22.12+. Node 24.22.0 was listed as LTS on the official [Node download page](https://nodejs.org/en/download).

Real Chromium qualification is available from the project root with Vite running and backend port 8765 free:

```powershell
./backend/.venv/Scripts/python.exe backend/tests/live/m5_dashboard_smoke.py --output .local/dashboard-browser-check
```

Choose a new output directory each run. This starts an isolated test backend, verifies a test note and deduplication, checks development and production sessions, and stops its backend afterwards.

## Verification recorded on 2026-10-16

- Backend regression: 498 passed, including 18 dashboard transport tests.
- Frontend: 16 tests passed; TypeScript production build and Oxlint passed.
- Dependency audit: zero known vulnerabilities after the narrow parser override.
- Chromium: development memory-only authentication; deduplicated, verified test note; production HttpOnly session, refresh restoration, no bearer after bootstrap, logout revocation, no browser storage, and no mobile horizontal overflow. No page errors.
- Local evidence: `.local/9a-regression.log`, `.local/9a-regression.xml`, and `.local/9a-browser-verified/report.json` with desktop/mobile screenshots.

These checks cover section 9A. They do not qualify the real-model 30-goal benchmark or the remaining dashboard sections.
