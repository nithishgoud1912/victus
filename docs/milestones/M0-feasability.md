# M0 — Current feasibility and qualification boundaries

Recorded 19 October 2026 for the V4 implementation continuation. This fills the
previously empty record; it does not invent an earlier feasibility experiment.

The intended machine is Windows 11 on the user's HP Victus with 16 GB RAM,
RTX 4050 laptop GPU with about 6 GB VRAM and an H-series CPU. These are supplied
hardware facts, not measurements performed by this change.

## Architecture retained

- One durable task scheduler, one mutation owner and bounded spawned workers.
- DOM/accessibility and Windows UIA before selective visual reasoning.
- Local deterministic note/checklist/fixture workflows; shared dispatcher,
  exact-action review, strict model proposals and independent verification.
- Local English STT on CPU/int8 and a separately pinned optional reasoning model.
- Reviewed push to talk; wake and cloud remain separately gated and default off.
- Folder packaging and separate account-owned runtime/qualification data.

## Feasible scope and open evidence

Typed workspace notes and protected command intake are implemented. Native
Notepad, fixture research, reviewed speech and local reasoning have implementation
and qualification tooling, with the remaining machine/device evidence listed in
[the V4 handoff](../V4-TESTS-AND-INCOMPLETE.md). No public-web/general desktop
support or release readiness follows from module presence.

The production resource policy retains 2 GiB available RAM and 64 MiB available
mutation disk. Historical low RAM explains blocked attempts, but current resource
readiness must be measured on the target machine. Model fit/latency, actual
Notepad Save transitions, physical audio behavior and fresh-account deployment
cannot be established from this Linux coding environment.

No tests, inference, Windows control, audio session or package build were run for
this implementation increment, as requested. Syntax inspection is documented
separately and does not establish behavior.
