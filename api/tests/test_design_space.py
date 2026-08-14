"""Phase 00/09/10 — foundations, design-engine and grammar tests.

The design-space must be a *space*: at least 30 clearly distinct families, a
diversity budget that follows the findings.md measurement, and a layout grammar
that every family resolves to — the phase 10 constraint that replaced the
curated catalogue. These assert the structural floor the human eye then judges.
"""

from __future__ import annotations

from schema.design_families import DESIGN_FAMILIES, family_by_id
from schema.grammars import GRAMMARS, REGION_ROLES, REGION_SPANS, grammar_for_family

# The six-axis tuple order in design_families.py.
TYPE_AXIS = 0
COLOR_AXIS = 3
LAYOUT_AXIS = 5


def test_registry_has_at_least_thirty_families() -> None:
    assert len(DESIGN_FAMILIES) >= 30


def test_family_ids_are_unique() -> None:
    ids = [f.id for f in DESIGN_FAMILIES]
    assert len(ids) == len(set(ids))


def test_each_family_names_six_axes() -> None:
    for family in DESIGN_FAMILIES:
        assert len(family.axis) == 6, family.id


def test_diversity_budget_varies_identity_axes_more_than_color() -> None:
    # findings.md: typography and layout carry more identity than colour, so
    # the registry must vary families more on type+layout than on the color
    # system. Measured as distinct values across the registry.
    type_values = {f.axis[TYPE_AXIS] for f in DESIGN_FAMILIES}
    layout_values = {f.axis[LAYOUT_AXIS] for f in DESIGN_FAMILIES}
    color_values = {f.axis[COLOR_AXIS] for f in DESIGN_FAMILIES}
    assert len(type_values) >= len(color_values)
    assert len(layout_values) >= len(color_values)


def test_every_family_resolves_a_grammar() -> None:
    # Phase 10: a family with no grammar is a registry bug — the Deck
    # validator fails closed on it, so the registry must never have one.
    for family in DESIGN_FAMILIES:
        grammar = grammar_for_family(family)
        assert grammar is not None, family.id
        assert grammar.layout_character == family.axis[LAYOUT_AXIS]


def test_grammar_registry_is_nonempty_and_bounded() -> None:
    # ~9 grammars for 31 families: one per layout character, not per family.
    # This is the phase 10 decision — bounded authoring, on-family because each
    # family has exactly one layout character.
    assert len(GRAMMARS) >= 5
    assert len(GRAMMARS) <= 15


def test_each_grammar_is_internally_consistent() -> None:
    for grammar in GRAMMARS:
        assert grammar.roles, grammar.layout_character
        assert grammar.spans, grammar.layout_character
        assert grammar.max_regions >= 1
        # Every role is a real region role and every span a real span.
        assert set(grammar.roles).issubset(set(REGION_ROLES))
        assert set(grammar.spans).issubset(set(REGION_SPANS))
        # Every signature is a non-empty sequence of the grammar's own roles.
        for sig in grammar.signatures:
            assert sig
            assert set(sig).issubset(set(grammar.roles))


def test_lookup_helpers() -> None:
    assert family_by_id("swiss-grid") is not None
    assert family_by_id("does-not-exist") is None
