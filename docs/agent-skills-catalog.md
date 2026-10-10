# Agent Skills catalog (org-wide)

How EmbeddedOS skills are written, validated, and shared — the org-wide
Agent Skills catalog in the open Agent-Skills pattern (Claude "Ross"
pattern, now also a first-party Google format: Gemini Workspace rollout
Oct 5, Gemini app Oct 13). Every repo grows a `skills/` directory; this
document is the format contract. Reference implementation:
[`skills/eostudio-kicad/`](../skills/eostudio-kicad/) — the org's first skill.

## Why skills, not docs

Documentation tells an agent what is true. A skill tells an agent what to
*do*: a named capability with a trigger description, scripts that perform
it, and references that explain the domain. The catalog is the
distribution unit for agent capability — China Telecom's TeleAgent hit 1.5M
users / 50k skills in October 2026; enterprises are now buying
third-party security-agent catalogs. The org's Agent fabric (one MCP
gateway, skills catalog, knowledge base) treats skills as first-class
artifacts, not README appendices.

## Directory layout

```text
skills/<skill-name>/
  SKILL.md            # required: frontmatter + capability doc
  scripts/            # required if the skill acts: the tools it drives
  references/         # domain knowledge the scripts assume
```

## SKILL.md contract

Frontmatter (YAML):

```yaml
---
name: <skill-name>          # kebab-case, unique org-wide
description: <trigger>      # when to use this skill — the routing text
---
```

The `description` is the routing surface: it is what a gateway or agent
reads to decide *this* skill answers the task. Write it as "Use when..."
— concrete triggers, not marketing. (`eostudio-kicad`: "Read KiCad
schematics as data — inventory components, nets, and hierarchy from
`.kicad_sch` files without opening the GUI. Use when an agent needs to
answer questions about a board's schematic, check a BOM against the
design, or feed schematic structure into another tool.")

Body sections (follow the reference):

1. **What it answers** — the capability list, each mapped to the script
   or reference that implements it.
2. **Quick start** — copy-paste invocations with real arguments.
3. **Discipline** — the non-negotiable rules (read-only vs read-write,
   pinned dependencies, validate-before-trusting). An agent will follow
   the discipline section as policy; write it like policy.

## Rules

1. **One skill, one capability.** A skill that does three things is three
   skills. The description must stay routable.
2. **Scripts are the skill.** A SKILL.md with no scripts (and no
   references) is a doc page, not a skill — put it in `docs/`.
3. **Pin everything.** External APIs/CLIs the scripts call are pinned in
   `references/`; upgrades are reviewed changes, not drive-bys.
4. **Fail closed.** Scripts exit non-zero on unparsable input and report
   instead of guessing (the `eostudio-kicad` sch_inventory contract).
5. **Nightly CI validates frontmatter** (name/description present, name
   unique org-wide) and executes the scripts' `--help` / dry-run paths.
6. **Every new docs page updates the repo's `llms.txt`** — the light
   knowledge-base layer indexes the catalog.

## Naming

`<repo>-<capability>`: `eostudio-kicad`, `eosim-simulate`,
`eosim-board-port`. The repo prefix keeps the org-wide namespace
collision-free as the catalog grows toward the gateway's SKILLS tab.
