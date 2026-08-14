"""The design-space fingerprint — the variety metric (plan/08, spec.md bets).

The variety claim must be measurable, not vibes. A fingerprint is a
deterministic signature of a deck's position in the design space: which family,
the per-slide layout structures, and the motion intents. The acceptance run
asserts:

- Two decks sampled from the registry differ in fingerprint beyond a threshold
- Within a deck, layout structures are distributed (no collapse onto one frame)
- No presentational value passes the backstop

Phase 10: the per-slide dimension is the *layout signature* (the generated
region structure), not a catalogue archetype id — the variety gate measures
that generated layouts differ, not just that a catalogue was sampled widely.
This is the "53% identical" measurement from findings.md, made into a gate.
"""

from __future__ import annotations

import hashlib
import json

from pipeline.mapping.distribution import layout_signature
from schema.deck import Deck


def deck_fingerprint(deck: Deck) -> str:
    """A stable, deterministic fingerprint of a deck's design-space position.

    Includes the family, the ordered layout signatures, and the motion
    intents — the dimensions that make two decks visibly different. It does
    NOT include slide copy (two decks on different topics can share a frame,
    which is exactly what we are measuring).
    """
    payload = {
        "family": deck.family_id,
        "layouts": [layout_signature(slide.layout) for slide in deck.slides],
        "motion": [s.motion_intent for s in deck.slides],
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
