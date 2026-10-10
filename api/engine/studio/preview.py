"""The style card at the outline gate: the deck's style named, with its idea,
its type and its colours. No model call. Its slide thumbnails are gone: the
code-built layout drew every style as the same old slide (owner, 2026-10-10).

One generated style, changeable; never a menu (owner, 2026-10-05).
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.design import languages
from engine.design.theme import Theme


@dataclass(frozen=True)
class Card:
    """What the style card shows."""

    language: str
    name: str
    idea: str
    display: str
    text: str
    colors: dict[str, str]
    image_style: str


def card(theme: Theme) -> Card:
    lang = languages.get(theme.language) if theme.language else None
    keep = ("ground", "surface", "ink", "accent")
    return Card(
        language=theme.language,
        name=lang.name if lang else "",
        idea=lang.idea if lang else "",
        display=theme.display.family,
        text=theme.text.family,
        colors={k: v for k, v in theme.colors.items() if k in keep},
        image_style=theme.look.get("image", "") if lang and lang.image.appetite else "",
    )
