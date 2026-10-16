# 9B / 9C dashboard implementation and M5 evidence

Implemented application layout, typed note submission, sequenced task history, verified result display, fixed keyboard-accessible emergency Stop, exact-text approval previews and dependency status. Memory/settings remain deferred.

## Backend ownership and recovery

All task results come from authenticated task snapshots. Events use durable event IDs, deduplicate replay and reconnect with the last processed cursor. Each reconnect refreshes snapshots; a full reload replays history from zero without browser storage. No mount, reconnect or reload submits a task or resolves an approval. Uncertain task submissions retain their payload and request ID for an explicit retry. Approval decisions use a synchronous click guard and never retry automatically.

The backend currently exposes only `fs.create_note` through task creation. The UI deliberately offers filename and note content rather than implying arbitrary natural-language execution. The health response does not expose individual model, microphone, browser or worker readiness; those are visibly unreported. Approvals can be discovered from `approval_id` or `approval_ref` event payloads, but the existing task creation route does not currently emit a live approval workflow. Approval interaction qualification below therefore uses backend-contract fixtures.

Previews, event names, output names and errors render as React text. No extracted HTML is inserted. Approval review is an inline region so keyboard users can reach Stop without a modal focus trap. Visible focus styling, labelled controls, responsive wrapping and reduced-motion rules are included. Stop remains visible throughout authenticated use.

## Validation on 2026-10-16

- `npm run build`: passed, including backend schema/type regeneration.
- `npm test`: 20 tests passed across transport and event replay.
- `npm run lint`: passed without warnings.
- `backend/tests/live/m5_ui_contract.py`: Chromium fixtures passed for typed command submission, duplicate clicks, event replay/deduplication, reconnect cursor, task reload without mutation, expired approvals, duplicate approval clicks, keyboard Deny and Stop, literal HTML preview rendering, and 390px mobile overflow/Stop visibility. Laptop viewport: 1440px.
- `backend/tests/live/m5_dashboard_smoke.py --output .local/9bc-live`: real isolated backend passed verified note creation/readback, task idempotency, development authentication, production HttpOnly cookie/reload, logout and mobile overflow.
- Screenshots inspected at `.local/9bc-browser/laptop.png` and `mobile.png`; fixture report: `.local/9bc-browser/report.json`; real backend report: `.local/9bc-live/report.json`.

Run the fixture check with the backend virtual environment. It starts its own temporary Vite server on port 5174, uses no real tokens or desktop mutations, and stops its server when done. Browser qualification requires local socket/browser access outside the restricted sandbox. The real backend smoke requires the existing Vite server on 5173 and a free backend port 8765.
