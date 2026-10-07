"""A deck's art direction: its own visual language, invented per deck
(owner, 2026-10-08: decks that differ only in font and palette are the same
design). One cheap call writes three genuinely different directions and rates
how typical each is; code keeps the least typical. The compose prompt then
follows it instead of a house style.

The direction may only use what the engine can draw: the deck's type and
colours, flat shapes (design/patterns.py), rules, textures, colour fields,
type at any scale, charts. No images or icons until phase 25.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from engine.design.patterns import SHAPES
from engine.design.theme import Theme
from engine.llm.openrouter import ModelError, Seam
from engine.models import Storyline
from lib.result import Err, Result, ok

PROMPT_VERSION = "direction.v1"
ShapeKind = Literal[
    "disc", "ring", "arc", "half", "quarter", "diagonal", "band", "blob", "steps", "plus"
]


class Direction(BaseModel):
    name: str = Field(max_length=60)
    idea: str = Field(max_length=300)  # the visual concept in one or two sentences
    type: str = Field(max_length=300)  # how type behaves: scale, case, alignment, crops
    shapes: list[ShapeKind] = Field(default_factory=list, max_length=3)
    shape_use: str = Field(default="", max_length=300)  # how those shapes appear
    composition: list[str] = Field(min_length=2, max_length=5)
    never: list[str] = Field(min_length=2, max_length=4)
    texture: Literal["never", "rare", "often"] = "rare"
    typicality: float = Field(ge=0, le=1)


class Directions(BaseModel):
    directions: list[Direction] = Field(min_length=3, max_length=3)


SYSTEM = f"""You are the art director of one presentation deck. Invent THREE genuinely
different visual languages for it — three directions a strong studio might pitch — and rate
how typical each one is of presentation design, 0 (never seen) to 1 (every template does this).

Each direction can use ONLY what this engine draws:
- the deck's three type faces, its type sizes and weights (any scale, any case, cropped by the
  slide edge, rotated 90 degrees, set as giant numerals);
- its colours: ground, surface, ink, quiet ink, one accent;
- flat shapes, any size, any position, overlapping, bleeding off the edge: {", ".join(SHAPES)};
- colour fields, rules of any weight, the deck's texture patterns, charts drawn from data.
No photographs, illustrations, icons, gradients, shadows, glow, 3D, transparency.

Make the three truly different from each other and from the default AI deck (a small label,
a short accent line, the headline top-left, thin rules between points, a dot texture in a
corner). That default must not be any of them. Each direction must still let every slide hold
its words legibly at 1920x1080.

For each: name; idea (the concept); type (how type behaves); shapes (0 to 3 kinds from the
list) and shape_use (how they appear across the deck); composition (2 to 5 principles every
slide follows); never (2 to 4 things this deck never does); texture (never, rare or often);
typicality. Answer as JSON matching the schema."""


def _brief(story: Storyline, theme: Theme, title: str) -> str:
    beats = "\n".join(
        f"- {p.intent}: {next((f.text for f in p.fields if f.name == 'headline'), '')}"
        for p in story.slides
    )
    return (
        f"Deck: {title}\nIt argues: {story.governing_thought}\n"
        f"Its look: {theme.summary}\nFonts: display {theme.display.family}, "
        f"text {theme.text.family}, label {theme.label.family}.\nSlides:\n{beats}"
    )


async def direct(
    seam: Seam, story: Storyline, theme: Theme, *, title: str, model: str
) -> Result[Direction, ModelError]:
    """Three directions, the least typical kept."""
    got = await seam.complete_json(
        "direction",
        Directions,
        system=SYSTEM,
        user=_brief(story, theme, title),
        model=model,
        prompt_version=PROMPT_VERSION,
        max_tokens=4000,
    )
    if isinstance(got, Err):
        return got
    return ok(min(got.value.directions, key=lambda d: d.typicality))


def render(d: Direction) -> str:
    """The direction as the compose prompt reads it."""
    lines = [
        f"ART DIRECTION FOR THIS DECK — {d.name}",
        f"Idea: {d.idea}",
        f"Type: {d.type}",
    ]
    if d.shapes:
        lines.append(f"Shapes (<dd-shape kind=…>): {', '.join(d.shapes)}. {d.shape_use}")
    else:
        lines.append("Shapes: none in this deck.")
    lines.append("Every slide follows:")
    lines += [f"- {c}" for c in d.composition]
    lines.append("This deck never: " + "; ".join(d.never))
    lines.append(f"Textures: {d.texture}.")
    lines.append(
        "Follow this direction on every slide, varying the composition slide to slide. It "
        "overrides any habit of your own."
    )
    return "\n".join(lines)
