"""The design-space fingerprint — the variety metric (plan/08, spec.md bets).

The variety claim must be measurable, not vibes. A fingerprint is a
deterministic signature of a deck's position in the design space: which family,
the per-slide layout structures, the motion intents, and the chart types. The
acceptance run asserts:

- Two decks sampled from the registry differ in fingerprint beyond a threshold
- Within a deck, layout structures are distributed (no collapse onto one frame)
- Within a deck, chart types are distributed (no chart-type collapse)
- No presentational value passes the backstop

Phase 10: the per-slide dimension is the *layout signature* (the generated
region structure), not a catalogue archetype id. Phase 11 adds chart-type
distribution so a deck that draws the same chart on every slide is flagged.
This is the "53% identical" measurement from findings.md, made into a gate.
"""

from __future__ import annotations

import hashlib
import json

from pipeline.mapping.distribution import layout_signature
from schema.deck import ChartBlock, Deck


def chart_types(deck: Deck) -> list[str]:
    """The chart type of every slide that carries one, in deck order."""
    out: list[str] = []
    for slide in deck.slides:
        for block in slide.blocks:
            if isinstance(block, ChartBlock):
                out.append(block.chart_type)
    return out


def deck_fingerprint(deck: Deck) -> str:
    """A stable, deterministic fingerprint of a deck's design-space position.

    Includes the family, the ordered layout signatures, the motion intents,
    and the chart types — the dimensions that make two decks visibly
    different. It does NOT include slide copy (two decks on different topics
    can share a frame, which is exactly what we are measuring).
    """
    payload = {
        "family": deck.family_id,
        "layouts": [layout_signature(slide.layout) for slide in deck.slides],
        "motion": [s.motion_intent for s in deck.slides],
        "charts": chart_types(deck),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf8")).hexdigest()


def archetype_distribution(deck: Deck) -> dict[str, int]:
    """Count of each layout signature across the deck."""
    counts: dict[str, int] = {}
    for slide in deck.slides:
        sig = layout_signature(slide.layout)
        counts[sig] = counts.get(sig, 0) + 1
    return counts


def chart_type_ratio(deck: Deck) -> float:
    """The fraction of charts that are NOT the most-common chart type.

    1.0 means every chart differs; 0.0 means the deck drew the same chart
    everywhere. A deck with fewer than two charts trivially passes (there is
    nothing to collapse). This is the within-deck chart-variety measure.
    """
    types = chart_types(deck)
    if len(types) < 2:
        return 1.0
    counts: dict[str, int] = {}
    for t in types:
        counts[t] = counts.get(t, 0) + 1
    most_common = max(counts.values())
    return 1.0 - (most_common / len(types))


def distribution_ratio(deck: Deck) -> float:
    """The fraction of slides that are NOT the most-common layout signature.

    1.0 means every slide has a different layout; 0.0 means the deck collapsed
    onto one frame. This is the within-deck variety measure.
    """
    if not deck.slides:
        return 1.0
    counts = archetype_distribution(deck)
    most_common = max(counts.values())
    return 1.0 - (most_common / len(deck.slides))
