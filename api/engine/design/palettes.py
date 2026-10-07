"""A deck's colours, generated from one continuous palette space
(docs/v4/plan/36-independent-design.md -> Make, 7). There are no named
strategies to run out of: ground lightness and tint, ink tint, the accent's
hue split, lightness and chroma are all drawn per deck.

`resolve()` then forces every pair a slide may use to its contrast target by
moving lightness only, so a generated palette cannot fail contrast: the
guarantee is in construction, and `tests/test_design.py` checks it over 1,000
seeds. Chroma is capped on grounds and large fields: no neon, no glow.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from engine.design import dataviz
from engine.design.color import Need, Oklch, clamp, fit, from_hex

# What each pair must reach. "Text" pairs carry body copy; "large" is the
# accent used as text at 64px and up, or as a filled shape.
TEXT = Need(wcag=7.0, apca=75)  # ink on ground: the projector margin (W6)
BODY = Need(wcag=4.5, apca=60)
LARGE = Need(wcag=3.0, apca=45)
GRAPHIC = Need(wcag=3.0, apca=30)

GROUND_CHROMA = 0.035  # the most a ground is ever tinted: more reads as candy
FIELD_CHROMA = 0.16

Roles = dict[str, Oklch]


@dataclass(frozen=True)
class Tilt:
    """What a tone does to the palette space: it leans the draw, never fixes it."""

    dark: float  # chance of a dark ground
    accent_c: tuple[float, float]  # accent chroma range
    tint: float  # most ground chroma
    split: float  # chance the accent moves off the deck's hue (two-colour print)


TILTS: dict[str, Tilt] = {
    "plain": Tilt(dark=0.15, accent_c=(0.09, 0.15), tint=0.02, split=0.15),
    "confident": Tilt(dark=0.3, accent_c=(0.12, 0.17), tint=0.03, split=0.25),
    "warm": Tilt(dark=0.15, accent_c=(0.1, 0.16), tint=GROUND_CHROMA, split=0.3),
    "bold": Tilt(dark=0.5, accent_c=(0.14, 0.19), tint=0.04, split=0.3),
}


def _toward(a: float, b: float, t: float) -> float:
    """The hue t of the way from a to b, the short way round."""
    d = ((b - a + 540) % 360) - 180
    return (a + d * t) % 360


def generate(h: float, rng: random.Random, tone: str = "confident", *, split: bool = True) -> Roles:
    """Colour roles for one deck around hue ``h``, every value continuous."""
    tilt = TILTS.get(tone, TILTS["confident"])
    dark = rng.random() < tilt.dark
    two_colour = split and rng.random() < tilt.split
    # The ground leans anywhere from neutral to the deck's hue.
    ground_h = _toward(rng.uniform(0, 360), h, rng.random())
    ground_c = rng.uniform(0.0, tilt.tint) * (1.6 if two_colour else 1.0)
    ground_l = rng.uniform(0.14, 0.26) if dark else rng.uniform(0.91, 0.99)
    ground = Oklch(ground_l, min(ground_c, GROUND_CHROMA), ground_h)
    lift = rng.uniform(0.04, 0.08)
    surface = ground.with_l(ground_l + lift if dark else ground_l - lift)
    # Ink takes its tint from somewhere between the ground and the accent.
    ink_h = _toward(ground_h, h, rng.random())
    ink_c = rng.uniform(0.0, 0.07)
    ink_l = rng.uniform(0.92, 0.97) if dark else rng.uniform(0.13, 0.26)
    quiet = rng.uniform(0.17, 0.28)
    accent_h = (h + rng.uniform(120, 240)) % 360 if two_colour else h
    accent_l = rng.uniform(0.68, 0.8) if dark else rng.uniform(0.42, 0.62)
    # A light accent at full chroma is pastel neon as a field: dark decks take less.
    accent_c = rng.uniform(*tilt.accent_c) * (0.7 if dark else 1.0)
    return {
        "ground": ground,
        "surface": surface,
        "ink": Oklch(ink_l, ink_c, ink_h),
        "ink-2": Oklch(ink_l - quiet if dark else ink_l + quiet, ink_c * 0.8, ink_h),
        "accent": Oklch(accent_l, accent_c, accent_h),
    }


def describe(roles: Roles) -> str:
    """The palette in a few words, for the look's summary and record."""
    g, a = roles["ground"], roles["accent"]
    ground = "dark" if g.l < 0.5 else "light"
    tint = "neutral" if g.c < 0.012 else "tinted"
    return f"{ground} {tint} ground, accent at {a.h:.0f}°"


def gap(a: Roles, b: Roles) -> float:
    """How different two palettes look, 0 .. about 3."""
    ga, gb = a["ground"], b["ground"]
    hue = abs(a["accent"].h - b["accent"].h) % 360
    return (
        abs(ga.l - gb.l)
        + min(1.0, abs(ga.c - gb.c) * 25)
        + min(hue, 360 - hue) / 180
        + min(1.0, abs(a["ink"].c - b["ink"].c) * 15)
    )


class UnfitError(Exception):
    """No lightness satisfies a pair: a bug in the palette space, never user input."""


def resolve(roles: Roles) -> Roles:
    """Force every pair to its target. Raises UnfitError only if the space is broken."""
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
    """Chart colours: generated from the deck's accent and validated by the
    dataviz checks (design/dataviz.py), in a fixed order, never cycled."""
    ground = roles["ground"]
    return dataviz.series(roles["accent"], ground, ground.l < 0.5, n)


def brand(hex_value: str, roles: Roles) -> Roles:
    """A brand colour becomes the accent: its hue kept, its lightness corrected
    by resolve(). Chroma is capped so a neon brand still reads as print."""
    b = from_hex(hex_value)
    return {**roles, "accent": Oklch(b.l, min(b.c, FIELD_CHROMA + 0.03), b.h)}
