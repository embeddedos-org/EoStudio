# KiCon Asia 2026 — talk proposal: "Agent-driven KiCad: EoStudio's MCP surface for schematic capture"

Status: **draft for Aswin's review — NOT submitted.** Submission is Aswin's call.
CFP deadline: **Nov 1, 2026** (~3.5 weeks). Conference: Nov 5–7, 2026 (Asia).

## Title candidate

**Agent-driven KiCad: EoStudio's MCP surface for schematic capture**

Aligns with the Agent-fabric plan item: evaluating `kicad-sch-api` as the CAD
surface for MCP-driven hardware design.

## Abstract (150 words)

Schematic capture is still a manual bottleneck: parts placement, net naming,
ERC cleanup, and layout iteration eat the first week of every board. What if
an agent could drive KiCad the way it drives a browser — through a Model
Context Protocol surface? This talk introduces EoStudio's MCP layer for
schematic capture: agents query a board's netlist state, place symbols, route
nets, and run ERC through a typed, versioned tool API, while HeyPCB
multiplayer sessions and Circuit World's design context keep the human in the
loop. We show the schematic API surface, a worked capture session from
blueprint to ERC-clean netlist, and where the agent must stop and ask —
footprint assignment, high-current routing, and anything safety-relevant.
The goal is not autopilot layout but *agent-assisted* capture: the boring
parts automated, the judgment calls yours.

## Outline

1. Why agents need a CAD surface (the MCP pattern, Ross Markdown skills).
2. `kicad-sch-api`: the tool surface — what the agent can see and change.
3. Worked session: capture → ERC → review loop in EoStudio editors.
4. Stop-and-ask boundaries: where human judgment is required.
5. Roadmap: layout assistance, codegen to EoS board descriptors.

## What this talk asks of KiCon

- A 30-minute slot (25 talk + 5 Q&A).
- Interest in the MCP-for-CAD pattern from the KiCad community.
