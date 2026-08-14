"""The layout-grammar registry — the v2 constraint on generated layouts.

Phase 10 replaces the curated archetype catalogue (v1) with per-family layout
*generation*: the model composes a LayoutStructure within a family's grammar.
The grammar defines the legal moves — which region roles may appear, which
relative spans, how dense — and the model picks the move and fills the values.
This is the structured-diversity finding from findings.md: sample the discrete
choices structurally, let the model fill continuous values within the region it
was handed.

A family's grammar is keyed by its layout-character axis value (axis[5]): the
same axis phase 09's diversity budget identified as carrying identity. There
are ~9 grammars for 31 families — bounded authoring, still on-family because
each family has exactly one layout character.

ponytail: one grammar per layout character, not per family. If two families
that share a character start producing indistinguishable layouts, split the
character's grammar per-family (the trigger is a fingerprint collision in the
variety gate, phase 15).
"""

from __future__ import annotations

from dataclasses import dataclass

from schema.design_families import DesignFamily, family_by_id

# The region roles the grammar constrains. These are semantic (what a region is
# for), never presentational (no hex, no px, no font) — patterns.md rule 1.
REGION_ROLES: tuple[str, ...] = (
    "headline",
    "body",
    "media",
    "stats",
    "quote",
    "chart",
    "aside",
)

# Relative spans: size *relationships* between regions, not pixels. The renderer
# maps these to grid columns; the model never emits a length.
REGION_SPANS: tuple[str, ...] = (
    "full",
    "two-thirds",
    "half",
    "third",
    "quarter",
)


@dataclass(frozen=True)
class FamilyGrammar:
    """The legal moves for one layout character.

    ``roles`` and ``spans`` are the alphabet the model composes from; a
    generated layout is legal iff every region's role is in ``roles``, span in
    ``spans``, and there are at most ``max_regions`` regions. ``signatures`` are
    canonical role sequences — exemplars the prompt shows so generation starts
    on-family; the model may compose any legal combination, not just these.
    """

    layout_character: str
    roles: tuple[str, ...]
    spans: tuple[str, ...]
    max_regions: int
    signatures: tuple[tuple[str, ...], ...]


# Keyed by DesignFamily.axis[5] (the layout-character axis). A family whose
# layout character has no grammar here is a registry bug — the Deck validator
# fails closed on it (fails, never defaults).
GRAMMARS: tuple[FamilyGrammar, ...] = (
    FamilyGrammar(
        "grid",
        ("headline", "body", "stats", "chart", "media", "aside"),
        ("full", "half", "third"),
        4,
        (
            ("headline", "body"),
            ("headline", "stats", "stats"),
            ("headline", "chart"),
            ("headline", "body", "media"),
        ),
    ),
    FamilyGrammar(
        "magazine",
        ("headline", "body", "media", "quote", "aside"),
        ("full", "two-thirds", "half", "third"),
        4,
        (
            ("headline", "body", "media"),
            ("headline", "quote"),
            ("headline", "media", "body"),
        ),
    ),
    FamilyGrammar(
        "poster",
        ("headline", "body", "media", "stats", "quote", "aside"),
        ("full", "half", "quarter"),
        4,
        (
            ("headline", "body"),
            ("headline", "stats"),
            ("headline", "media"),
        ),
    ),
    FamilyGrammar(
        "print",
        ("headline", "body", "media", "quote", "aside"),
        ("full", "half", "two-thirds", "third"),
        4,
        (
            ("headline", "body"),
            ("headline", "quote"),
            ("headline", "media", "body"),
        ),
    ),
    FamilyGrammar(
        "lab",
        ("headline", "body", "stats", "chart", "media", "aside"),
        ("full", "half", "third", "quarter"),
        5,
        (
            ("headline", "stats"),
            ("headline", "chart"),
            ("headline", "stats", "stats"),
            ("headline", "chart", "body"),
        ),
    ),
    FamilyGrammar(
        "terminal",
        ("headline", "body", "stats", "chart", "aside"),
        ("full", "half", "third"),
        4,
        (
            ("headline", "body"),
            ("headline", "stats"),
            ("headline", "chart"),
        ),
    ),
    FamilyGrammar(
        "cinematic",
        ("headline", "body", "media", "quote", "aside"),
        ("full", "two-thirds", "half"),
        3,
        (
            ("headline", "media"),
            ("headline", "body"),
            ("media", "headline"),
        ),
    ),
    FamilyGrammar(
        "literary",
        ("headline", "body", "quote", "media", "aside"),
        ("full", "two-thirds", "half"),
        4,
        (
            ("headline", "body"),
            ("headline", "quote", "body"),
            ("headline", "body", "quote"),
        ),
    ),
    FamilyGrammar(
        "colorblock",
        ("headline", "body", "stats", "media", "quote"),
        ("full", "half", "third", "quarter"),
        4,
        (
            ("headline", "stats", "stats"),
            ("headline", "media", "body"),
            ("headline", "body"),
        ),
    ),
)


def grammar_for_family(family: DesignFamily) -> FamilyGrammar | None:
    """The grammar for a family, keyed by its layout-character axis."""
    for grammar in GRAMMARS:
        if grammar.layout_character == family.axis[5]:
            return grammar
    return None


def grammar_for_family_id(family_id: str) -> FamilyGrammar | None:
    family = family_by_id(family_id)
    if family is None:
        return None
    return grammar_for_family(family)
