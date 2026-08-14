"""Phase 00/09 — foundations and design-engine tests.

The design-space must be a *space*: at least 30 clearly distinct families, an
archetype catalogue that supports distributed layouts, and a diversity budget
that follows the findings.md measurement — families differ most on the
identity-bearing axes (type pairing, layout character) and least on colour.
These assert the structural floor the human eye then judges.
"""

from __future__ import annotations

from schema.archetypes import LAYOUT_ARCHETYPES, archetype_by_id
from schema.design_families import DESIGN_FAMILIES, family_by_id

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


def test_archetype_catalogue_is_larger_than_one_deck_needs() -> None:
    # A 12-slide deck uses 7-8 archetypes; the catalogue must be bigger than
    # that, or decks collapse onto the same frames.
    assert len(LAYOUT_ARCHETYPES) >= 10


def test_archetype_ids_are_unique() -> None:
    ids = [a.id for a in LAYOUT_ARCHETYPES]
    assert len(ids) == len(set(ids))


def test_lookup_helpers() -> None:
    assert family_by_id("swiss-grid") is not None
    assert family_by_id("does-not-exist") is None
    assert archetype_by_id("stats") is not None
    assert archetype_by_id("does-not-exist") is None
