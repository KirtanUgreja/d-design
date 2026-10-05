"""Textures and the deck's mark, generated per look (docs/v4/design-engine.md ->
"Generated, not picked").

Every texture is a colourless SVG mask whose geometry comes from continuous
parameters — dot pitch and size, hatch angle and spacing, grid pitch and
weight — so two decks with the same motif still do not share a texture. The
mark is drawn from the deck's own title: a small generated emblem that exists
for that deck only, the way a generative identity draws each instance from its
rules (MIT Media Lab, 2011).

Pure code, no model. The colour is always a theme token underneath the mask.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from urllib.parse import quote


def _svg(body: str, w: float, h: float | None = None) -> str:
    hh = w if h is None else h
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{w:g}' height='{hh:g}' "
        f"viewBox='0 0 {w:g} {hh:g}'>{body}</svg>"
    )
    return f'url("data:image/svg+xml,{quote(svg)}")'


@dataclass(frozen=True)
class Params:
    """One look's texture geometry. Every field is continuous within a range
    the eye reads as texture, not as noise or as stripes."""

    dot_pitch: float  # 14-34px between halftone dots
    dot_fill: float  # 0.22-0.46 of the pitch is the dot radius
    hatch_angle: float  # 18-72 degrees
    hatch_pitch: float  # 7-18px between hatch lines
    line: float  # 1.5-4.5px stroke for hatch, grid and rules
    grid_pitch: float  # 26-60px grid cells
    dither_level: int  # 3-11 of 16 Bayer cells lit
    weave: float  # 3-6px weave block width
    grain: float  # 0.6-1.1 turbulence frequency

    @staticmethod
    def draw(rng: random.Random) -> Params:
        return Params(
            dot_pitch=round(rng.uniform(14, 34), 1),
            dot_fill=round(rng.uniform(0.22, 0.46), 2),
            hatch_angle=round(rng.uniform(18, 72), 1),
            hatch_pitch=round(rng.uniform(7, 18), 1),
            line=round(rng.uniform(1.5, 4.5), 1),
            grid_pitch=round(rng.uniform(26, 60), 1),
            dither_level=rng.randint(3, 11),
            weave=round(rng.uniform(3, 6), 1),
            grain=round(rng.uniform(0.6, 1.1), 2),
        )


# The look phase 22 shipped with, kept for the three hand-specified themes.
DEFAULT = Params(24, 0.27, 45, 10, 3, 40, 6, 5, 0.9)

_BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


def tiles(p: Params) -> dict[str, str]:
    """kind -> CSS url() of the mask tile."""
    pitch, r = p.dot_pitch, p.dot_pitch * p.dot_fill
    # Angled stripes tile seamlessly only at special angles, so the hatch is
    # one slide-sized mask holding a rotated <pattern>: a texture is never
    # larger than the slide, so it never has to repeat.
    hs = p.hatch_pitch
    hatch = _svg(
        f"<defs><pattern id='h' width='{hs:g}' height='{hs:g}' patternUnits='userSpaceOnUse' "
        f"patternTransform='rotate({p.hatch_angle:g})'><rect width='{hs:g}' "
        f"height='{p.line:g}'/></pattern></defs><rect width='1920' height='1080' fill='url(#h)'/>",
        1920,
        1080,
    )
    cell = 4
    dither = _svg(
        "".join(
            f"<rect x='{x * cell}' y='{y * cell}' width='{cell}' height='{cell}'/>"
            for y, row in enumerate(_BAYER)
            for x, t in enumerate(row)
            if t < p.dither_level
        ),
        cell * 4,
    )
    g = p.grid_pitch
    return {
        "halftone": _svg(f"<circle cx='{pitch / 2:g}' cy='{pitch / 2:g}' r='{r:.2f}'/>", pitch),
        "hatch": hatch,
        "crosshatch": _svg(
            f"<rect width='{hs * 2:g}' height='{p.line:g}'/>"
            f"<rect width='{p.line:g}' height='{hs * 2:g}'/>",
            hs * 2,
        ),
        "grid": _svg(f"<path d='M0 0H{g:g}V{p.line:g}H0ZM0 0V{g:g}H{p.line:g}V0Z'/>", g),
        "dither": dither,
        "weave": _svg(
            f"<rect width='{p.weave:g}' height='8'/>"
            f"<rect x='8' y='8' width='{p.weave:g}' height='8'/>",
            16,
        ),
        "lines": _svg(f"<rect width='{hs * 2:g}' height='{p.line:g}'/>", hs * 2),
        "grain": _svg(
            f"<filter id='g'><feTurbulence type='fractalNoise' baseFrequency='{p.grain:g}' "
            "numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0 0 0 0 0 0 "
            "0 0 0 0 0 0 0 0 -1.6 1.1'/></filter><rect width='64' height='64' filter='url(#g)'/>",
            64,
        ),
    }


def mark(words: str, rng: random.Random) -> str:
    """The deck's signature: an emblem drawn from its own title.

    The title's letters set the geometry, the look's seed picks the grammar
    (rings, bars or a dotted arc), so the same title in two looks differs and
    two titles in one look differ. Square, colourless, used as a mask.
    """
    digest = hashlib.sha256(words.lower().encode()).digest()
    values = [b / 255 for b in digest[:12]]
    grammar = rng.choice(("rings", "bars", "arc"))
    size = 240
    body: list[str] = []
    if grammar == "rings":
        for i, v in enumerate(values[:5]):
            radius: float = 20 + i * 22
            sweep = 0.35 + v * 0.6
            start = values[i + 5] * 2 * math.pi
            end = start + sweep * 2 * math.pi
            x0, y0 = 120 + radius * math.cos(start), 120 + radius * math.sin(start)
            x1, y1 = 120 + radius * math.cos(end), 120 + radius * math.sin(end)
            large = 1 if sweep > 0.5 else 0
            body.append(
                f"<path d='M{x0:.1f} {y0:.1f}A{radius} {radius} 0 {large} 1 {x1:.1f} {y1:.1f}' "
                "fill='none' stroke='#000' stroke-width='12' stroke-linecap='butt'/>"
            )
    elif grammar == "bars":
        width = size / 9
        for i, v in enumerate(values[:8]):
            height = 30 + v * 190
            body.append(
                f"<rect x='{8 + i * (width + 4):.1f}' y='{size - height:.1f}' "
                f"width='{width:.1f}' height='{height:.1f}'/>"
            )
    else:
        for i, v in enumerate(values):
            a = (i / len(values)) * 1.6 * math.pi - 0.3 * math.pi
            radius = 70 + v * 40
            cx, cy = 120 + radius * math.cos(a), 120 + radius * math.sin(a)
            body.append(f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='{8 + v * 14:.1f}'/>")
    return _svg("".join(body), size)
