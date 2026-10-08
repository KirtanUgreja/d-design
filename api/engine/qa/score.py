"""A design score from what QA already measured (docs/v4/plan/39-design-reset.md
-> Make, 7): used to keep the best of N compositions (``--candidates``).

Zero errors is required; among clean slides the score prefers:
- **balance**: the mass of text and shapes not lopsided (centroid near the
  centre, or deliberately on one third);
- **alignment**: few distinct left edges (things hang on shared axes);
- **empty space**: one large quiet field rather than scattered gaps;
- **clutter**: few separate blocks;
- **hero**: one element clearly larger than the rest.

ponytail: weights set by reading, not fitted. The default stays one candidate
until the test-day wall shows this ranker picks what the owner picks.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.qa.metrics import Box, Shape, empty_rect

W, H = 1920, 1080
EDGE_TOLERANCE = 12.0  # px: left edges this close are one axis


@dataclass(frozen=True)
class Score:
    total: float  # 0..1, higher is better; -1 when the slide has errors
    balance: float
    alignment: float
    empty: float
    clutter: float
    hero: float


def _area(b: Box | Shape) -> float:
    return max(0.0, b.r - b.l) * max(0.0, b.b - b.t)


def score(boxes: list[Box], shapes: list[Shape], *, errors: int = 0) -> Score:
    if errors:
        return Score(-1.0, 0, 0, 0, 0, 0)
    parts: list[Box | Shape] = [*boxes, *shapes]
    if not parts:
        return Score(0.0, 0, 0, 0, 0, 0)
    mass = sum(_area(p) for p in parts) or 1.0
    cx = sum((p.l + p.r) / 2 * _area(p) for p in parts) / mass / W
    cy = sum((p.t + p.b) / 2 * _area(p) for p in parts) / mass / H
    # Centred or on a third both read as intended; in between reads as drift.
    off = min(abs(cx - c) for c in (1 / 3, 0.5, 2 / 3)) + min(
        abs(cy - c) for c in (1 / 3, 0.5, 2 / 3)
    )
    balance = max(0.0, 1 - off * 4)

    edges: list[float] = []
    for b in sorted(boxes, key=lambda b: b.l):
        if not edges or b.l - edges[-1] > EDGE_TOLERANCE:
            edges.append(b.l)
    alignment = 1.0 if len(boxes) <= 1 else max(0.0, 1 - (len(edges) - 1) / max(len(boxes), 1))

    share, _, _ = empty_rect([(p.l, p.t, p.r, p.b) for p in parts])
    empty = min(1.0, share / 0.35)  # a third of the slide quiet is plenty

    clutter = max(0.0, 1 - max(0, len(parts) - 4) / 8)

    sizes = sorted((b.size for b in boxes), reverse=True)
    hero = 1.0 if len(sizes) < 2 else min(1.0, (sizes[0] / max(sizes[1], 1) - 1) / 1.5)

    total = 0.25 * balance + 0.25 * alignment + 0.2 * empty + 0.15 * clutter + 0.15 * hero
    return Score(round(total, 4), balance, alignment, empty, clutter, hero)
