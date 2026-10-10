"""The style card: the deck's style named, with its type and colours, and
no model call."""

from __future__ import annotations

from engine.design.sampler import look_for
from engine.design.theme import build
from engine.studio import preview

SWISS = build(look_for("preview-test", words="a pitch", language="swiss"))


def test_the_card_names_the_style() -> None:
    card = preview.card(SWISS)
    assert card.name == "Swiss grid" and card.idea
    assert set(card.colors) == {"ground", "surface", "ink", "accent"}
    assert card.display == SWISS.display.family
