"""Intake's output. Phase 08 produces it; defined here so there is one source.

Three entry paths — import, prompt, Q&A — and one output shape. v1 builds the
prompt and Q&A paths only; import needs the fetch worker, which is v3
infrastructure. The shape is identical either way, so import is purely
additive.
"""

from pydantic import Field

from schema.base import Schema
from schema.scene import HREF_PATTERN


class BriefCta(Schema):
    label: str = Field(min_length=1, max_length=32)
    # The same allowlist `CtaProps.href` uses, imported rather than restated
    # (docs/v1/plan/08-intake.md -> "The URL rule": "Validate it here with the
    # same scheme allowlist phase 06 uses"). This is the *entry* of every URL
    # in the system — the AI never composes one, it only arranges this — so
    # rejecting `javascript:`/`data:`/`vbscript:`/`//host` here is what makes
    # phase 06's provenance check a check on already-safe values rather than
    # the only thing standing between an injected link and a published page.
    href: str = Field(min_length=1, max_length=2048, pattern=HREF_PATTERN)


class AssetRef(Schema):
    id: str = Field(min_length=1)
    description: str = Field(default="", max_length=200)


class BriefDraft(Schema):
    """What the Intake model is allowed to produce — and, far more importantly,
    what it is not.

    There is no `goal`, no `audience` and no `cta` field here. That is the
    enforcement of docs/v1/plan/08-intake.md -> "Always ask, never assume": the
    three fields that determine narrative structure are taken verbatim from the
    user's own answers in `features/intake/interview.py` and are never in the
    model's output at all. A rule the model is merely *told* is a rule it
    follows most of the time; a field the schema does not have is one it cannot
    fill. Same reasoning as rule 7 and presentational values.

    `key_messages` and `proof_points` are approved copy, so the model's job
    here is to *select and split* the user's own words, never to smooth them —
    which `features/intake/checks.py` then verifies rather than trusts.

    Not in `EXPORTED`: it is an internal step between the user and a `Brief`,
    and `web` only ever sees the `Brief`.
    """

    key_messages: list[str] = Field(min_length=3, max_length=5)
    proof_points: list[str] = Field(default_factory=list, max_length=20)
    tone: str = Field(min_length=1, max_length=200)
    constraints: str | None = Field(default=None, max_length=1000)


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
