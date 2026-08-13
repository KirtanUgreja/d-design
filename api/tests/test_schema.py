"""Phase 01 — schema tests.

The Deck schema must validate the golden deck, the no-styling backstop must
reject presentational values, and the structural rules that do not survive the
JSON Schema trip must hold in Pydantic. The cross-language round-trip (Pydantic
and generated Zod agree) lives in web/render tests, because it needs the
generated TypeScript.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from schema.deck import Deck, Slide, TextBlock
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
            layout_archetype="opener",
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
            "layout_archetype": "opener",
            "blocks": [{"kind": "text", "style": "headline", "content": "a"}],
        },
        {
            "id": "s1",
            "title": "b",
            "layout_archetype": "opener",
            "blocks": [{"kind": "text", "style": "headline", "content": "b"}],
        },
    ]
    with pytest.raises(ValidationError):
        Deck.model_validate({"family_id": "editorial-serif", "slides": slides})
