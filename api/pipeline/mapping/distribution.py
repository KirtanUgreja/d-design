"""The layout-distribution check (v2).

This is the within-deck variety assertion, now measured on *generated layout
structures* rather than catalogue archetypes (phase 10). A layout signature is
the derived shape of a slide — its region roles and spans, in reading order —
and the check makes variety measurable on that space: no identical signature
more than twice in a row, and across a 10+ slide deck, at least half the
distinct signatures available are used.

A deck that collapses onto one frame is the exact failure mode this product
exists to prevent (findings.md measured 53% identical). The check runs on
every mapped Deck, before slides are built.
"""

from __future__ import annotations

from schema.deck import Deck

# The most times a single layout signature may appear consecutively. Two is the
# ceiling: three in a row reads as a repeated frame.
MAX_CONSECUTIVE = 2


def layout_signature(layout: object) -> str:
    """A stable, deterministic signature of one slide's layout structure.

    The region roles and spans in reading order, e.g. "headline:full,body:half,
    media:half". Emphasis is deliberately excluded — two slides with the same
    skeleton but different emphasis are different *renders*, not different
    frames, and the distribution claim is about the frame.
    """
    from schema.deck import LayoutStructure

    if not isinstance(layout, LayoutStructure):
        raise TypeError(f"expected LayoutStructure, got {type(layout).__name__}")
    return ",".join(f"{r.role}:{r.span}" for r in layout.regions)


def layout_sequence(deck: Deck) -> list[str]:
    return [layout_signature(slide.layout) for slide in deck.slides]


def distribution_violation(deck: Deck) -> str | None:
    """Return a human-readable violation, or None if the distribution holds.

    Two rules:
    - No layout signature appears more than MAX_CONSECUTIVE times in a row.
    - A deck with 10+ slides uses at least 5 distinct signatures.
    """
    seq = layout_sequence(deck)

    run = 1
    for i in range(1, len(seq)):
        if seq[i] == seq[i - 1]:
            run += 1
            if run > MAX_CONSECUTIVE:
                return f"layout '{seq[i]}' appears {run} times in a row"
        else:
            run = 1

    distinct = len(set(seq))
    if len(seq) >= 10 and distinct < 5:
        return f"deck uses only {distinct} distinct layouts for {len(seq)} slides"

    return None
