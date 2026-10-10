"""Visual languages: the authored systems a deck is drawn in
(docs/v4/plan/39-design-reset.md -> Make, 1).

A language is a whole system, not a palette: the type kinds it allows, its
grids, edges, grounds, texture and shape policy, how much imagery it carries
and in what style, and the brief the compose prompt reads. They are written by
hand in ``library/languages/<id>.json``; a model asked to invent a style made
noise (the 2026-10-08 wall).

Pure: reads the library once; the caller passes usage counts in.
"""

from __future__ import annotations

import functools
import random
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from engine.design.axes import EDGES, GRIDS, PAIRINGS, Pairing

LIBRARY = Path(__file__).resolve().parent.parent.parent / "library" / "languages"
PRIOR_HIT = 2.0  # a matching tone or deck type doubles a language's weight


class Imagery(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    appetite: float = Field(ge=0, le=1)  # the share of slides with an image
    styles: tuple[str, ...] = Field(min_length=1)


class Language(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(pattern="^[a-z]+$")
    name: str
    idea: str  # one line, for the style card
    brief: str  # the system, for the compose prompt
    never: tuple[str, ...]
    kinds: tuple[str, ...]  # pairing kinds allowed
    pairings: tuple[str, ...] = ()  # and these pairings by id
    grids: tuple[str, ...] = Field(min_length=1)
    edges: tuple[str, ...] = Field(min_length=1)
    dark: float = Field(ge=0, le=1)  # the chance of a dark ground
    split: float = Field(ge=0, le=1)  # the chance of a second hue for the accent
    density: tuple[str, ...] = Field(min_length=1)
    ratio: tuple[float, float]  # the display ratio range: how loud the type is
    texture: Literal["never", "rare", "often"]
    shapes: bool  # may use dd-shape
    image: Imagery
    tones: tuple[str, ...] = ()
    deck_types: tuple[str, ...] = ()
    # Drawn for new decks only when on (owner, 2026-10-10: only the looks he
    # rated well, Studio, Frame, Bright and Soft); old decks keep theirs.
    active: bool = True
    # Its surface (owner, 2026-10-09: textured references, but "I don't want
    # every deck to look the same"): the finishes a deck in it may draw, and
    # whether it may carry one soft glow. Most languages stay crisp and flat.
    finishes: tuple[Literal["none", "fine", "film"], ...] = ("none",)
    glow: bool = False

    def allows(self, pairing: Pairing) -> bool:
        return pairing.kind in self.kinds or pairing.id in self.pairings

    @property
    def allowed_pairings(self) -> tuple[Pairing, ...]:
        return tuple(p for p in PAIRINGS if self.allows(p))

    def prompt(self) -> str:
        """The language as the compose model reads it."""
        return f"Visual language: {self.name}. {self.brief} Never: {'; '.join(self.never)}."


@functools.cache
def all_languages() -> tuple[Language, ...]:
    out = tuple(Language.model_validate_json(p.read_text()) for p in sorted(LIBRARY.glob("*.json")))
    grids = {g.id for g in GRIDS}
    for lang in out:
        # A bad manifest is a bug in the library, caught by the tests at load.
        known = set(lang.grids) <= grids and set(lang.edges) <= set(EDGES)
        if not lang.allowed_pairings or not known:
            raise ValueError(f"language {lang.id}: unknown pairing, grid or edge")
    return out


def get(language_id: str) -> Language:
    return next(lang for lang in all_languages() if lang.id == language_id)


def choose(
    rng: random.Random,
    *,
    tone: str = "confident",
    deck_type: str = "auto",
    usage: Mapping[str, int] | None = None,
    exclude: frozenset[str] = frozenset(),
) -> Language:
    """The deck's language: balanced by how often each has been used, with a
    light prior from the tone and the deck type. ``exclude`` skips languages
    (Another style draws a different one)."""
    live = [lang for lang in all_languages() if lang.active]
    pool = [lang for lang in live if lang.id not in exclude] or live
    used = usage or {}
    weights = [
        (PRIOR_HIT if tone in lang.tones else 1.0)
        * (PRIOR_HIT if deck_type in lang.deck_types else 1.0)
        / (1 + used.get(lang.id, 0))
        for lang in pool
    ]
    return rng.choices(pool, weights=weights)[0]
