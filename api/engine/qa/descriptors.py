"""A slide's composition as numbers: its "behaviour" in quality-diversity terms
(docs/v4/plan/36-independent-design.md -> Make, 1).

Ten continuous descriptors in 0..1 plus a layout hash, all from geometry that
measure.js already reports. Nothing here reads text or colour, so what it
returns is never customer content: it can be archived across every deck.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from engine.qa.metrics import AREA, Box, H, Rect, Shape, W, empty_rect

NAMES = (
    "mass_x",  # visual-mass centroid, 0 left .. 1 right
    "mass_y",  # 0 top .. 1 bottom
    "spread",  # how far the mass reaches from its centroid
    "empty",  # the largest empty rectangle's share of the slide
    "empty_x",  # where that rectangle sits
    "empty_y",
    "hero",  # largest type size over smallest, on a log scale
    "hero_area",  # the largest text block's share of the slide
    "blocks",  # how many distinct things are on the slide
    "axis",  # 0 a tall column of content .. 1 a wide band of it
    "edge",  # how much of the canvas edge the shapes touch or bleed off
    "field",  # colour fields, images, charts and textures as a share of the slide
)
HASH_X, HASH_Y = 32, 18  # 60px cells
HASH_BITS = HASH_X * HASH_Y


@dataclass(frozen=True)
class Descriptors:
    values: tuple[float, ...]  # in NAMES order
    hash: int  # occupancy map, one bit per 60px cell, text and colour ignored

    def named(self) -> dict[str, float]:
        return dict(zip(NAMES, self.values, strict=True))


def _clamp(v: float) -> float:
    return min(1.0, max(0.0, v))


def _area(r: Rect) -> float:
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def occupancy(rects: list[Rect]) -> int:
    """One bit per cell whose centre lies inside any rect."""
    bits = 0
    for y in range(HASH_Y):
        cy = (y + 0.5) * H / HASH_Y
        for x in range(HASH_X):
            cx = (x + 0.5) * W / HASH_X
            if any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in rects):
                bits |= 1 << (y * HASH_X + x)
    return bits


def _covered(rects: list[Rect]) -> float:
    """Share of the slide covered by the union of rects, at hash resolution."""
    return occupancy(rects).bit_count() / HASH_BITS


def _edge(rects: list[Rect]) -> float:
    """Share of the canvas perimeter that shapes touch (within 4px) or bleed off."""
    touched = 0.0
    for left, top, right, bottom in rects:
        width, height = right - left, bottom - top
        touched += width * ((top <= 4) + (bottom >= H - 4))
        touched += height * ((left <= 4) + (right >= W - 4))
    return _clamp(touched / (2 * (W + H)))


def describe(boxes: list[Box], shapes: list[Shape]) -> Descriptors:
    text: list[Rect] = [(b.l, b.t, b.r, b.b) for b in boxes]
    solid: list[Rect] = [(s.l, s.t, s.r, s.b) for s in shapes]
    everything = text + solid
    weights = [_area(r) for r in everything]
    total = sum(weights) or 1.0
    mx = sum((r[0] + r[2]) / 2 * w for r, w in zip(everything, weights, strict=True)) / total
    my = sum((r[1] + r[3]) / 2 * w for r, w in zip(everything, weights, strict=True)) / total
    spread = math.sqrt(
        sum(
            (((r[0] + r[2]) / 2 - mx) / W) ** 2 + (((r[1] + r[3]) / 2 - my) / H) ** 2
            for r in everything
        )
        / max(len(everything), 1)
    ) / math.sqrt(0.5)
    empty, ex, ey = empty_rect(everything)
    sizes = [b.size for b in boxes] or [1.0]
    hero = math.log(max(sizes) / max(min(sizes), 1.0)) / math.log(16)
    hero_area = max((_area(r) for r in text), default=0.0) / AREA
    if text:
        width = (max(r[2] for r in text) - min(r[0] for r in text)) / W
        height = (max(r[3] for r in text) - min(r[1] for r in text)) / H
    else:
        width = height = 0.0
    values = (
        _clamp(mx / W) if everything else 0.5,
        _clamp(my / H) if everything else 0.5,
        _clamp(spread),
        _clamp(empty),
        _clamp(ex),
        _clamp(ey),
        _clamp(hero),
        _clamp(hero_area * 4),
        _clamp(len(everything) / 12),
        _clamp(0.5 + (width - height) / 2),
        _edge(solid),
        _covered(solid),
    )
    return Descriptors(tuple(round(v, 4) for v in values), occupancy(everything))


def distance(a: Descriptors, b: Descriptors) -> float:
    """0 identical .. 1 as different as two compositions get. Descriptors and
    the occupancy map each see sameness the other misses, so a pair is only as
    far apart as the closer of the two says."""
    euclid = math.dist(a.values, b.values) / math.sqrt(len(NAMES))
    hamming = (a.hash ^ b.hash).bit_count() / HASH_BITS
    return min(euclid * 2, hamming * 2, 1.0)
