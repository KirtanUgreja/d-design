"""The design axes (docs/v4/design-engine.md -> Registry). Data only: the
sampler picks a value per axis and theme.py turns the picks into a Theme.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pairing:
    id: str
    kind: str  # condensed · grotesk · wide · serif · didone · slab · mono — for distance
    display: str  # family
    display_weight: int
    text: str
    label: str
    note: str  # how to use it, for the compose prompt


PAIRINGS: tuple[Pairing, ...] = (
    Pairing(
        "anton-hanken",
        "condensed",
        "Anton",
        400,
        "Hanken Grotesk",
        "IBM Plex Mono",
        "tall condensed poster capitals, cropped and stacked",
    ),
    Pairing(
        "shoulders-public",
        "condensed",
        "Big Shoulders Display",
        900,
        "Public Sans",
        "DM Mono",
        "heavy industrial condensed display, signage energy",
    ),
    Pairing(
        "barlow-work",
        "condensed",
        "Barlow Condensed",
        800,
        "Work Sans",
        "Space Mono",
        "compact condensed headlines that fit long claims",
    ),
    Pairing(
        "league-franklin",
        "condensed",
        "League Gothic",
        400,
        "Libre Franklin",
        "JetBrains Mono",
        "narrow gothic headlines, newspaper-poster",
    ),
    Pairing(
        "archivo-plex",
        "grotesk",
        "Archivo",
        900,
        "IBM Plex Sans",
        "IBM Plex Mono",
        "heavy Swiss grotesk set tight and large",
    ),
    Pairing(
        "bricolage-figtree",
        "grotesk",
        "Bricolage Grotesque",
        800,
        "Figtree",
        "DM Mono",
        "a characterful grotesk with ink traps, warm and direct",
    ),
    Pairing(
        "familjen-karla",
        "grotesk",
        "Familjen Grotesk",
        700,
        "Karla",
        "Space Mono",
        "a quirky grotesk with a hand-cut feel",
    ),
    Pairing(
        "syne-work",
        "wide",
        "Syne",
        700,
        "Work Sans",
        "JetBrains Mono",
        "an extended, art-gallery display face; give it width",
    ),
    Pairing(
        "unbounded-public",
        "wide",
        "Unbounded",
        800,
        "Public Sans",
        "DM Mono",
        "a round, wide display; few words per line",
    ),
    Pairing(
        "fraunces-schibsted",
        "serif",
        "Fraunces",
        700,
        "Schibsted Grotesk",
        "Schibsted Grotesk",
        "a soft, characterful serif against a quiet grotesk",
    ),
    Pairing(
        "bodoni-franklin",
        "didone",
        "Bodoni Moda",
        800,
        "Libre Franklin",
        "Libre Franklin",
        "a high-contrast didone at dramatic sizes; fashion editorial",
    ),
    Pairing(
        "bodoni-sourceserif",
        "didone",
        "Bodoni Moda",
        500,
        "Source Serif 4",
        "IBM Plex Mono",
        "a refined didone over a book serif; quiet luxury",
    ),
    Pairing(
        "dmserif-hanken",
        "serif",
        "DM Serif Display",
        400,
        "Hanken Grotesk",
        "DM Mono",
        "a heavy-contrast display serif, magazine cover",
    ),
    Pairing(
        "instrument-figtree",
        "serif",
        "Instrument Serif",
        400,
        "Figtree",
        "JetBrains Mono",
        "a narrow, elegant serif; set it very large",
    ),
    Pairing(
        "young-karla",
        "serif",
        "Young Serif",
        400,
        "Karla",
        "Space Mono",
        "a sturdy old-style serif, friendly and bookish",
    ),
    Pairing(
        "gloock-public",
        "serif",
        "Gloock",
        400,
        "Public Sans",
        "IBM Plex Mono",
        "a sharp, high-contrast serif with a cut edge",
    ),
    Pairing(
        "zilla-work",
        "slab",
        "Zilla Slab",
        700,
        "Work Sans",
        "IBM Plex Mono",
        "a slab serif with a typewriter echo, plain-spoken",
    ),
    Pairing(
        "alfa-franklin",
        "slab",
        "Alfa Slab One",
        400,
        "Libre Franklin",
        "Space Mono",
        "a fat slab, wood-type poster",
    ),
    Pairing(
        "newsreader-public",
        "serif",
        "Newsreader",
        600,
        "Public Sans",
        "DM Mono",
        "a newspaper serif headline over a civic sans",
    ),
    Pairing(
        "archivo-newsreader",
        "grotesk",
        "Archivo",
        800,
        "Newsreader",
        "IBM Plex Mono",
        "a heavy grotesk headline over a reading serif",
    ),
    Pairing(
        "bricolage-literata",
        "grotesk",
        "Bricolage Grotesque",
        800,
        "Literata",
        "DM Mono",
        "a confident grotesk over a literary serif",
    ),
    Pairing(
        "garamond-hanken",
        "serif",
        "EB Garamond",
        600,
        "Hanken Grotesk",
        "JetBrains Mono",
        "a classical book face at display size; restrained",
    ),
    Pairing(
        "spacemono-plex",
        "mono",
        "Space Mono",
        700,
        "IBM Plex Sans",
        "Space Mono",
        "mono-led: technical, terminal, precise",
    ),
    Pairing(
        "jetbrains-sourceserif",
        "mono",
        "JetBrains Mono",
        600,
        "Source Serif 4",
        "JetBrains Mono",
        "a monospaced display over a serif text; the engineer's notebook",
    ),
)


@dataclass(frozen=True)
class Grid:
    id: str
    cols: int
    margin: int
    gutter: int
    note: str


GRIDS: tuple[Grid, ...] = (
    Grid("swiss", 12, 112, 32, "a strict 12-column Swiss grid; flush left, hang everything on it"),
    Grid("asymmetric", 12, 128, 40, "an asymmetric 5/7 split; one narrow and one wide field"),
    Grid("modular", 6, 96, 24, "a modular 6x4 grid of equal cells; content snaps to modules"),
    Grid("editorial", 8, 160, 32, "an editorial column with a wide margin for notes and labels"),
    Grid("poster", 1, 96, 32, "a free poster field; full-bleed, scale and crop carry it"),
)


@dataclass(frozen=True)
class Motif:
    id: str
    textures: tuple[str, ...]  # dd-texture kinds this deck uses
    note: str


MOTIFS: tuple[Motif, ...] = (
    Motif("halftone", ("halftone", "solid"), "halftone dot fields behind or beside type"),
    Motif("dither", ("dither", "solid"), "ordered-dither fields, a printed-screen feel"),
    Motif("hatch", ("hatch", "solid"), "engraved diagonal hatching in blocks"),
    Motif("crosshatch", ("crosshatch", "solid"), "cross-hatched fields, etching-like"),
    Motif("weave", ("weave", "solid"), "a quiet canvas weave in large fields"),
    Motif("grain", ("grain", "solid"), "paper grain fields; the quietest texture"),
    Motif("rules", ("lines", "solid"), "ruled lines: hairlines and thick rules organise the page"),
    Motif("frames", ("lines", "solid"), "framed panels: a thick ruled frame around one element"),
    Motif("numerals", ("grain", "solid"), "oversized numerals (data-deco) as the visual anchor"),
    Motif("grid-paper", ("grid", "solid"), "a drafting grid in fields; plans and measurement"),
)
TEXTURE_KINDS = frozenset(k for m in MOTIFS for k in m.textures) | {"halftone", "hatch", "grid"}

# px for each step of the type scale on the 1920 canvas. The scale axis moves
# the display steps; headline steps (h1-h3) barely move, so claims still fit.
SCALES: dict[str, dict[str, int]] = {
    "modest": {
        "mega": 240,
        "d1": 168,
        "d2": 120,
        "d3": 92,
        "h1": 72,
        "h2": 56,
        "h3": 44,
        "body": 34,
        "small": 28,
        "label": 22,
    },
    "dramatic": {
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
    },
    "extreme": {
        "mega": 400,
        "d1": 256,
        "d2": 176,
        "d3": 112,
        "h1": 80,
        "h2": 60,
        "h3": 44,
        "body": 34,
        "small": 28,
        "label": 22,
    },
}

# edge -> (radius px, rule px, hard shadow)
EDGES: dict[str, tuple[int, int, bool]] = {
    "sharp": (0, 3, False),
    "soft": (14, 2, False),
    "ruled": (0, 5, True),
}

# density -> multiplier on margins and spacing
DENSITIES: dict[str, float] = {"airy": 1.2, "balanced": 1.0, "dense": 0.8}

MOTIONS = ("still", "subtle", "confident")

IMAGE_TREATMENTS = (
    "editorial photo",
    "duotone",
    "halftone photo",
    "flat illustration",
    "cut-paper collage",
    "line drawing",
)
