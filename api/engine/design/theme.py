"""Themes: the only source of visual truth (docs/v4/design-engine.md).

Phase 22 shipped three hand-specified themes, kept as THEMES. Phase 23 adds
``build()``: sampled axes (design/sampler.py) into a Theme. No model call here.
"""

from __future__ import annotations

import functools
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from engine.design import patterns
from engine.design.axes import DENSITIES
from engine.design.palettes import series

if TYPE_CHECKING:
    from engine.design.sampler import Look


@dataclass(frozen=True)
class Face:
    family: str  # the CSS family name
    folder: str  # under library/fonts
    weights: tuple[int, ...]
    # A variable face: axis -> (min, max), one file (variable.woff2) for all of it.
    axes: tuple[tuple[str, float, float], ...] = ()

    def axis(self, tag: str) -> tuple[float, float] | None:
        return next(((lo, hi) for t, lo, hi in self.axes if t == tag), None)


@dataclass(frozen=True)
class Theme:
    id: str
    summary: str
    colors: dict[str, str]  # role -> hex
    display: Face
    text: Face
    label: Face
    w_display: int
    w_bold: int
    scale: dict[str, int] = field(
        default_factory=lambda: {
            "mega": 320,
            "d1": 208,
            "d2": 144,
            "d3": 104,
            "h1": 80,
            "h2": 60,
            "h3": 44,
            "body": 34,
            "small": 28,
            "label": 22,
        }
    )
    space: tuple[int, ...] = (8, 16, 24, 40, 64, 96, 128, 192)
    margin: int = 112
    gutter: int = 32
    radius: int = 0
    rule: int = 3
    # The display face's cap height plus descender, in em, rounded up: below
    # it a descender meets the capital under it. Measured in Chromium on
    # 2026-10-01. Exposed as --lh-display; QA reports tighter as E3.
    leading: float = 0.9
    cols: int = 12
    textures: tuple[str, ...] = ("halftone", "hatch", "grid", "solid")
    guidance: str = ""  # the grid, motif and pairing notes, for the compose prompt
    look: dict[str, str] = field(default_factory=dict)  # the sampled axes, for the record
    # Generated per look (design/patterns.py): texture geometry and the deck's mark.
    tiles: dict[str, str] = field(default_factory=lambda: patterns.tiles(patterns.DEFAULT))
    mark: str = field(
        default_factory=lambda: patterns.mark("d-design", random.Random(0))  # noqa: S311 - a shape
    )
    track: float = 0.0  # display letter-spacing, em
    # A variable display face's drawn instance: wdth in percent, other axes.
    stretch: float = 100.0
    variation: str = "normal"
    logo: str = ""  # the user's logo as a data: URL (components/logo.py), once per deck
    shapes: dict[str, str] = field(default_factory=dict)  # dd-shape kind -> mask url

    @property
    def faces(self) -> tuple[Face, ...]:
        seen: dict[str, Face] = {}
        for face in (self.display, self.text, self.label):
            seen.setdefault(face.family, face)
        return tuple(seen.values())

    def css(self) -> str:
        """The ``:root`` token block. Custom properties inherit into every
        slide's shadow root, which is how one theme reaches every slide."""
        lines = [f"--c-{role}:{value};" for role, value in self.colors.items()]
        lines += [
            f"--f-display:'{self.display.family}';",
            f"--f-text:'{self.text.family}';",
            f"--f-label:'{self.label.family}';",
            f"--w-display:{self.w_display};",
            "--w-regular:400;",
            f"--w-bold:{self.w_bold};",
        ]
        lines += [f"--t-{step}:{px}px;" for step, px in self.scale.items()]
        lines += [f"--s-{n}:{px}px;" for n, px in enumerate(self.space, start=1)]
        lines += [f"--tile-{kind}:{url};" for kind, url in self.tiles.items()]
        lines += [f"--shape-{kind}:{url};" for kind, url in self.shapes.items()]
        lines += [
            f"--margin:{self.margin}px;",
            f"--gutter:{self.gutter}px;",
            f"--radius:{self.radius}px;",
            f"--rule:{self.rule}px;",
            f"--lh-display:{self.leading};",
            f"--cols:{self.cols};",
            f"--track-display:{self.track:.3f}em;",
            f"--stretch-display:{self.stretch:g}%;",
            f"--fv-display:{self.variation};",
            *([f'--logo:url("{self.logo}");'] if self.logo else []),
            f"--mark:{self.mark};",
            "--shadow-hard:14px 14px 0 var(--c-ink);",
        ]
        return ":root{" + "".join(lines) + "}"

    def describe(self) -> str:
        """The tokens as the compose model reads them."""
        colors = ", ".join(f"--c-{role}" for role in self.colors)
        sizes = ", ".join(f"--t-{step} ({px}px)" for step, px in self.scale.items())
        spaces = ", ".join(f"--s-{n} ({px}px)" for n, px in enumerate(self.space, start=1))
        return (
            f"Look: {self.summary}\n"
            f"Colours (use only these): {colors}. --c-ground is the slide background, "
            "--c-ink the main text, --c-ink-2 quieter text, --c-accent the one loud colour, "
            "--c-on-accent text on accent, --c-surface a second ground, --c-rule lines.\n"
            f"Fonts: --f-display ({self.display.family}, weight var(--w-display)), "
            f"--f-text ({self.text.family}, weights var(--w-regular) and var(--w-bold)), "
            f"--f-label ({self.label.family}, weight var(--w-regular)).\n"
            f"Type sizes (use only these): {sizes}.\n"
            f"Spacing: {spaces}; --margin ({self.margin}px) is the page margin; "
            f"--gutter ({self.gutter}px). --radius is {self.radius}px. "
            f"--rule ({self.rule}px) is the line weight. --shadow-hard is a hard offset shadow.\n"
            f"--lh-display ({self.leading}) is the tightest display line-height; "
            "tighter collides.\n"
            f"--cols ({self.cols}) columns. --track-display ({self.track:.3f}em) is the "
            "display letter-spacing. dd-texture kinds in this look: "
            f'{", ".join(self.textures)}, and "mark" — this deck\'s own emblem, for the '
            "cover and the ask only." + (f"\nThis look: {self.guidance}" if self.guidance else "")
        )


_PLEX_SANS = Face("IBM Plex Sans", "ibm-plex-sans", (400, 600))
_PLEX_MONO = Face("IBM Plex Mono", "ibm-plex-mono", (400, 500))

THEMES: dict[str, Theme] = {
    "ledger": Theme(
        id="ledger",
        summary=(
            "Swiss and exact. Warm paper, black ink, one vermilion. Heavy grotesk display set "
            "tight and large, hairline rules, mono labels, strict left alignment on a grid. "
            "Big empty fields are part of the design."
        ),
        colors={
            "ground": "#f3efe6",
            "surface": "#e6e0d2",
            "ink": "#15140f",
            "ink-2": "#5c584d",
            "accent": "#c9381c",
            "on-accent": "#fff8ee",
            "rule": "#15140f",
        },
        display=Face("Archivo", "archivo", (800, 900)),
        text=_PLEX_SANS,
        label=_PLEX_MONO,
        w_display=900,
        w_bold=600,
    ),
    "broadsheet": Theme(
        id="broadsheet",
        summary=(
            "Editorial, like a well-made magazine. Bright paper, soft black, deep green. A "
            "characterful serif display at dramatic sizes against a quiet grotesk; thin rules, "
            "column structure, asymmetric margins, small caps-like labels."
        ),
        colors={
            "ground": "#fbfaf5",
            "surface": "#efece2",
            "ink": "#1b1b19",
            "ink-2": "#63605a",
            "accent": "#1d4f3b",
            "on-accent": "#f6f3e8",
            "rule": "#1b1b19",
        },
        display=Face("Fraunces", "fraunces", (400, 700)),
        text=Face("Schibsted Grotesk", "schibsted-grotesk", (400, 600)),
        label=Face("Schibsted Grotesk", "schibsted-grotesk", (400, 600)),
        w_display=700,
        w_bold=600,
        rule=2,
        leading=0.97,
    ),
    "nightshift": Theme(
        id="nightshift",
        summary=(
            "A poster at night. Near-black ground, bone text, one signal yellow that carries "
            "the slide's key number or phrase. Tall condensed display type at large sizes, "
            "given air between lines; mono labels; hard edges, never glow."
        ),
        colors={
            "ground": "#0f1317",
            "surface": "#1c232a",
            "ink": "#eeefe8",
            # Fitted 2026-10-05: #a3a89f reached APCA Lc 54 on this ground; 60 is the target.
            "ink-2": "#b3b8af",
            "accent": "#e9c53f",
            "on-accent": "#15140f",
            "rule": "#eeefe8",
        },
        display=Face("Anton", "anton", (400,)),
        text=Face("Hanken Grotesk", "hanken-grotesk", (400, 600)),
        label=_PLEX_MONO,
        w_display=400,
        w_bold=600,
        leading=0.99,
    ),
}


# --- sampled themes -------------------------------------------------------------

_FONTS = Path(__file__).resolve().parent.parent.parent / "library" / "fonts"


class _Metrics(BaseModel):
    leading: float
    width: float


class _FontMeta(BaseModel):
    family: str
    weights: list[int]
    metrics: dict[str, _Metrics]
    axes: dict[str, tuple[float, float]] = {}


@functools.cache
def _meta() -> dict[str, tuple[str, _FontMeta]]:
    """family -> (folder, meta), parsed once from library/fonts/*/meta.json."""
    out: dict[str, tuple[str, _FontMeta]] = {}
    for path in _FONTS.glob("*/meta.json"):
        meta = _FontMeta.model_validate_json(path.read_text())
        out[meta.family] = (path.parent.name, meta)
    return out


def face(family: str) -> Face:
    folder, meta = _meta()[family]
    axes = tuple((t, lo, hi) for t, (lo, hi) in sorted(meta.axes.items()))
    return Face(family, folder, tuple(meta.weights), axes)


def _measured(family: str, weight: float) -> _Metrics:
    """Metrics at any weight: measured ones exactly, a variable face's
    in-between weights interpolated from the two measured either side."""
    metrics = _meta()[family][1].metrics
    if str(round(weight)) in metrics:
        return metrics[str(round(weight))]
    known = sorted(int(k) for k in metrics)
    lo = max((k for k in known if k <= weight), default=known[0])
    hi = min((k for k in known if k >= weight), default=known[-1])
    if lo == hi:
        return metrics[str(lo)]
    t = (weight - lo) / (hi - lo)
    a, b = metrics[str(lo)], metrics[str(hi)]
    return _Metrics(leading=max(a.leading, b.leading), width=a.width + (b.width - a.width) * t)


def display_width(family: str, weight: float, stretch: float = 100.0) -> float:
    """Average advance in em, measured (benchtools/fonts.py). ``stretch`` is a
    wdth axis value in percent; ponytail: advance scales with it linearly —
    measure at the axis ends if a condensed instance overflows."""
    return _measured(family, weight).width * stretch / 100


def _leading(family: str, weight: float) -> float:
    return _measured(family, weight).leading


# A display face's average advance, in em, that the base scale is drawn for
# (Archivo 900 is 0.53). Wider faces are set smaller, so a headline holds about
# as many characters per line in any pairing. Never larger: a narrow face's
# figures are not narrow, and enlarging them pushed numbers into the margin.
_REFERENCE_WIDTH = 0.5
_DISPLAY_STEPS = ("mega", "d1", "d2", "d3", "h1", "h2", "h3")
_FLOOR = {"h1": 56, "h2": 56, "h3": 40}  # QA's headline minimum (E4) stays reachable


def _fit_width(
    scale: dict[str, int], family: str, weight: int, stretch: float = 100.0
) -> dict[str, int]:
    width = display_width(family, weight, stretch)
    k = min(1.0, max(0.6, _REFERENCE_WIDTH / width))
    out = dict(scale)
    for step in _DISPLAY_STEPS:
        out[step] = max(_FLOOR.get(step, 0), round(scale[step] * k / 2) * 2)
    return out


def scale_from(heading_ratio: float, display_ratio: float) -> dict[str, int]:
    """A type scale from two continuous ratios. Headline steps stay within what
    QA allows (56-96px); the display steps carry the look's drama."""
    h3 = max(40, min(52, round(34 * heading_ratio)))
    h2 = max(56, round(h3 * heading_ratio))
    h1 = max(64, min(96, round(h2 * heading_ratio * 1.15)))
    d3 = min(112, round(h1 * display_ratio))  # some layouts set headlines at d3
    d2 = round(d3 * display_ratio)
    d1 = round(d2 * display_ratio)
    mega = min(420, round(d1 * display_ratio))
    return {
        "mega": mega,
        "d1": d1,
        "d2": d2,
        "d3": d3,
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "body": 34,
        "small": 28,
        "label": 22,
    }


def build(look: Look) -> Theme:
    """A generated look into a Theme. Pure and deterministic."""
    pairing = look.pairing
    display, text, label = face(pairing.display), face(pairing.text), face(pairing.label)
    roles = look.roles
    colors = {role: c.hex for role, c in roles.items()}
    colors |= {f"series-{n}": c.hex for n, c in enumerate(series(roles), start=1)}
    k = DENSITIES[look.density]
    grid = look.grid
    motif = look.motif
    weight = round(look.axis("wght", pairing.display_weight))
    stretch = look.axis("wdth", 100.0)
    named = [(t, v) for t, v in look.instance if t.isupper()]
    variation = ",".join(f'"{t}" {v:g}' for t, v in named) or "normal"
    return Theme(
        id=look.id,
        summary=f"{pairing.note}; {look.palette}; {grid.id} grid; texture: {motif.note}.",
        colors=colors,
        display=display,
        text=text,
        label=label,
        w_display=weight,
        w_bold=max(text.weights),
        scale=_fit_width(
            scale_from(look.heading_ratio, look.display_ratio),
            pairing.display,
            weight,
            stretch,
        ),
        space=tuple(round(px * k) for px in (8, 16, 24, 40, 64, 96, 128, 192)),
        # Continuous, and still kept within 96-144px: wider starves the columns,
        # narrower puts large figures into the 64px safe area.
        margin=min(144, max(96, look.margin)),
        gutter=look.gutter,
        radius=look.radius,
        rule=look.rule,
        leading=_leading(pairing.display, weight),
        cols=grid.cols,
        textures=motif.textures,
        guidance=f"{grid.note}. Motif: {motif.note}. Type: {pairing.note}.",
        look=look.record(),
        tiles=patterns.tiles(look.texture)
        | ({"motif": look.motif_tile} if look.motif_tile else {}),
        mark=look.mark or patterns.mark(look.id, random.Random(0)),  # noqa: S311 - a shape
        track=look.track,
        stretch=stretch,
        variation=variation,
        shapes=dict(look.shapes) or patterns.shapes(random.Random(look.id)),  # noqa: S311 - a shape
    )
