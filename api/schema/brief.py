"""Intake's output. Phase 08 produces it; defined here so there is one source.

Three entry paths — import, prompt, Q&A — and one output shape. v1 builds the
prompt and Q&A paths only; import needs the fetch worker, which is v3
infrastructure. The shape is identical either way, so import is purely
additive.
"""

from pydantic import Field

from schema.base import Schema


class BriefCta(Schema):
    label: str = Field(min_length=1, max_length=32)
    href: str = Field(min_length=1, max_length=2048)


class AssetRef(Schema):
    id: str = Field(min_length=1)
    description: str = Field(default="", max_length=200)


class Brief(Schema):
    # `goal`, `audience` and `cta` are always asked and never assumed. They
    # determine narrative structure, and guessing them wastes the entire
    # downstream pipeline.
    goal: str = Field(min_length=1, max_length=500)
    audience: str = Field(min_length=1, max_length=300)
    # APPROVED copy. Build arranges these; it does not write new claims.
    key_messages: list[str] = Field(min_length=3, max_length=5)
    proof_points: list[str] = Field(default_factory=list, max_length=20)
    tone: str = Field(min_length=1, max_length=200)
    cta: BriefCta
    assets: list[AssetRef] = Field(default_factory=list, max_length=50)
    constraints: str | None = Field(default=None, max_length=1000)
