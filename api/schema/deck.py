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

from pydantic import BaseModel, Field, field_validator, model_validator


def _block_fills_role(block: SlideBlock, role: str) -> bool:
    """The role a block can fill. Kept in one place so the renderer's block
    allocation and the schema's validator cannot drift apart."""
    if isinstance(block, TextBlock):
        if block.style == "headline":
            return role == "headline"
        if block.style in ("eyebrow", "caption"):
            return role == "aside"
        return role == "body"
    if isinstance(block, StatBlock):
        return role == "stats"
    if isinstance(block, QuoteBlock):
        return role == "quote"
    if isinstance(block, ChartBlock):
        return role == "chart"
    # ImageBlock is the last member of the closed SlideBlock union.
    return role == "media"


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


class LayoutRegion(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """One region of a slide's layout: a semantic role and a relative size.

    The model *generates* the layout (phase 10) within the family's grammar.
    ``role`` is what the region is for, ``span`` is a size *relationship* to
    the other regions (never a pixel), and ``emphasis`` is hierarchy. None of
    these is presentational — patterns.md rule 1 holds: the renderer maps them
    to CSS via the family tokens.
    """

    role: Literal["headline", "body", "media", "stats", "quote", "chart", "aside"]
    span: Literal["full", "two-thirds", "half", "third", "quarter"]
    emphasis: Literal["primary", "secondary", "quiet"] = "secondary"


class LayoutStructure(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """A slide's generated layout: an ordered sequence of regions.

    The grammar (schema/grammars.py) constrains which roles, spans, and how
    many regions are legal for the deck's family; the Deck validator enforces
    it. The ordering is the reading order — the first region leads the slide.
    """

    regions: list[LayoutRegion] = Field(min_length=1, max_length=6)


class Slide(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """One slide: a generated layout and the content blocks that fill it.

    ``layout`` is the generated structure (phase 10) — the model composes
    regions within the family's grammar instead of picking from a catalogue.
    ``blocks`` are the content that fills the regions; a validator enforces
    that every block belongs to a region and every region is filled.
    ``motion_intent`` is the *kind* of reveal, not a duration — the family's
    motion vocabulary owns pacing.
    """

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1, max_length=120)
    layout: LayoutStructure
    blocks: list[SlideBlock] = Field(min_length=1, max_length=12)
    cta: Cta | None = None
    motion_intent: Literal["reveal", "emphasize", "transition", "none"] = "reveal"

    @model_validator(mode="after")
    def blocks_fill_the_layout(self) -> Slide:
        """Two whole-tree rules that do not survive the JSON Schema trip.

        - One headline per slide, and it comes first (the v1 rule survives).
        - Every block belongs to a region of the slide's layout, and every
          region is filled — the layout/block consistency that keeps a
          generated layout from being a frame around nothing.
        """
        headlines = [b for b in self.blocks if isinstance(b, TextBlock) and b.style == "headline"]
        if len(headlines) > 1:
            raise ValueError("a slide may have at most one headline")
        if headlines and self.blocks[0] is not headlines[0]:
            raise ValueError("the headline must be the first block")

        roles = [r.role for r in self.layout.regions]
        for region_role in roles:
            if not any(_block_fills_role(b, region_role) for b in self.blocks):
                raise ValueError(f"layout region '{region_role}' has no block filling it")
        for block in self.blocks:
            if not any(_block_fills_role(block, r) for r in roles):
                raise ValueError(f"block '{block.kind}' has no region in the layout")
        return self


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

    @model_validator(mode="after")
    def layouts_follow_the_family_grammar(self) -> Deck:
        """Every slide's layout is a legal move in the family's grammar.

        The grammar (schema/grammars.py) is the v2 constraint that replaced the
        curated catalogue: roles, spans, and density must be legal for this
        family. A family whose layout character has no grammar is a registry
        bug — this fails closed (raises), never defaults.
        """
        from schema.design_families import family_by_id
        from schema.grammars import grammar_for_family

        family = family_by_id(self.family_id)
        if family is None:
            raise ValueError(f"unknown design family: {self.family_id}")
        grammar = grammar_for_family(family)
        if grammar is None:
            raise ValueError(
                f"design family '{self.family_id}' has no grammar for layout "
                f"character '{family.axis[5]}'"
            )
        for slide in self.slides:
            roles = {r.role for r in slide.layout.regions}
            spans = {r.span for r in slide.layout.regions}
            if not roles.issubset(set(grammar.roles)):
                raise ValueError(
                    f"layout roles {sorted(roles)} not legal in grammar "
                    f"'{grammar.layout_character}'"
                )
            if not spans.issubset(set(grammar.spans)):
                raise ValueError(
                    f"layout spans {sorted(spans)} not legal in grammar "
                    f"'{grammar.layout_character}'"
                )
            if len(slide.layout.regions) > grammar.max_regions:
                raise ValueError(
                    f"layout has {len(slide.layout.regions)} regions, grammar "
                    f"'{grammar.layout_character}' allows at most {grammar.max_regions}"
                )
        return self

    @model_validator(mode="after")
    def opener_leads_with_a_full_region(self) -> Deck:
        """The first slide's first region is full-span.

        The v1 "opener" narrative role is now expressed structurally: the first
        slide leads with a full-width region (headline or media). Every grammar
        has a full span, so this is a through-line rule, not a presentational
        one.
        """
        if not self.slides:
            return self
        first_region = self.slides[0].layout.regions[0]
        if first_region.span != "full":
            raise ValueError("the opener's leading region must span full width")
        return self
