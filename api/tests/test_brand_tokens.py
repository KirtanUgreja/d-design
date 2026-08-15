"""brand_tokens tests — contrast enforcement (phase 17).

The core claim: mapping is separate from extraction, and a brand fact that
cannot reach WCAG AA against its pair is NOT forced — the family's own token
stands. A forced unreadable accent would be a grant that hurts the deck.
"""

from __future__ import annotations

from pipeline.mapping.brand_tokens import (
    BrandFacts,
    contrast_ratio,
    map_brand_to_family,
)


def test_brand_accent_maps_when_contrast_clears() -> None:
    # Near-black accent on white paper clears AA easily.
    tokens = map_brand_to_family("#111111", None, None)
    assert tokens.accent == "#111111"
    assert tokens.paper is None
    assert tokens.ink is None


def test_weak_accent_falls_back_not_forced() -> None:
    # Mid-gray accent on white fails AA; the family's accent stands.
    tokens = map_brand_to_family("#999999", None, None)
    assert tokens.accent is None


def test_accent_against_dark_paper() -> None:
    # On a dark paper, white accent clears AA and maps.
    tokens = map_brand_to_family("#ffffff", None, None, paper=(17, 17, 17))
    assert tokens.accent == "#ffffff"


def test_brand_paper_maps_only_if_ink_stays_readable() -> None:
    # A dark paper would make the default near-black ink unreadable -> falls
    # back (the family's own paper stands).
    tokens = map_brand_to_family(None, "#333333", None)
    assert tokens.paper is None
    # A white paper keeps the default ink readable -> maps.
    tokens2 = map_brand_to_family(None, "#ffffff", None)
    assert tokens2.paper == "#ffffff"
    # A gray that barely misses AA against the default ink -> falls back.
    tokens3 = map_brand_to_family(None, "#777777", None)
    assert tokens3.paper is None


def test_ink_maps_only_if_readable_on_paper() -> None:
    tokens = map_brand_to_family(None, None, "#111111")
    assert tokens.ink == "#111111"
    # Light ink on white paper fails -> falls back.
    tokens2 = map_brand_to_family(None, None, "#eeeeee")
    assert tokens2.ink is None


def test_contrast_ratio_known_values() -> None:
    # WCAG examples: black/white is 21:1.
    assert contrast_ratio((0, 0, 0), (255, 255, 255)) == 21.0


def test_facts_mapping_end_to_end() -> None:
    facts = BrandFacts(accent_hex="#111111", paper_hex="#ffffff", ink_hex="#333333")
    tokens = map_brand_to_family(facts.accent_hex, facts.paper_hex, facts.ink_hex)
    # White paper maps (keeps ink readable), near-black ink maps, accent maps.
    assert tokens.paper == "#ffffff"
    assert tokens.ink == "#333333"
    assert tokens.accent == "#111111"
