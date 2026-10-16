# SPDX-License-Identifier: MIT
"""Catalogue invariant tests for BUILTIN_TEMPLATES.

The catalogue in `eostudio/templates/samples.py` is data, and until
now its invariants were enforced by hand — adding the UNO Q template
needed a manual count-assertion bump elsewhere plus a follow-up fix
commit. These tests pin the invariants as data so the next template
addition fails CI informatively instead of shipping a malformed
entry: unique keys matching names, non-empty description /
components / screens, known editor types, difficulty +
estimated_time metadata, and the UNO Q bridge contract (exactly one
crossing, and every call/serve is a method the bridge declares).
No hardcoded template count — a new well-formed template passes.
"""

from __future__ import annotations

from eostudio.templates.samples import BUILTIN_TEMPLATES, get_template, list_templates

# The editor types the catalogue uses today. A new editor type is a
# deliberate addition: extend this set in the same commit that adds
# the template, so the change is reviewed as a catalogue decision.
KNOWN_EDITOR_TYPES = {"ui", "cad", "game", "database", "simulation"}


def test_keys_match_template_names():
    assert BUILTIN_TEMPLATES, "catalogue must not be empty"
    for key, template in BUILTIN_TEMPLATES.items():
        assert key == template.name, f"key {key!r} != template name {template.name!r}"


def test_every_template_is_well_formed():
    for key, template in BUILTIN_TEMPLATES.items():
        assert template.description.strip(), f"{key}: empty description"
        assert template.category.strip(), f"{key}: empty category"
        assert template.components, f"{key}: no components"
        assert isinstance(template.screens, list), f"{key}: screens must be a list"
        if template.editor_type in {"ui", "database"}:
            # Screen-oriented editors ship screens; CAD/game/simulation
            # templates legitimately have none (verified in the catalogue:
            # mechanical-part, game-platformer, simulation-pid all have 0).
            assert template.screens, f"{key}: screen-oriented template with no screens"
        for component in template.components:
            assert component.get("type"), f"{key}: component without a type: {component!r}"
        assert template.editor_type in KNOWN_EDITOR_TYPES, (
            f"{key}: unknown editor_type {template.editor_type!r} "
            f"(known: {sorted(KNOWN_EDITOR_TYPES)}); add it here deliberately"
        )
        assert template.metadata.get("difficulty"), f"{key}: metadata lacks difficulty"
        assert template.metadata.get("estimated_time"), f"{key}: metadata lacks estimated_time"


def test_lookup_helpers_agree_with_catalogue():
    assert {t.name for t in list_templates()} == set(BUILTIN_TEMPLATES)
    for key in BUILTIN_TEMPLATES:
        assert get_template(key) is BUILTIN_TEMPLATES[key]
    assert get_template("no-such-template") is None
    for template in BUILTIN_TEMPLATES.values():
        by_category = list_templates(category=template.category)
        assert template in by_category


def test_to_project_dict_round_trips_identity():
    for key, template in BUILTIN_TEMPLATES.items():
        project = template.to_project_dict()
        assert project["name"] == template.name
        assert project["editor_type"] == template.editor_type
        assert project["components"] == template.components
        assert project["metadata"]["difficulty"] == template.metadata["difficulty"]


def test_uno_q_bridge_contract_is_the_only_crossing():
    template = BUILTIN_TEMPLATES["uno-q-dual-brain"]
    bridges = [c for c in template.components if c.get("type") == "bridge_contract"]
    assert len(bridges) == 1, "exactly one bridge_contract component"
    bridge = bridges[0]
    declared = {f"{bridge['name']}.{m['name']}" for m in bridge["methods"]}
    assert declared, "bridge declares no methods"

    crossings = 0
    for component in template.components:
        if component.get("type") == "bridge_contract":
            continue
        for key in ("calls", "serves"):
            names = component.get(key)
            if names is None:
                continue
            crossings += 1
            assert set(names) <= declared, (
                f"{component.get('name')}: {key} names not declared by the bridge: "
                f"{sorted(set(names) - declared)}"
            )
    assert crossings == 2, "expected exactly the linux_app calls + mcu_sketch serves crossings"
