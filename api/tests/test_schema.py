"""Phase 01/10 — schema tests.

The Deck schema must validate the golden deck, the no-styling backstop must
reject presentational values, and the structural rules that do not survive the
JSON Schema trip must hold in Pydantic: block/region consistency, grammar
legality, and the structural opener. The cross-language round-trip (Pydantic
and generated Zod agree) lives in web/render tests, because it needs the
generated TypeScript.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from schema.deck import (
    ChartBlock,
    ChartSeries,
    Deck,
    LayoutRegion,
    LayoutStructure,
    Slide,
    StatBlock,
    TextBlock,
)
from schema.no_style import assert_no_presentational_values, has_presentational_value
from tests.fixtures import GOLDEN_DECK_JSON, golden_deck


def test_golden_deck_validates() -> None:
    deck = Deck.model_validate(GOLDEN_DECK_JSON)
    assert len(deck.slides) == 5
    assert deck.family_id == "editorial-serif"


def test_golden_deck_carries_no_presentational_values() -> None:
    deck = golden_deck()
    assert_no_presentational_values(deck.model_dump())


def test_presentational_values_are_caught() -> None:
    assert has_presentational_value("the colour is #fff")
    assert has_presentational_value("padding: 12px")
    assert has_presentational_value("fade in 300ms")
    assert has_presentational_value("rgb(0, 0, 0)")
    assert not has_presentational_value("we grew 3.4x in Q3")
    assert not has_presentational_value("a plain sentence, no styling")


def test_backstop_rejects_presentational_value() -> None:
    deck = golden_deck().model_dump()
    slide = deck["slides"][0]
    blocks = slide["blocks"]
    assert isinstance(blocks, list)
    blocks.append({"kind": "text", "style": "body", "content": "margin: 8px"})
    with pytest.raises(ValueError, match="presentational"):
        assert_no_presentational_values(deck)


def test_headline_is_first_and_single() -> None:
    with pytest.raises(ValidationError):
        Slide(
            id="s1",
            title="x",
            layout=LayoutStructure(regions=[LayoutRegion(role="headline", span="full")]),
            blocks=[
                TextBlock(kind="text", style="body", content="first"),
                TextBlock(kind="text", style="headline", content="second"),
            ],
        )


def test_unknown_family_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Deck.model_validate({"family_id": "not-a-family", "slides": []})


def test_duplicate_slide_ids_are_rejected() -> None:
    slides = [
        {
            "id": "s1",
            "title": "a",
            "layout": {"regions": [{"role": "headline", "span": "full"}]},
            "blocks": [{"kind": "text", "style": "headline", "content": "a"}],
        },
        {
            "id": "s1",
            "title": "b",
            "layout": {"regions": [{"role": "headline", "span": "full"}]},
            "blocks": [{"kind": "text", "style": "headline", "content": "b"}],
        },
    ]
    with pytest.raises(ValidationError):
        Deck.model_validate({"family_id": "editorial-serif", "slides": slides})


def test_block_without_a_region_is_rejected() -> None:
    # A chart block with no chart region in the layout must fail the
    # block/region consistency check.
    with pytest.raises(ValidationError, match="no region"):
        Slide(
            id="s1",
            title="x",
            layout=LayoutStructure(regions=[LayoutRegion(role="headline", span="full")]),
            blocks=[
                TextBlock(kind="text", style="headline", content="H"),
                ChartBlock(
                    kind="chart",
                    chart_type="bar",
                    title="Growth",
                    series=[ChartSeries(label="Q1", value=1.0)],
                ),
            ],
        )


def test_unfilled_region_is_rejected() -> None:
    with pytest.raises(ValidationError, match="no block filling it"):
        Slide(
            id="s1",
            title="x",
            layout=LayoutStructure(
                regions=[
                    LayoutRegion(role="headline", span="full"),
                    LayoutRegion(role="body", span="full"),
                ]
            ),
            blocks=[TextBlock(kind="text", style="headline", content="H")],
        )


def test_layout_illegal_in_family_grammar_is_rejected() -> None:
    # editorial-serif is literary: stats is not a legal role. A stats region
    # filled by a stat block passes block/region consistency but must fail the
    # Deck-level grammar legality check.
    with pytest.raises(ValidationError, match="not legal in grammar"):
        Deck(
            family_id="editorial-serif",
            slides=[
                Slide(
                    id="s1",
                    title="x",
                    layout=LayoutStructure(regions=[LayoutRegion(role="stats", span="full")]),
                    blocks=[StatBlock(kind="stat", value="92%", label="recall")],
                )
            ],
        )


def test_layout_legal_in_one_family_and_illegal_in_another() -> None:
    # A stats-led layout is legal in the lab grammar (scientific) but not the
    # literary grammar (editorial-serif).
    slides = [
        {
            "id": "s1",
            "title": "x",
            "layout": {"regions": [{"role": "stats", "span": "full"}]},
            "blocks": [{"kind": "stat", "value": "92%", "label": "recall"}],
        }
    ]
    Deck.model_validate({"family_id": "scientific", "slides": slides})
    with pytest.raises(ValidationError):
        Deck.model_validate({"family_id": "editorial-serif", "slides": slides})


def test_opener_leads_with_a_full_region() -> None:
    # The first slide's first region must be full-span (the structural
    # through-line rule that replaced the opener archetype).
    with pytest.raises(ValidationError, match="full width"):
        Deck(
            family_id="editorial-serif",
            slides=[
                Slide(
                    id="s1",
                    title="x",
                    layout=LayoutStructure(regions=[LayoutRegion(role="headline", span="half")]),
                    blocks=[TextBlock(kind="text", style="headline", content="H")],
                )
            ],
        )
