"""Palette strategies (docs/v4/design-engine.md -> Registry, "Palette strategy").

Each strategy turns a hue (and the seeded RNG) into colour roles in OKLCH.
`resolve()` then forces every pair a slide may use to its contrast target by
moving lightness only, so a sampled theme cannot fail contrast: the guarantee
is in construction, and `tests/test_design.py` checks it over 1,000 seeds.

Chroma is capped on grounds and large fields: no neon, no glow.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from engine.design.color import Need, Oklch, clamp, fit, from_hex

# What each pair must reach. "Text" pairs carry body copy; "large" is the
# accent used as text at 64px and up, or as a filled shape.
TEXT = Need(wcag=7.0, apca=75)  # ink on ground: the projector margin (W6)
BODY = Need(wcag=4.5, apca=60)
LARGE = Need(wcag=3.0, apca=45)
GRAPHIC = Need(wcag=3.0, apca=30)

GROUND_CHROMA = 0.035
FIELD_CHROMA = 0.16

Roles = dict[str, Oklch]
Strategy = Callable[[float, random.Random], Roles]


def _paper(h: float, rng: random.Random) -> Roles:
    """Ink and one accent on paper."""
    warm = rng.choice((70.0, 85.0, 95.0, 250.0))
    ground = Oklch(rng.uniform(0.95, 0.98), rng.uniform(0.008, 0.02), warm)
    return {
        "ground": ground,
        "surface": ground.with_l(ground.l - 0.05),
        "ink": Oklch(0.2, 0.012, warm),
        "ink-2": Oklch(0.45, 0.012, warm),
        "accent": Oklch(rng.uniform(0.5, 0.58), rng.uniform(0.13, 0.17), h),
    }


def _night(h: float, rng: random.Random) -> Roles:
    """A dark ground and one spot colour."""
    cool = rng.choice((240.0, 260.0, 60.0))
    ground = Oklch(rng.uniform(0.16, 0.21), rng.uniform(0.008, 0.02), cool)
    return {
        "ground": ground,
        "surface": ground.with_l(ground.l + 0.06),
        "ink": Oklch(0.95, 0.01, cool),
        "ink-2": Oklch(0.75, 0.012, cool),
        "accent": Oklch(rng.uniform(0.78, 0.86), rng.uniform(0.12, 0.16), h),
    }


def _duotone(h: float, rng: random.Random) -> Roles:
    """Two inks, like a two-colour print: a tinted ground in one hue, ink in the same."""
    ground = Oklch(rng.uniform(0.92, 0.95), GROUND_CHROMA, h)
    return {
        "ground": ground,
        "surface": ground.with_l(ground.l - 0.06),
        "ink": Oklch(0.25, 0.07, h),
        "ink-2": Oklch(0.42, 0.06, h),
        "accent": Oklch(0.55, 0.14, (h + rng.choice((150.0, 180.0, 210.0))) % 360),
    }


def _blocks(h: float, rng: random.Random) -> Roles:
    """Colour-block fields: the accent is meant to fill large areas."""
    ground = Oklch(rng.uniform(0.94, 0.97), 0.01, rng.choice((80.0, 100.0)))
    return {
        "ground": ground,
        "surface": ground.with_l(ground.l - 0.06),
        "ink": Oklch(0.18, 0.01, ground.h),
        "ink-2": Oklch(0.42, 0.01, ground.h),
        "accent": Oklch(rng.uniform(0.45, 0.6), FIELD_CHROMA, h),
    }


def _tonal(h: float, rng: random.Random) -> Roles:
    """One hue throughout, in steps of lightness."""
    ground = Oklch(rng.uniform(0.93, 0.96), 0.025, h)
    return {
        "ground": ground,
        "surface": ground.with_l(ground.l - 0.07),
        "ink": Oklch(0.22, 0.05, h),
        "ink-2": Oklch(0.43, 0.05, h),
        "accent": Oklch(0.48, 0.11, h),
    }


def _signal(h: float, rng: random.Random) -> Roles:
    """Black and white, and one signal colour."""
    ground = Oklch(rng.choice((0.985, 0.995)), 0.0, 0.0)
    return {
        "ground": ground,
        "surface": Oklch(0.92, 0.0, 0.0),
        "ink": Oklch(0.13, 0.0, 0.0),
        "ink-2": Oklch(0.42, 0.0, 0.0),
        "accent": Oklch(rng.uniform(0.55, 0.62), 0.18, h),
    }


def _deep(h: float, rng: random.Random) -> Roles:
    """A dark tonal ground in the hue, light ink, a lighter accent."""
    ground = Oklch(rng.uniform(0.2, 0.26), 0.04, h)
    return {
        "ground": ground,
        "surface": ground.with_l(ground.l + 0.06),
        "ink": Oklch(0.95, 0.015, h),
        "ink-2": Oklch(0.78, 0.02, h),
        "accent": Oklch(0.8, 0.12, (h + rng.choice((40.0, -40.0, 180.0))) % 360),
    }


STRATEGIES: dict[str, Strategy] = {
    "paper": _paper,
    "night": _night,
    "duotone": _duotone,
    "blocks": _blocks,
    "tonal": _tonal,
    "signal": _signal,
    "deep": _deep,
}
DARK = frozenset({"night", "deep"})
# Hues that read as a deliberate colour, not a default blue.
HUES = (25.0, 40.0, 60.0, 90.0, 130.0, 160.0, 190.0, 230.0, 265.0, 300.0, 340.0)


class UnfitError(Exception):
    """No lightness satisfies a pair: a bug in a strategy, never user input."""


def resolve(roles: Roles) -> Roles:
    """Force every pair to its target. Raises UnfitError only if a strategy is broken."""
    ground, surface = clamp(roles["ground"]), clamp(roles["surface"])

    def need(c: Oklch, grounds: list[Oklch], n: Need) -> Oklch:
        got = fit(c, grounds, n)
        if got is None:
            raise UnfitError(f"{c.css} cannot reach {n} on {[g.css for g in grounds]}")
        return got

    ink = need(roles["ink"], [ground], TEXT)
    ink = need(ink, [ground, surface], BODY)
    ink2 = need(roles["ink-2"], [ground, surface], BODY)
    accent, on_accent = _accent_pair(roles["accent"], ground)
    return {
        "ground": ground,
        "surface": surface,
        "ink": ink,
        "ink-2": ink2,
        "accent": accent,
        "on-accent": on_accent,
        "rule": ink,
    }


def _accent_pair(accent: Oklch, ground: Oklch) -> tuple[Oklch, Oklch]:
    """The accent nearest its own lightness that reads on the ground (LARGE)
    and carries text of its own (BODY), with that text. A mid-lightness
    accent fails both a light and a dark on-accent, so L moves until one fits."""
    accent = clamp(accent)
    for step in range(0, 61):
        for sign in (-1, 1) if step else (1,):
            cand = clamp(accent.with_l(accent.l + sign * step * 0.01))
            if fit(cand, [ground], LARGE) != cand:
                continue
            for text_l in (0.98, 0.16):
                on = fit(Oklch(text_l, 0.01, cand.h), [cand], BODY)
                if on is not None and abs(on.l - text_l) < 0.12:
                    return cand, on
    raise UnfitError(f"no accent near {accent.css} works on {ground.css}")


def series(roles: Roles, n: int = 5) -> list[Oklch]:
    """Chart colours: the accent first, then hues spaced around it, each
    readable as a filled shape on the ground."""
    a = roles["accent"]
    out = [a]
    for i in range(1, n):
        cand = Oklch(a.l, max(a.c, 0.09), (a.h + i * 360 / n) % 360)
        got = fit(cand, [roles["ground"]], GRAPHIC)
        out.append(got if got is not None else roles["ink-2"])
    return out


def brand(hex_value: str, roles: Roles) -> Roles:
    """A brand colour becomes the accent: its hue kept, its lightness corrected
    by resolve(). Chroma is capped so a neon brand still reads as print."""
    b = from_hex(hex_value)
    return {**roles, "accent": Oklch(b.l, min(b.c, FIELD_CHROMA + 0.03), b.h)}
