"""The design-family registry: data, not code.

A DesignFamily is a tuple of discrete axes — type pairing, layout archetypes,
spacing rhythm, texture, color system, motion vocabulary. The registry is the
single source of visual truth. The model never emits a presentational value:
it picks a family, and the family's tokens (which live in the renderer's
registry, not here) are what style the deck.

This module holds the *identities* — the names and the axis choices that make
each family distinct. The token values that bring them to life are in
web/src/features/design-system/tokens.ts. The two are keyed by the same family
id, and a family with an id in one registry and not the other is a bug the
acceptance run's fingerprint check would surface as a mismatch.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DesignFamily:
    id: str
    name: str
    axis: tuple[str, str, str, str, str, str]
    """Six axes: (type pairing, spacing rhythm, texture, color system, motion
    vocabulary, layout character). Each axis value is a short tag the renderer's
    token registry maps to concrete values."""


# 12 families. Combinatorial: a deck samples one family and the mapping pass
# distributes archetypes within it, so two decks that draw the same family still
# differ in archetype distribution, content, and image placement. The ids are
# the contract between this registry and the renderer's token registry.
DESIGN_FAMILIES: tuple[DesignFamily, ...] = (
    DesignFamily(
        "editorial-serif",
        "Editorial Serif",
        ("serif-display", "roomy", "paper", "warm-ink", "editorial", "literary"),
    ),
    DesignFamily(
        "brutalist-stencil",
        "Brutalist Stencil",
        ("mono-display", "tight", "stencil", "acid", "brutal", "poster"),
    ),
    DesignFamily(
        "swiss-grid",
        "Swiss Grid",
        ("sans-tight", "systematic", "hairline", "cool-neutral", "swiss", "grid"),
    ),
    DesignFamily(
        "neo-noir",
        "Neo Noir",
        ("sans-wide", "atmospheric", "grain", "noir", "noir", "cinematic"),
    ),
    DesignFamily(
        "scientific",
        "Scientific",
        ("sans-mono", "precise", "plot", "cool-academic", "precise", "lab"),
    ),
    DesignFamily(
        "editorial-sans",
        "Editorial Sans",
        ("sans-display", "airy", "texture", "warm-ink", "editorial", "magazine"),
    ),
    DesignFamily(
        "brutalist-poster",
        "Brutalist Poster",
        ("display-serif", "loud", "offset", "acid", "loud", "poster"),
    ),
    DesignFamily(
        "tech-minimal",
        "Tech Minimal",
        ("sans-mono", "tight", "hairline", "cool-academic", "precise", "terminal"),
    ),
    DesignFamily(
        "dark-editorial",
        "Dark Editorial",
        ("serif-display", "roomy", "grain", "noir", "editorial", "literary"),
    ),
    DesignFamily(
        "vivid-flat",
        "Vivid Flat",
        ("sans-rounded", "playful", "flat", "vivid", "playful", "colorblock"),
    ),
    DesignFamily(
        "print-specimen",
        "Print Specimen",
        ("serif-display", "roomy", "paper", "warm-ink", "editorial", "print"),
    ),
    DesignFamily(
        "system-mono",
        "System Mono",
        ("mono-display", "tight", "plot", "cool-neutral", "swiss", "terminal"),
    ),
)


def family_by_id(family_id: str) -> DesignFamily | None:
    for family in DESIGN_FAMILIES:
        if family.id == family_id:
            return family
    return None
