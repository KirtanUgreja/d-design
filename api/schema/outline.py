"""The Brief (what the user typed) and the Outline (what the interview approved).

The Outline is the first schema-validated shape and the trust device: it is the
approved-claims record the mapping pass turns into a Deck. Claim provenance is
recorded here — which claims came from the user, which from the model — so an
invented claim can be traced and rejected (spec.md risk 2).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

ClaimSource = Literal["user", "model"]


class BrandKit(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """v1 brand kit is typed text, not file upload (uploads are v2). Colors,
    fonts and vibe are strings the design family maps to tokens — never
    presentational values."""

    colors: str = Field(default="", max_length=300)
    fonts: str = Field(default="", max_length=300)
    vibe: str = Field(default="", max_length=300)


class Brief(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """The user's typed input: the interview starting point, not the outline."""

    topic: str = Field(min_length=1, max_length=500)
    slide_count: int = Field(ge=1, le=40)
    audience: str = Field(default="", max_length=500)
    goal: str = Field(default="", max_length=500)
    brand_kit: BrandKit = Field(default_factory=BrandKit)
    extra_info: str = Field(default="", max_length=2000)


class OutlineClaim(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """A single claim the deck will make, with its provenance."""

    text: str = Field(min_length=1, max_length=240)
    source: ClaimSource


class OutlineSection(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """A section of the deck: a narrative beat with the claims it carries."""

    heading: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=400)
    claims: list[OutlineClaim] = Field(min_length=1, max_length=20)


class Outline(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """The approved-claims record. Schema-validated at the boundary; the mapping
    pass consumes it; the user has approved it before any slide is built."""

    title: str = Field(min_length=1, max_length=120)
    audience: str = Field(min_length=1, max_length=300)
    goal: str = Field(min_length=1, max_length=300)
    sections: list[OutlineSection] = Field(min_length=1, max_length=12)
    must_haves: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("sections")
    @classmethod
    def sections_are_nonempty(cls, value: list[OutlineSection]) -> list[OutlineSection]:
        for section in value:
            if not section.summary.strip():
                raise ValueError("every section needs a summary")
        return value
