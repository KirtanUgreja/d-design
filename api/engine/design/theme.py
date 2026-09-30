"""Themes: the only source of visual truth (docs/v4/design-engine.md).

Phase 22 ships three hand-specified themes. Phase 23 replaces the constants
with a sampler; the ``Theme`` shape and ``css()`` stay. No model call here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Face:
    family: str  # the CSS family name
    folder: str  # under library/fonts
    weights: tuple[int, ...]


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
        lines += [
            f"--margin:{self.margin}px;",
            f"--gutter:{self.gutter}px;",
            f"--radius:{self.radius}px;",
            f"--rule:{self.rule}px;",
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
            f"--rule ({self.rule}px) is the line weight. --shadow-hard is a hard offset shadow."
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
    ),
    "nightshift": Theme(
        id="nightshift",
        summary=(
            "A poster at night. Near-black ground, bone text, one signal yellow used in solid "
            "blocks. Tall condensed display type at enormous sizes, cropped and stacked; mono "
            "labels; flat colour fields and hard edges, never glow."
        ),
        colors={
            "ground": "#0f1317",
            "surface": "#1c232a",
            "ink": "#eeefe8",
            "ink-2": "#a3a89f",
            "accent": "#e9c53f",
            "on-accent": "#15140f",
            "rule": "#eeefe8",
        },
        display=Face("Anton", "anton", (400,)),
        text=Face("Hanken Grotesk", "hanken-grotesk", (400, 600)),
        label=_PLEX_MONO,
        w_display=400,
        w_bold=600,
    ),
}
