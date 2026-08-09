"""Colour maths for the linter: WCAG 2.2, APCA, and OKLCH.

Three standards because they answer three different questions, and the linter
needs all three to say what it needs to say.

**WCAG 2.2 is the legal floor.** It is what an enterprise accessibility audit
runs and what a procurement checklist cites. You cannot ship below it regardless
of whether it measures the right thing.

**APCA is the quality gate, and it is the only one that can judge
`cinematic-dark` at all.** WCAG 2's ratio is polarity-blind — it scores
light-on-dark and dark-on-light identically when the eye does not perceive them
the same way — which is exactly why dark themes routinely clear 4.5:1 on paper
and read muddy. The flagship art direction is dark by definition, so the
standard everyone reaches for first is the one least able to judge it.

**OKLCH is for the saturation bound** (docs/design/principles.md rule 19): a
loud, light, saturated colour on a near-black ground blooms, and blooming is
what the no-gradient rules exist to prevent by other means.

## Why this is Python and not a call into `web`

`web/src/features/art-direction/color.ts` already has WCAG 2 contrast and is
already correct. This is a second implementation of that one function, which is
a duplication and is worth naming rather than hiding: the linter runs at the
point of save, in `api`, because it is the thing standing between a token value
and a published page — and a validator that has to make a network call to
another process to decide is a validator that fails open when that process is
down. `test_lint.py` pins the two implementations to the same fixtures, which is
the same treatment `seed_from_id` gets for the same reason.
"""

import math

from schema.art_direction import DtcgColorValue

# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------

_CHANNEL_MAX = 255.0


class Rgb:
    """8-bit channels plus alpha, which is what both standards take.

    A plain class rather than a Pydantic model: this is an intermediate in a
    calculation, never a wire shape, and giving it validation would imply it
    crosses a boundary it does not.
    """

    __slots__ = ("a", "b", "g", "r")

    def __init__(self, r: float, g: float, b: float, a: float = 1.0) -> None:
        self.r = r
        self.g = g
        self.b = b
        self.a = a


def to_rgb(value: DtcgColorValue) -> Rgb:
    """A DTCG colour token's value as 8-bit channels.

    `components` is authoritative and `hex` is ignored entirely — the spec says
    the components win, and re-parsing the fallback would make a lossy
    serialization the source of the number every gate below depends on.
    """
    r, g, b = value.components
    return Rgb(r * _CHANNEL_MAX, g * _CHANNEL_MAX, b * _CHANNEL_MAX, value.alpha)


def composite(fg: Rgb, bg: Rgb) -> Rgb:
    """`fg` over `bg`, opaque.

    Both standards below take opaque colours, and half this palette is not:
    `ink-muted` is ink at 62% and `hairline` is ink at 10%. Measuring a
    translucent colour as though it were opaque is how a token that reads as
    grey gets scored as though it were white.
    """
    return Rgb(
        fg.r * fg.a + bg.r * (1 - fg.a),
        fg.g * fg.a + bg.g * (1 - fg.a),
        fg.b * fg.a + bg.b * (1 - fg.a),
        1.0,
    )


# ---------------------------------------------------------------------------
# WCAG 2.2
# ---------------------------------------------------------------------------


def _srgb_to_linear(channel: float) -> float:
    c = channel / _CHANNEL_MAX
    return float(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)


def relative_luminance(color: Rgb) -> float:
    """WCAG relative luminance. Ignores alpha — callers composite first."""
    return (
        0.2126 * _srgb_to_linear(color.r)
        + 0.7152 * _srgb_to_linear(color.g)
        + 0.0722 * _srgb_to_linear(color.b)
    )


def contrast_ratio(fg: Rgb, bg: Rgb) -> float:
    """WCAG 2.2 contrast ratio, compositing `fg` over `bg` first if it carries
    alpha. The same formula `web/src/features/art-direction/color.ts` uses, and
    `test_lint.py` pins the two to the same fixtures."""
    a = relative_luminance(composite(fg, bg) if fg.a < 1 else fg)
    b = relative_luminance(composite(bg, bg) if bg.a < 1 else bg)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# APCA
#
# **APCA-W3 revision 0.1.9 (beta, 2022-07-03), constants from `SA98G`.**
# Pinned deliberately: APCA is a WCAG 3.0 draft and its constants have moved
# between revisions, so "APCA" without a revision is not a specification. If a
# later revision is adopted, the fixtures in `test_lint.py` are what says which
# numbers moved.
#
# Two things about the transfer function surprise people reading this next to
# `relative_luminance` above, and both are deliberate in the spec: APCA uses a
# *simple* 2.4 power curve rather than the piecewise sRGB one, and it soft-clamps
# near-black rather than letting luminance run to zero. The second is why it can
# judge a dark art direction at all — WCAG 2's ratio is dominated by the +0.05
# term down there, which is what makes every near-black ground score the same.
# ---------------------------------------------------------------------------

_MAIN_TRC = 2.4
_RCO, _GCO, _BCO = 0.2126729, 0.7151522, 0.0721750
_NORM_BG, _NORM_TXT = 0.56, 0.57
_REV_TXT, _REV_BG = 0.62, 0.65
_BLK_THRS, _BLK_CLMP = 0.022, 1.414
_SCALE_BOW, _SCALE_WOB = 1.14, 1.14
_LO_BOW_OFFSET, _LO_WOB_OFFSET = 0.027, 0.027
_DELTA_Y_MIN = 0.0005
_LO_CLIP = 0.1


def _apca_y(color: Rgb) -> float:
    return float(
        _RCO * (color.r / _CHANNEL_MAX) ** _MAIN_TRC
        + _GCO * (color.g / _CHANNEL_MAX) ** _MAIN_TRC
        + _BCO * (color.b / _CHANNEL_MAX) ** _MAIN_TRC
    )


def _soft_clamp(y: float) -> float:
    return y if y > _BLK_THRS else y + (_BLK_THRS - y) ** _BLK_CLMP


def apca_lc(text: Rgb, background: Rgb) -> float:
    """Lightness contrast `Lc`, signed by polarity.

    Positive means dark text on a light ground, negative means light text on a
    dark one. The linter compares the absolute value against a threshold,
    because a threshold is about legibility and the sign is about which way
    round the design is — but the sign is preserved here rather than discarded,
    because throwing it away is what makes a polarity-aware metric behave like a
    polarity-blind one.
    """
    text_y = _soft_clamp(_apca_y(composite(text, background) if text.a < 1 else text))
    bg_y = _soft_clamp(
        _apca_y(composite(background, background) if background.a < 1 else background)
    )

    if abs(bg_y - text_y) < _DELTA_Y_MIN:
        return 0.0

    if bg_y > text_y:  # dark text on a light ground
        sapc = (bg_y**_NORM_BG - text_y**_NORM_TXT) * _SCALE_BOW
        output = 0.0 if sapc < _LO_CLIP else sapc - _LO_BOW_OFFSET
    else:  # light text on a dark ground
        sapc = (bg_y**_REV_BG - text_y**_REV_TXT) * _SCALE_WOB
        output = 0.0 if sapc > -_LO_CLIP else sapc + _LO_WOB_OFFSET

    return output * 100.0


# ---------------------------------------------------------------------------
# OKLCH
#
# Björn Ottosson's OKLab, plus the polar form. Used for one bound and no other
# purpose: a colour that is simultaneously loud (`C`), light (`L`) and sitting
# on a near-black ground is one that blooms, and a bloom is what rule 19 forbids
# by a route the no-gradient check cannot see.
#
# Perceptual uniformity is why it is this space and not HSL: HSL's "lightness"
# says a saturated yellow and a saturated blue at L 50% are equally light, which
# is why a bound expressed in HSL either rejects usable blues or admits
# fluorescent yellows.
# ---------------------------------------------------------------------------


class Oklch:
    __slots__ = ("chroma", "hue", "lightness")

    def __init__(self, lightness: float, chroma: float, hue: float) -> None:
        self.lightness = lightness
        self.chroma = chroma
        self.hue = hue


def to_oklch(color: Rgb) -> Oklch:
    r = _srgb_to_linear(color.r)
    g = _srgb_to_linear(color.g)
    b = _srgb_to_linear(color.b)

    long_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    medium = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    short = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    lc = math.cbrt(long_)
    mc = math.cbrt(medium)
    sc = math.cbrt(short)

    lightness = 0.2104542553 * lc + 0.7936177850 * mc - 0.0040720468 * sc
    a = 1.9779984951 * lc - 2.4285922050 * mc + 0.4505937099 * sc
    b_ = 0.0259040371 * lc + 0.7827717662 * mc - 0.8086757660 * sc

    return Oklch(
        lightness=lightness,
        chroma=math.hypot(a, b_),
        hue=math.degrees(math.atan2(b_, a)) % 360.0,
    )
