"""The style preview (phase 39 -> Verify): thumbnails of the deck's own words
in its references, with no model call, and a card naming the style."""

from __future__ import annotations

import asyncio
from pathlib import Path

from engine.compose import preview
from tests.test_references import SWISS, _story


def test_previews_render_the_decks_words_without_a_model(tmp_path: Path) -> None:
    story = _story(6)
    names = asyncio.run(preview.render(SWISS, story, tmp_path))
    assert names and names[0] == "preview-1.png"  # the cover always comes first
    assert all((tmp_path / n).stat().st_size > 1000 for n in names)
    assert not (tmp_path / "preview.html").exists()
    picked = preview.chosen(story)
    assert picked[0].intent == "cover" and picked[-1].intent == "ask"


def test_the_card_names_the_style() -> None:
    card = preview.card(SWISS)
    assert card.name == "Swiss grid" and card.idea
    assert set(card.colors) == {"ground", "surface", "ink", "accent"}
    assert card.display == SWISS.display.family
