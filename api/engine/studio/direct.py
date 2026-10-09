"""Layer 3a, the art director: one call that sees the whole outline and the
deck's design system, and plans a different composition for every slide, so
the deck has a rhythm instead of one template ten times (live decks,
2026-10-09: the same circle on 8 of 10 slides; three alike in a row).

The plan is advice the designer reads, not a contract: what comes back is
checked only for shape, and a failed call falls back to a plain plan."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from engine.design.theme import Theme
from engine.llm.openrouter import ModelError, Seam
from engine.models import SlidePlan, Storyline
from lib.result import Err, Result, ok

PROMPT_VERSION = "direct.v1"
IMAGE_CAP = 3  # pictures in one deck: where a picture says something, not as filler

Hero = Literal["headline", "number", "chart", "visual", "image", "diagram", "quote", "list"]
Ground = Literal["ground", "accent", "ink", "surface"]

SYSTEM = f"""You are the art director of a studio known for presentations that look designed
by people with taste: editorial, bold, every slide different, never a template (think the best
of Pentagram, Collins and Apple keynotes; never a Gamma or Canva theme). A designer will build
each slide from your plan in HTML, CSS and flat SVG at 1920x1080.

Plan the whole deck at once. For EVERY slide give:
- hero: the one thing the eye lands on first — headline, number, chart (when the slide has one),
  visual (when the slide has one), image, diagram (a flat SVG drawing the designer makes: a
  loop, layers, a funnel, a timeline, a network, a device outline, abstract product art), quote
  or list.
- ground: the slide's main field — ground (the light page), surface, accent (the loud colour)
  or ink (dark).
- image: true only where a picture says something words cannot (a person, a place, a mood),
  never on a number, chart or visual slide; at most {IMAGE_CAP} in the deck.
- idea: two or three sentences a designer can build without asking: where the hero sits and
  how big (in px or columns of 12), what crops or bleeds off an edge, where the headline and
  the rest go, and what makes THIS slide unlike its neighbours.

Rules of the rhythm:
- No two slides in a row share a layout idea, a hero or a ground. At least two slides sit on
  an accent or ink field. The cover and the ask are the two strongest slides.
- Scale contrast is the tool: a hero 4 to 8 times the size of the body text.
- Use the whole canvas: asymmetric grids, bleeds, crops, a giant numeral or word as
  decoration, colour fields that run off the edge. Centre a slide only when it is one bold line.
- Never: cards around points, rows of icons, pills or badges, gradients, shadows, glows,
  everything centred, small text floating in empty space.

concept: one sentence for the deck's visual idea, specific to this product and audience.

Answer as JSON."""


class SlideDirection(BaseModel):
    id: str
    hero: Hero
    ground: Ground
    image: bool
    idea: str


class Direction(BaseModel):
    concept: str
    slides: list[SlideDirection] = Field(default_factory=list)

    def of(self, slide_id: str) -> SlideDirection | None:
        return next((s for s in self.slides if s.id == slide_id), None)


def _outline(story: Storyline) -> str:
    lines = [f"The deck argues: {story.governing_thought}", f"Audience: {story.audience}", ""]
    for n, p in enumerate(story.slides, start=1):
        has = ["chart"] if p.chart else []
        has += [f"visual:{p.visual.kind}"] if p.visual else []
        extra = " — has " + ", ".join(has) if has else ""
        lines.append(f"[{p.id}] slide {n}, {p.intent} ({p.beat}){extra}")
        lines += [f"    {f.name}: {f.text}" for f in p.fields if f.name != "source"]
    return "\n".join(lines)


def plain(plans: list[SlidePlan]) -> Direction:
    """The fallback plan: still varied by position, so a failed call never
    gives ten identical slides."""
    grounds: list[Ground] = ["accent", "ground", "surface", "ground", "ink"]
    slides = []
    for n, p in enumerate(plans):
        hero: Hero = (
            "chart"
            if p.chart
            else "visual"
            if p.visual
            else "number"
            if any(f.name == "stat" for f in p.fields)
            else "headline"
        )
        side = "left" if n % 2 == 0 else "right"
        slides.append(
            SlideDirection(
                id=p.id,
                hero=hero,
                ground=grounds[n % len(grounds)] if n else "accent",
                image=False,
                idea=f"The {hero} large on the {side}, the rest in the other columns.",
            )
        )
    return Direction(concept="", slides=slides)


async def direct(
    seam: Seam, story: Storyline, theme: Theme, *, model: str, prefix: str
) -> Result[Direction, ModelError]:
    got = await seam.complete_json(
        "direction",
        Direction,
        system=SYSTEM,
        user=f"{_outline(story)}\n\nPlan every slide, by id, in order.",
        model=model,
        prefix=prefix,
        prompt_version=PROMPT_VERSION,
        max_tokens=16000,
    )
    if isinstance(got, Err):
        return got
    plan = got.value
    # At most IMAGE_CAP pictures, never on a slide that has its own picture.
    by = {p.id: p for p in story.slides}
    pictured = 0
    slides = []
    for s in plan.slides:
        p = by.get(s.id)
        wants = s.image and p is not None and p.chart is None and p.visual is None
        wants = wants and pictured < IMAGE_CAP
        pictured += wants
        slides.append(s.model_copy(update={"image": wants}))
    return ok(plan.model_copy(update={"slides": slides}))
