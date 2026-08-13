"""The layout-distribution check.

This is the within-deck variety assertion (spec.md -> "Within-deck variety",
plan/03 -> "no repeated frame"). The mapping pass must distribute layout
archetypes; the check makes it measurable: no archetype more than twice in a
row, and across a 10+ slide deck, at least half the distinct archetypes
available are used.

A deck that collapses onto one frame is the exact failure mode this product
exists to prevent (findings.md measured 53% identical). The check runs on
every mapped Deck, before slides are built.
"""

from __future__ import annotations

from schema.deck import Deck

# The most times a single archetype may appear consecutively. Two is the
# ceiling: three in a row reads as a repeated frame.
MAX_CONSECUTIVE = 2


def archetype_sequence(deck: Deck) -> list[str]:
    return [slide.layout_archetype for slide in deck.slides]


def distribution_violation(deck: Deck) -> str | None:
    """Return a human-readable violation, or None if the distribution holds.

    Two rules:
    - No archetype appears more than MAX_CONSECUTIVE times in a row.
    - A deck with 10+ slides uses at least 5 distinct archetypes.
    """
    seq = archetype_sequence(deck)

    run = 1
    for i in range(1, len(seq)):
        if seq[i] == seq[i - 1]:
            run += 1
            if run > MAX_CONSECUTIVE:
                return f"archetype '{seq[i]}' appears {run} times in a row"
        else:
            run = 1

    distinct = len(set(seq))
    if len(seq) >= 10 and distinct < 5:
        return f"deck uses only {distinct} distinct archetypes for {len(seq)} slides"

    return None
