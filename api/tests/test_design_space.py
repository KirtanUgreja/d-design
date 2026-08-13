"""Phase 00 — foundations tests.

The design-space skeleton must be a *space*: at least 10 clearly distinct
families, and an archetype catalogue that supports distributed layouts. These
assert the structural floor the human eye then judges.
"""

from __future__ import annotations

from schema.archetypes import LAYOUT_ARCHETYPES, archetype_by_id
from schema.design_families import DESIGN_FAMILIES, family_by_id


def test_registry_has_at_least_ten_families() -> None:
    assert len(DESIGN_FAMILIES) >= 10


def test_family_ids_are_unique() -> None:
    ids = [f.id for f in DESIGN_FAMILIES]
    assert len(ids) == len(set(ids))


def test_each_family_names_six_axes() -> None:
    for family in DESIGN_FAMILIES:
        assert len(family.axis) == 6, family.id


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
