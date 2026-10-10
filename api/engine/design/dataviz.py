"""Chart colours, computed and checked, never eyeballed (docs/v4/plan/
37-beautiful-data.md). A port of the dataviz method's validator: each deck's
categorical series must pass the lightness band, the chroma floor, colour-blind
separation under simulated protanopia and deuteranopia (Machado, Oliveira and
Fernandes 2009, severity 1.0), the normal-vision floor, and contrast against
the ground. ΔE is Euclidean distance in OKLab x100, as the method defines it.

``series`` generates the deck's palette and steps it until it passes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise

from engine.design.color import Oklch, from_hex, in_gamut, rgb, to_hex, wcag

BAND = {"light": (0.43, 0.77), "dark": (0.48, 0.67)}  # OKLCH L for marks
CHROMA_FLOOR = 0.10
CVD_TARGET = 8.0  # ΔEx100, adjacent pairs, worst of protan and deutan
NORMAL_FLOOR = 15.0  # ΔEx100, adjacent pairs, unsimulated vision
CONTRAST_MIN = 3.0  # WCAG, a mark against the ground

_MACHADO = {
    "protan": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deutan": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
}

Lab = tuple[float, float, float]


def _lin(c: Oklch) -> tuple[float, float, float]:
    def dec(v: int) -> float:
        x = v / 255
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4

    r, g, b = rgb(c)
    return dec(r), dec(g), dec(b)


def _oklab(r: float, g: float, b: float) -> Lab:
    l_ = math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m_ = math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s_ = math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def _seen(c: Oklch, kind: str | None) -> Lab:
    r, g, b = _lin(c)
    if kind is None:
        return _oklab(r, g, b)
    m = _MACHADO[kind]
    sim = [min(1.0, max(0.0, row[0] * r + row[1] * g + row[2] * b)) for row in m]
    return _oklab(sim[0], sim[1], sim[2])


def delta_e(a: Oklch, b: Oklch, kind: str | None = None) -> float:
    """ΔEx100 in OKLab, as a person with ``kind`` vision sees the pair."""
    return 100 * math.dist(_seen(a, kind), _seen(b, kind))


def cvd(a: Oklch, b: Oklch) -> float:
    return min(delta_e(a, b, "protan"), delta_e(a, b, "deutan"))


@dataclass(frozen=True)
class Check:
    ok: bool
    problems: tuple[str, ...]


def validate(colours: list[Oklch], ground: Oklch, dark: bool) -> Check:
    """The computable checks, on adjacent pairs (bars, stacks, lines). The
    method's checks 1 and 6 (fixed order, documented values) are structural:
    the order is fixed by ``series`` and never cycled."""
    lo, hi = BAND["dark" if dark else "light"]
    problems: list[str] = []
    for c in colours:
        if not lo - 0.005 <= c.l <= hi + 0.005:
            problems.append(f"{to_hex(c)} lightness {c.l:.2f} outside {lo}-{hi}")
        if c.c < CHROMA_FLOOR - 0.005:
            problems.append(f"{to_hex(c)} chroma {c.c:.3f} below {CHROMA_FLOOR}")
        if wcag(c, ground) < CONTRAST_MIN:
            problems.append(f"{to_hex(c)} {wcag(c, ground):.2f}:1 on the ground")
    for a, b in pairwise(colours):
        if cvd(a, b) < CVD_TARGET:
            problems.append(f"{to_hex(a)}/{to_hex(b)} colour-blind ΔE {cvd(a, b):.1f}")
        if delta_e(a, b) < NORMAL_FLOOR:
            problems.append(f"{to_hex(a)}/{to_hex(b)} ΔE {delta_e(a, b):.1f}")
    return Check(not problems, tuple(problems))


def _candidates(ground: Oklch, dark: bool) -> list[Oklch]:
    """Every in-gamut mark colour the method allows on this ground: hues every
    10°, lightness through the band, chroma at or above the floor."""
    lo, hi = BAND["dark" if dark else "light"]
    out: list[Oklch] = []
    steps = 9
    for hue in range(0, 360, 10):
        for i in range(steps):
            lightness = lo + (hi - lo) * i / (steps - 1)
            for chroma in (0.17, 0.14, 0.11):
                c = Oklch(lightness, chroma, float(hue))
                if in_gamut(c) and wcag(c, ground) >= CONTRAST_MIN:
                    out.append(c)
                    break
    return out


# Where each slot's hue sits relative to the accent: far from its neighbour,
# and a set that reads as planned rather than random (a split around the
# accent, then the gaps).
OFFSETS = (0.0, 180.0, 60.0, 240.0, 120.0, 300.0)


def _hue_gap(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def series(first: Oklch, ground: Oklch, dark: bool, n: int = 5) -> list[Oklch]:
    """The deck's categorical series in a fixed order, never cycled. Slot 1
    is the allowed colour nearest the deck's accent; each next slot is the
    allowed colour nearest its planned hue that stays legal against the slots
    before it. Fewer series rather than a muddled one: it stops when nothing
    is legal. validate() passes by construction, and a test checks it."""
    pool = _candidates(ground, dark)
    if not pool:
        return []
    out = [min(pool, key=lambda c: _hue_gap(c.h, first.h) / 60 + abs(c.l - first.l) * 4)]
    for offset in OFFSETS[1:n]:
        want = (first.h + offset) % 360
        prev = out[-1]
        legal = [
            c
            for c in pool
            if delta_e(c, prev) >= NORMAL_FLOOR
            and cvd(c, prev) >= CVD_TARGET
            and all(delta_e(c, o) >= NORMAL_FLOOR for o in out)
        ]
        if not legal:
            break
        out.append(min(legal, key=lambda c: _hue_gap(c.h, want) / 60 + abs(c.l - out[0].l) * 2))
    return out


def hexes(colours: list[Oklch]) -> list[str]:
    return [to_hex(c) for c in colours]


def parse(values: list[str]) -> list[Oklch]:
    return [from_hex(v) for v in values]
