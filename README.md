# VICTUS — Local desktop and browser assistant

VICTUS uses bounded local commands, a durable queue, supervised workers,
exact-action approvals and independent verification. The React dashboard includes
notes, supported commands/clarification, checklist review, task history, Stop,
reviewed voice and memory controls. Capability availability is server-owned.

- [Setup and local authentication](dashboard/README.md)
- [Current supported workflows](docs/supported-workflows.md)
- [V4 implementation, unrun tests and incomplete work](docs/V4-TESTS-AND-INCOMPLETE.md)
- [Revised V4 implementation plan](outputs/VICTUS-v4-Revised-Next-Stage-Implementation-Plan.md)
- [Windows folder build and release procedure](docs/release/README.md)

This is a 0.1.0 candidate. V4 names the implementation guide, not a released
product version. Native/browser/model/voice gates remain explicit; module presence
does not enable arbitrary computer control or public-web research. Cloud and wake
are optional and default off. Portable Linux validation and remaining failures are recorded in the handoff;
Windows/hardware qualification remains open before enabling new capabilities.

## Earlier implementation records

Browser session ownership (roadmap section 6A) is implemented. See
[the implementation and verification notes](docs/milestones/M2-6A-browser-sessions.md)
for lifecycle usage, dedicated persistent profiles, tests and the live probe.

Browser observations and guarded target references (roadmap section 6B) are implemented.
See [usage, tests and qualification limits](docs/milestones/M2-6B-browser-observations.md).

Task-scoped network/file-transfer restrictions and Windows application-profile adapters
(roadmap sections 6C/6D) are implemented. See
[usage and target-machine qualification](docs/milestones/M2-6CD-network-uia.md).

The first dispatcher-routed checklist and local browser research workflows (section 6E)
are implemented. See [workflow usage, M2 evidence and remaining Windows qualification](docs/milestones/M2-6E-workflows.md).

The model gateway and strict action/finish parser (section 7A) are implemented.
See [budgets, schema repair and pending live model qualification](docs/milestones/M3-7A-model-gateway.md).

The bounded StateGraph and persistent SQLite checkpoints (section 7B) are implemented.
See [domain-service composition, restart recovery and graph tests](docs/milestones/M3-7B-state-graph.md).

The React dashboard transport and session foundation (section 9A) is implemented.
See [dashboard setup, local sessions, generated API types and checks](dashboard/README.md).
Current dashboard/command/voice behavior is described in the V3/V4 milestones.
## M8 optional features

Wake-word qualification, the selected local MCP note adapter and explicit cloud
transfer review are documented in [the integration guide](evaluation/integrations/README.md).
They default off. See [verification results](evaluation/integrations/results-2026-10-17.md)
for passed checks and the remaining real-audio/live-provider qualification work.
