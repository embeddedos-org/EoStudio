# kicad-sch-api reference

`kicad-sch-api` is the read path this skill is built around: a small
Python API over KiCad's `.kicad_sch` S-expression format. This note
records the query patterns the skill relies on, so the pinned behavior
is reviewable without reading the library source.

## Pinned version

`kicad-sch-api` — pin the exact version in the consumer's requirements
before relying on it in CI. Upgrades are reviewed changes (the
S-expression schema drifts between KiCad major versions).

## Query patterns

### Component inventory

Symbols live under `(symbol ...)` nodes. The properties that matter:

| Property | S-expression | Meaning |
|---|---|---|
| Reference | `(property "Reference" "R12" ...)` | Designator; skip values starting with `#` (power symbols) |
| Value | `(property "Value" "10k" ...)` | Component value |
| Footprint | `(property "Footprint" "Resistor_SMD:R_0603_1608Metric" ...)` | Assigned footprint |
| Datasheet | `(property "Datasheet" "https://..." ...)` | Datasheet link |

`scripts/sch_inventory.py` implements this with a minimal S-expression
parser (no dependency) for the read-only inventory case. For heavier
queries (netlisting, hierarchy walks), prefer the real `kicad-sch-api`
over extending the hand parser.

### Nets

Nets are `(net <id> "name")` declarations; pins attach via
`(pin ... (net <id>))` references. To list "which pins are on net X":
resolve the net id, then walk all symbol pins for that id.

### Hierarchy

Multi-sheet designs nest `(sheet ...)` nodes containing
`(sheet_instances ...)` and `(symbol ... (sheetpath ...))`. Sheet paths
disambiguate identical references across sheets.

## KiCad version notes

- KiCad 7/8/9/10 all use the S-expression `.kicad_sch` format; the
  property names above are stable across them.
- KiCad 10.0.7 (current RC, Sept 2026): no schematic format break vs 9.

## When not to use this

- **Writing schematics**: this skill is read-only by design. Round-trip
  S-expression edits lose formatting and risk silent corruption; use
  KiCad or `kicad-sch-api`'s write path with a reviewed diff.
- **Layout (`.kicad_pcb`)**: different format, different skill.
