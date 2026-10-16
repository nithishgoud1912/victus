# VICTUS - A Desktop and browser automation

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
Task and approval dashboard screens remain for later M5 sections.
## M8 optional features

Wake-word qualification, the selected local MCP note adapter and explicit cloud
transfer review are documented in [the integration guide](evaluation/integrations/README.md).
They default off. See [verification results](evaluation/integrations/results-2026-10-17.md)
for passed checks and the remaining real-audio/live-provider qualification work.
