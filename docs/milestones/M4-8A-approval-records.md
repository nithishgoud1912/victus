# M4 / 8A — Approval records

Implemented the record and permit primitives requested in section 8A.

## Records and states

`backend/victus/safety/approvals.py` defines an immutable `ApprovalBinding`,
`ApprovalRecord`, the supplied compact UTF-8 JSON SHA-256 algorithm, and a SQLite
`ApprovalStore`. Records contain task ID, action ID, tool name/version, canonical
argument hash, policy version, resolved target identity, observation identity,
preview reference, expiry, state and creation/update timestamps.

States progress as follows:

- `pending` → `approved`, `denied`, `expired` or `invalidated`.
- `approved` → `consumed`, `expired` or `invalidated`.
- `denied`, `expired`, `invalidated` and `consumed` are terminal.

Decisions require the exact binding. A changed binding invalidates the approval.
Expiry is checked at the exact boundary on reads, decisions, permit issuance and
consumption. The default review lifetime is 60 seconds, capped at 300 seconds.
Only trusted review code may call `decide`; a model's approval claim grants no
authority. These classes do not themselves authenticate HTTP callers.

## Single-use permits

`backend/victus/safety/permits.py` issues a random permit only for an approved,
unexpired record. Only a SHA-256 of the permit token is persisted. One approval
can issue one permit; losing that token requires a new approval request.

Consumption checks every binding under a SQLite write transaction and commits
`consumed` before returning. Concurrent callers and reopened stores cannot consume
the same permit twice. A crash after consumption cannot replay the permit. A
permit authorizes one dispatch attempt, not a successful outcome or a retry.
Uncertain writes must still become `unknown` in the action ledger.

## Preview protection and retention

Preview bodies are separate from approval metadata. They are JSON objects bounded
to 128,000 bytes, stored atomically with the request. On Windows, current-user
DPAPI encrypts bodies before database insertion; protection failure fails closed.
The Windows protection is exercised by the local tests. On POSIX, storage uses
the private database file with mode 0600 rather than DPAPI encryption.

Preview access requires both the approval ID and matching task ID and is limited
to pending/approved, unexpired records. Preview expiry matches approval expiry.
`purge_expired()` removes expired bodies while retaining approval metadata;
ordinary store operations also clear expired bodies. A service maintenance caller
must schedule cleanup when there is no approval-store traffic. Cleanup is logical
deletion; SQLite pages, WAL files and backups are not a forensic erase guarantee.
DPAPI does not protect against another process running as the same Windows user.

The argument hash binds the payload and does not encrypt it. Avoid copying raw
arguments or preview bodies into ordinary logs or events.

## Migration and integration boundary

Migration `0005_approval_records.sql` retains the original decisions in
`approvals_legacy` and imports their IDs as `invalidated` records with explicit
unbound placeholders. Old approvals cannot issue new permits. The migration and
its schema-version record commit atomically; a failed migration rolls back.

At the 8A milestone, this section added reusable durable stores. It did not replace the existing
agent's callback/proposal-reference approval gate, add approval API/dashboard
routes, or change existing workflow-specific upload/download permits. Connecting
the new records to the agent execution path is now implemented in
`M4-8B-8C-dispatch-review.md`. Workflow-specific upload/download reviews remain
separate adapter safeguards.

For that integration, prepare the ledger action ID before requesting review,
derive identities from trusted live resolution, and hash the final validated
arguments with `argument_hash`. Do not reuse the older ledger `_canonical_hash`:
its serialization differs. Keep existing ledger hashes readable for old actions.
Immediately before dispatch, revalidate live policy/target/observation, consume
the permit within the stop/mutation barrier, and dispatch using that same action
ID. Never regenerate a permit automatically after an uncertain write.

## Validation

`backend/tests/test_approvals.py` covers the exact hash, non-JSON inputs, all
binding mismatches at each gate, pending/denied/expired/invalidated/consumed
behavior, exact-boundary expiry, preview isolation/encryption/retention, protection
failure, counterfeit permits, concurrent issuance/consumption across reopened
stores, legacy migration and migration rollback. Regression results are recorded
in `.local/8a-regression.xml` and `.local/8a-regression.log`.

Validation on 2026-10-16: **426 tests passed in 145.58 seconds**, including 49
new approval tests. Ruff lint/format checks, Python compilation and
`git diff --check` passed. No real-model benchmark or live UI workflow was run.
