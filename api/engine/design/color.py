"""Colour maths for themes: OKLCH, WCAG 2 and APCA (docs/v4/design-engine.md ->
Registry, "Palette strategy"). Pure functions, no dependency.

Palettes are built in OKLCH because lightness there is perceptual: moving L
keeps the hue a person sees. Every ink/ground pair a theme exposes is found by
searching L until both WCAG 2 and APCA pass, so contrast is guaranteed by
construction, not checked after the fact.

APCA is APCA-W3 0.1.9 (2022-07-03), constants from SA98G — the revision v3
pinned (`git show cbfebfa^:web/src/features/art-direction/color.ts`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Oklch:
    l: float  # noqa: E741 - the name of the axis  # 0..1
    c: float  # chroma, 0..~0.37
    h: float  # hue, degrees

    def with_l(self, l: float) -> Oklch:  # noqa: E741
        return Oklch(min(1.0, max(0.0, l)), self.c, self.h)

    @property
    def hex(self) -> str:
        return to_hex(self)

    @property
    def css(self) -> str:
        return f"oklch({self.l:.3f} {self.c:.3f} {self.h:.1f})"


# --- OKLCH <-> sRGB (Björn Ottosson's OKLab) ------------------------------------


def _lab_to_linear(lab_l: float, a: float, b: float) -> tuple[float, float, float]:
    l_ = lab_l + 0.3963377774 * a + 0.2158037573 * b
    m_ = lab_l - 0.1055613458 * a - 0.0638541728 * b
    s_ = lab_l - 0.0894841775 * a - 1.2914855480 * b
    l3, m3, s3 = l_**3, m_**3, s_**3
    return (
        4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3,
        -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3,
        -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3,
    )


def _encode(x: float) -> float:
    return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055


def _decode(x: float) -> float:
    return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4


def _linear(c: Oklch) -> tuple[float, float, float]:
    rad = math.radians(c.h)
    return _lab_to_linear(c.l, c.c * math.cos(rad), c.c * math.sin(rad))


def in_gamut(c: Oklch) -> bool:
    return all(-1e-4 <= v <= 1 + 1e-4 for v in _linear(c))


def clamp(c: Oklch) -> Oklch:
    """Into sRGB by reducing chroma only: hue and lightness are what a person sees."""
    if in_gamut(c):
        return c
    lo, hi = 0.0, c.c
    for _ in range(24):
        mid = (lo + hi) / 2
        if in_gamut(Oklch(c.l, mid, c.h)):
            lo = mid
        else:
            hi = mid
    return Oklch(c.l, lo, c.h)


def rgb(c: Oklch) -> tuple[int, int, int]:
    r, g, b = _linear(clamp(c))
    return tuple(round(min(1.0, max(0.0, _encode(v))) * 255) for v in (r, g, b))  # type: ignore[return-value]


def to_hex(c: Oklch) -> str:
    return "#" + "".join(f"{v:02x}" for v in rgb(c))


def from_hex(value: str) -> Oklch:
    v = value.lstrip("#")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    r, g, b = (_decode(int(v[i : i + 2], 16) / 255) for i in (0, 2, 4))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    lab_l = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return Oklch(lab_l, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360)


# --- WCAG 2 -------------------------------------------------------------------------


def luminance(c: Oklch) -> float:
    r, g, b = (_decode(v / 255) for v in rgb(c))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def wcag(a: Oklch, b: Oklch) -> float:
    x, y = luminance(a), luminance(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


# --- APCA-W3 0.1.9 ------------------------------------------------------------------

_TRC, _RCO, _GCO, _BCO = 2.4, 0.2126729, 0.7151522, 0.072175
_NORM_BG, _NORM_TXT, _REV_TXT, _REV_BG = 0.56, 0.57, 0.62, 0.65
_BLK_THRS, _BLK_CLMP, _SCALE, _LO_OFFSET, _DELTA_Y_MIN, _LO_CLIP = (
    0.022,
    1.414,
    1.14,
    0.027,
    0.0005,
    0.1,
)


def _apca_y(c: Oklch) -> float:
    r, g, b = rgb(c)
    y: float = _RCO * (r / 255) ** _TRC + _GCO * (g / 255) ** _TRC + _BCO * (b / 255) ** _TRC
    return y if y > _BLK_THRS else y + float((_BLK_THRS - y) ** _BLK_CLMP)


def apca(text: Oklch, ground: Oklch) -> float:
    """Lightness contrast Lc, signed: positive is dark on light."""
    t, g = _apca_y(text), _apca_y(ground)
    if abs(g - t) < _DELTA_Y_MIN:
        return 0.0
    if g > t:
        sapc = (g**_NORM_BG - t**_NORM_TXT) * _SCALE
        return 0.0 if sapc < _LO_CLIP else (sapc - _LO_OFFSET) * 100
    sapc = (g**_REV_BG - t**_REV_TXT) * _SCALE
    return 0.0 if sapc > -_LO_CLIP else (sapc + _LO_OFFSET) * 100


@dataclass(frozen=True)
class Need:
    """A contrast requirement for one fg/bg pair."""

    wcag: float
    apca: float  # absolute Lc


def passes(fg: Oklch, bg: Oklch, need: Need) -> bool:
    return wcag(fg, bg) >= need.wcag and abs(apca(fg, bg)) >= need.apca


def fit(fg: Oklch, grounds: list[Oklch], need: Need) -> Oklch | None:
    """The fg closest to its own lightness that meets ``need`` on every ground,
    moving L only. None when no lightness works (the caller picks another fg)."""
    fg = clamp(fg)
    if all(passes(fg, g, need) for g in grounds):
        return fg
    # Outward in 0.01 steps: the first lightness that passes is the nearest.
    for step in range(1, 101):
        for sign in (-1, 1):
            cand = clamp(fg.with_l(fg.l + sign * step * 0.01))
            if all(passes(cand, g, need) for g in grounds):
                return cand
    return None
