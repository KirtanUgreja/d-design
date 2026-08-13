"""The Deck schema — the Pydantic source of truth for the whole system.

The Deck is the boundary between the pipeline and the renderer: what the
mapping pass produces and the slide builder consumes. It carries **no
presentational values** — no hex, no px, no font name, no duration. The model
cannot emit a hex code because the schema has no field that accepts one
(non-negotiable 7, patterns.md rule 1).

The discriminated union stays nested inside Deck (an object) rather than at the
schema root — that is the shape strict structured-output validators handle
cleanly (python.md -> "The constraints that do not survive the trip").
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ImageBlock(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """An image expressed as *what it is*, never how it looks.

    subject is a plain-language description of the content; role is how the
    slide will use it (background, hero, illustration, chart companion). The
    family's tokens style it, and the exporter embeds the generated asset as a
    data URI. There is no URL field and no path field — a generated image is
    embedded at export so the zero-network guarantee holds.
    """

    kind: Literal["image"]
    subject: str = Field(min_length=3, max_length=160)
    role: Literal["background", "hero", "illustration", "chart_companion"]
    alt: str = Field(min_length=3, max_length=240)


class TextBlock(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """A headline or body text. Character caps live here (they are what rejects
    an over-long model response) and are restated in the prompt as hard numbers
    because structured-output implementations widely ignore min/maxLength.
    """

    kind: Literal["text"]
    style: Literal["headline", "body", "eyebrow", "caption"]
    content: str = Field(min_length=1, max_length=500)


class StatBlock(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """One number with a label. The value is a string so the model can write
    "3.4x" or "92%"; the renderer formats it."""

    kind: Literal["stat"]
    value: str = Field(min_length=1, max_length=20)
    label: str = Field(min_length=1, max_length=80)


class QuoteBlock(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    kind: Literal["quote"]
    text: str = Field(min_length=1, max_length=400)
    attribution: str = Field(min_length=1, max_length=120)


class ChartSeries(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """One series point in a chart. A small object, not a positional tuple —
    tuples emit prefixItems, which strict structured-output providers reject
    (array schema missing items). An object survives strict providers and is
    clearer than a bare pair."""

    label: str = Field(min_length=1, max_length=80)
    value: float


class ChartBlock(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """A chart is spec'd here (what it says) and built in the slide builder
    (how it looks). v1 ships bars, lines and donuts; the rest is v2."""

    kind: Literal["chart"]
    chart_type: Literal["bar", "line", "donut"]
    title: str = Field(min_length=1, max_length=120)
    series: list[ChartSeries] = Field(min_length=1, max_length=12)


SlideBlock = ImageBlock | TextBlock | StatBlock | QuoteBlock | ChartBlock


class Cta(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """A call-to-action. The destination is a URL the user approved (or a
    protocol the model is allowed to emit), so this is a bounded string — never
    a presentational value."""

    label: str = Field(min_length=1, max_length=40)
    destination: str = Field(min_length=1, max_length=2048)


class Slide(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """One slide: a layout archetype and the content blocks that fill it.

    layout_archetype is a reference into the curated catalogue, never an
    invented shape. motion_intent is the *kind* of reveal, not a duration —
    the family's motion vocabulary owns pacing.
    """

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1, max_length=120)
    layout_archetype: str = Field(min_length=1, max_length=40)
    variant: str = Field(default="", max_length=40)
    blocks: list[SlideBlock] = Field(min_length=1, max_length=12)
    cta: Cta | None = None
    motion_intent: Literal["reveal", "emphasize", "transition", "none"] = "reveal"

    @field_validator("blocks")
    @classmethod
    def blocks_are_ordered(cls, value: list[SlideBlock]) -> list[SlideBlock]:
        """One headline per slide, and it comes first. These are whole-tree
        rules that do not survive the JSON Schema trip, so they are Python-only
        (python.md -> "The constraints that do not survive the trip")."""
        headlines = [b for b in value if isinstance(b, TextBlock) and b.style == "headline"]
        if len(headlines) > 1:
            raise ValueError("a slide may have at most one headline")
        if headlines and value[0] is not headlines[0]:
            raise ValueError("the headline must be the first block")
        return value


class Deck(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """The per-deck design system plus the slides. This is the whole artefact
    the pipeline produces and the renderer consumes."""

    family_id: str = Field(min_length=1, max_length=40)
    slides: list[Slide] = Field(min_length=1, max_length=40)

    @field_validator("family_id")
    @classmethod
    def family_id_is_registered(cls, value: str) -> str:
        from schema.design_families import family_by_id

        if family_by_id(value) is None:
            raise ValueError(f"unknown design family: {value}")
        return value

    @field_validator("slides")
    @classmethod
    def slide_ids_are_unique(cls, value: list[Slide]) -> list[Slide]:
        ids = [s.id for s in value]
        if len(ids) != len(set(ids)):
            raise ValueError("slide ids must be unique within a deck")
        return value
