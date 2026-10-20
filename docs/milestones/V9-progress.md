# V9 — reliability and Windows release implementation

Base: merged V8 PR #12 (`4af156fa82d12d98d31aca08f21140d566773665`),
with its portable regression and incomplete model/audio/Windows gates. V6 remains unreconciled. Product version stays 0.1.0.

## Design before edits

Advertised source scope remains deterministic notes and reviewed command intake.
A Windows folder candidate is proposed for this bounded scope; it is not a
qualified release. Browser/native/model/voice obligations remain open and are
not silently removed by narrower packaging. No installation or public release
is authorized by this implementation.

Observed implementation gaps:

1. A short soak currently exits successfully even after recorded failures and
   computes qualification before server cleanup. Bind the final result to safe
   shutdown, preserve failure reports and keep smoke success distinct from the
   original two-hour gate. Bind source/config/contracts/locks as well as Python.
2. Package manifest creation can overwrite an existing manifest, accepts absent
   source identity and allows unlisted bundle additions. Require a verified
   source inventory for actual builds, exclusive manifest publication and exact
   file inventory verification; keep fixture-only manifest tests explicit.
3. Frozen self-tests use forced process termination without separate graceful
   shutdown accounting. Record forced cleanup truthfully; do not infer graceful
   server exit from Stop (Stop halts work, not the service).

Add focused negative tests before final portable regression. Run a real short
reliability workload with normal guards. A short workload does not replace the
7,200-second campaign, 100 verified tasks, two verified restores, zero failures,
RSS growth <=20% and health p95 <0.5 seconds. Record the full-duration gate as
pending if no complete final report exists. Windows package execution, owned
process observation, fresh-account/DPAPI and actual prior-artifact rollback
require their target environments and retained artifacts.

## Final portable verification

Final-source serial regression passed 1,004 backend tests and 23 frontend tests,
plus Ruff, frontend lint, API generation and build. Before/end release-input
identities match. Earlier regression passed 994 tests; final regression includes
additional identity/asset/CLI/abort cases. Dependency locks and public API are
unchanged. PowerShell and Windows executable tests were not run here.

The real 60.418-second core smoke passed: four admitted/verified tasks, four
memory cycles, one checksum-verified backup/restore, 120 health requests, zero
failures/pressure rejections, health p95 0.00422 seconds, warmed parent RSS growth
about 0.044%, completed server/work cleanup and no remaining multiprocessing
children. This is not the 7,200-second gate and does not prove Windows descendant
cleanup. No two-hour run is left active.

Release remains NO-GO: actual Windows package, graceful/descendant cleanup,
fresh-account/DPAPI, frozen advertised paths, retained-artifact rollback and
full-duration evidence are open. V7/V8 obligations remain recorded. See
[V9 test register](../V9-TESTS-AND-INCOMPLETE.md) and
[machine-readable status](../release/v9-release-status.json).
