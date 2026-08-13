"""The layout-archetype catalogue.

An archetype is a named compositional *role* a slide can play. The mapping pass
(phase 03) assigns each slide an archetype; the slide builder (phase 04) writes
the slide's content *for* that archetype; the renderer (phase 06) frames it
using the design family's tokens. Neither the archetype nor anything the model
emits carries a presentational value — a pixel, a hex, a font, a duration.

This is a curated catalogue, not an invented grammar. The model picks from it
by id; it never designs a new layout (that is v2).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LayoutArchetype:
    id: str
    name: str
    intent: str
    variants: tuple[str, ...]


# A 12-slide deck can use 7-8 distinct archetypes from this catalogue. The
# catalogue is deliberately larger than a single deck needs, so two decks
# sampled from the registry differ in which archetypes they draw.
LAYOUT_ARCHETYPES: tuple[LayoutArchetype, ...] = (
    LayoutArchetype(
        "opener",
        "Opener",
        "Claim the topic with a single, unmissable statement.",
        ("centered", "split", "frame"),
    ),
    LayoutArchetype(
        "statement",
        "Statement",
        "One bold assertion, given room to land.",
        ("centered", "left", "right"),
    ),
    LayoutArchetype(
        "section",
        "Section break",
        "Mark a turn in the narrative and reset attention.",
        ("centered", "left", "indexed"),
    ),
    LayoutArchetype(
        "split",
        "Split",
        "Two ideas in tension, given equal weight.",
        ("side-by-side", "stacked", "diagonal"),
    ),
    LayoutArchetype(
        "columns",
        "Columns",
        "A set of peers: options, pillars, comparisons.",
        ("two", "three", "four"),
    ),
    LayoutArchetype(
        "list",
        "List",
        "A sequence of steps or principles, read in order.",
        ("numbered", "stacked", "timeline"),
    ),
    LayoutArchetype(
        "stats",
        "Stats",
        "Numbers as the argument.",
        ("three", "grid", "banner"),
    ),
    LayoutArchetype(
        "quote",
        "Quote",
        "A voice that is not the presenter's.",
        ("centered", "pull", "letterform"),
    ),
    LayoutArchetype(
        "image",
        "Image",
        "One image carrying the meaning, with minimal type.",
        ("full-bleed", "frame", "split"),
    ),
    LayoutArchetype(
        "callout",
        "Callout",
        "One thing the audience must remember.",
        ("banner", "corner", "centered"),
    ),
    LayoutArchetype(
        "quote-image",
        "Quote + image",
        "A voice paired with a visual.",
        ("side-by-side", "overlay", "split"),
    ),
    LayoutArchetype(
        "closer",
        "Closer",
        "Land the deck: the ask, the next step, the final line.",
        ("centered", "split", "full-bleed"),
    ),
)


def archetype_by_id(archetype_id: str) -> LayoutArchetype | None:
    for archetype in LAYOUT_ARCHETYPES:
        if archetype.id == archetype_id:
            return archetype
    return None
