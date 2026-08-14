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

The diversity budget follows the findings.md measurement: typography and
layout carry more visual identity than colour. The registry therefore varies
families most on the type-pairing and layout axes, and least on the color
system — the axis a viewer attributes to a brand rather than to the tool.
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


# 30+ families. Combinatorial: a deck samples one family and the mapping pass
# distributes archetypes within it, so two decks that draw the same family still
# differ in archetype distribution, content, and image placement. The ids are
# the contract between this registry and the renderer's token registry.
#
# Diversity budget: the axes vary by how much identity they carry (findings.md).
# Type pairing and layout character are the most varied; the color system is
# reused across families so that two families differ on the identity-bearing
# axes first, and colour reads as the brand's choice rather than the tool's.
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
    DesignFamily(
        "magazine-tabloid",
        "Magazine Tabloid",
        ("display-serif", "roomy", "paper", "warm-ink", "editorial", "magazine"),
    ),
    DesignFamily(
        "compact-news",
        "Compact News",
        ("sans-tight", "tight", "rule", "cool-neutral", "swiss", "grid"),
    ),
    DesignFamily(
        "french-poster",
        "French Poster",
        ("display-serif", "loud", "offset", "acid", "loud", "poster"),
    ),
    DesignFamily(
        "opera-program",
        "Opera Program",
        ("serif-display", "roomy", "hairline", "noir", "editorial", "print"),
    ),
    DesignFamily(
        "blueprint",
        "Blueprint",
        ("sans-mono", "precise", "plot", "cool-academic", "precise", "lab"),
    ),
    DesignFamily(
        "clinic",
        "Clinic",
        ("sans-mono", "precise", "hairline", "cool-neutral", "precise", "lab"),
    ),
    DesignFamily(
        "market-report",
        "Market Report",
        ("sans-tight", "systematic", "rule", "cool-neutral", "swiss", "grid"),
    ),
    DesignFamily(
        "memoir",
        "Memoir",
        ("serif-display", "roomy", "paper", "warm-ink", "editorial", "literary"),
    ),
    DesignFamily(
        "cassette",
        "Cassette",
        ("sans-wide", "tight", "stencil", "acid", "loud", "poster"),
    ),
    DesignFamily(
        "zine",
        "Zine",
        ("mono-display", "tight", "stencil", "acid", "brutal", "poster"),
    ),
    DesignFamily(
        "monograph",
        "Monograph",
        ("serif-display", "airy", "paper", "warm-ink", "editorial", "print"),
    ),
    DesignFamily(
        "microfilm",
        "Microfilm",
        ("sans-mono", "atmospheric", "grain", "noir", "noir", "cinematic"),
    ),
    DesignFamily(
        "almanac",
        "Almanac",
        ("serif-display", "airy", "paper", "warm-ink", "editorial", "print"),
    ),
    DesignFamily(
        "telegraph",
        "Telegraph",
        ("mono-display", "tight", "plot", "cool-neutral", "swiss", "terminal"),
    ),
    DesignFamily(
        "street-sign",
        "Street Sign",
        ("sans-tight", "tight", "stencil", "vivid", "brutal", "poster"),
    ),
    DesignFamily(
        "blueprint-lab",
        "Blueprint Lab",
        ("sans-mono", "precise", "plot", "cool-academic", "precise", "lab"),
    ),
    DesignFamily(
        "enamel",
        "Enamel",
        ("sans-rounded", "playful", "flat", "vivid", "playful", "colorblock"),
    ),
    DesignFamily(
        "road-atlas",
        "Road Atlas",
        ("sans-tight", "systematic", "rule", "vivid", "swiss", "grid"),
    ),
    DesignFamily(
        "design-system",
        "Design System",
        ("sans-tight", "systematic", "none", "cool-neutral", "swiss", "grid"),
    ),
)


def family_by_id(family_id: str) -> DesignFamily | None:
    for family in DESIGN_FAMILIES:
        if family.id == family_id:
            return family
    return None
