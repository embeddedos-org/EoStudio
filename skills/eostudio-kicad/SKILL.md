---
name: eostudio-kicad
description: Read KiCad schematics as data — inventory components, nets, and hierarchy from .kicad_sch files without opening the GUI. Use when an agent needs to answer questions about a board's schematic, check a BOM against the design, or feed schematic structure into another tool.
---

# EoStudio KiCad Schematic Reader

Agent-driven access to KiCad schematics via `kicad-sch-api`
(the CAD surface of the Agent fabric). Schematics are S-expressions;
this skill treats them as queryable data.

## Quick start

```bash
# Inventory every component in a schematic
python3 scripts/sch_inventory.py board/main.kicad_sch

# JSON output for piping into other tools
python3 scripts/sch_inventory.py board/main.kicad_sch --json
```

## What it answers

- **Component inventory** — reference, value, footprint, datasheet link
  per symbol (`scripts/sch_inventory.py`).
- **Net listing** — which nets exist and which pins attach to them
  (see `references/kicad-sch-api.md` for the query pattern).
- **Hierarchy** — sheet structure for multi-sheet designs.

## Discipline

1. **Read-only.** This skill never writes `.kicad_sch` files. Schematic
   edits go through KiCad or a reviewed change; an agent rewriting
   S-expressions by hand is how boards get silently broken.
2. **Pin the API.** `kicad-sch-api` is pinned in `references/`; upgrades
   are reviewed changes.
3. **Validate before trusting.** The script exits non-zero on unparsable
   input; a schematic that fails to parse is reported, not guessed at.

## KiCon Asia tie-in

This skill is the demoable artifact for the agent-driven CAD talk
proposal (KiCon Asia, Nov 5-7): an agent reading a real board schematic,
answering design questions, and checking the BOM -- live, without the
KiCad GUI.
