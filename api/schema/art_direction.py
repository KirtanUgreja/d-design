"""The art-direction record — a DTCG primitive layer plus a semantic wrapper.

docs/v2/plan/01-ad-format.md, and docs/v2/art-direction-system.md -> "The
format". Pydantic owns it because the record crosses the language boundary now;
the Zod validator and the TypeScript types are generated from this file.

## What is DTCG here, and what is honestly not

The phase said to take the type names from the spec rather than from memory,
and doing that changed the design. Three things the 2025.10 draft settles:

**`color.$value` is an object**, not a hex string — `{colorSpace, components,
alpha?, hex?}`. The hex is the *optional* fallback, and the components are
authoritative.

**`dimension.$value` accepts `px` and `rem` and nothing else.** That is the
finding that reshapes this phase. This token system is deliberately fluid —
`clamp(3.5rem, 8vw, 8rem)` for a hero, `62ch` for a measure, `100svh` for a
scene frame — and none of those are expressible as a DTCG dimension. A format
that pretended otherwise would be emitting invalid DTCG that no tool could read,
which is worse than not claiming the standard at all.

**`$extensions` keys use reverse-domain notation.**

So the split is drawn where the spec actually draws it. The DTCG layer holds
colours, the fixed `px` spacing scale, font families and weights, durations,
easings and unitless numbers — real tokens a designer's tool can read. Fluid
lengths, clamp triples, the layout->fit table, texture structure, image
treatment, budgets and brand mapping all live under `$extensions`, because the
spec has no concept of them and inventing one would be proposing a standard
rather than using one.

That is a smaller DTCG surface than the phase sketch implies, and it is the
honest one. The win was never a full Figma round-trip — it is choosing a shape
that does not have to be migrated later.
"""

from typing import Annotated, Literal

from pydantic import Field

from schema.base import Schema

# Reverse domain notation, as the spec requires. One namespace, so everything
# this project adds is discoverable in one place and nothing collides with a
# tool's own extensions.
EXTENSION_KEY = "com.d-design.v2"

DtcgType = Literal[
    "color",
    "dimension",
    "fontFamily",
    "fontWeight",
    "duration",
    "cubicBezier",
    "number",
]


class DtcgColorValue(Schema):
    """`{colorSpace, components, alpha, hex}`.

    `components` is authoritative and `hex` is the optional fallback — which is
    the right way round for us too: the linter's APCA and WCAG maths wants
    channels, and a hex string is a lossy serialization of them.
    """

    color_space: Literal["srgb"] = "srgb"
    components: Annotated[list[float], Field(min_length=3, max_length=3)]
    alpha: float = Field(default=1.0, ge=0, le=1)
    hex: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class DtcgDimensionValue(Schema):
    """`px` or `rem`. The spec allows no other unit, which is why every
    viewport- or character-relative length in this system lives in
    `$extensions` instead of pretending to be one."""

    value: float
    unit: Literal["px", "rem"]


class DtcgDurationValue(Schema):
    value: float = Field(ge=0)
    unit: Literal["ms", "s"]


class DtcgToken(Schema):
    """One token. `$type` and `$value` are the spec's names, and Pydantic
    reaches them through an alias because a `$` cannot start a Python
    identifier — the wire format is the spec's, not ours."""

    type: DtcgType = Field(alias="$type")
    value: object = Field(alias="$value")
    description: str | None = Field(default=None, alias="$description")


# ---------------------------------------------------------------------------
# The `$extensions` payload: everything DTCG has no concept of.
# ---------------------------------------------------------------------------


class ContentBudgets(Schema):
    """Character caps, per art direction rather than per product.

    v1 treated these as universal constants and they are not: 58 characters is
    elegant at `editorial-light`'s display size and catastrophic at
    `bold-brutalist`'s `clamp(4rem, 12vw, 14rem)`.

    This is the point where "content is independent of styling" becomes
    "*mostly* independent", and the residue is character budget. The design
    response is to surface the coupling rather than hide it — which is why this
    is a stored field feeding an overflow banner, not a number derived at
    render time and quietly enforced.
    """

    eyebrow: int = Field(gt=0, le=200)
    headline: int = Field(gt=0, le=200)
    body: int = Field(gt=0, le=1000)
    quote: int = Field(gt=0, le=1000)
    stat: int = Field(gt=0, le=200)
    list_item: int = Field(gt=0, le=500)


class BrandMapping(Schema):
    """How this art direction consumes a brand — never the reverse.

    A marketer choosing an art direction is choosing that art direction.
    `cinematic-dark` maps a brand colour to accents and stays dark;
    `bold-brutalist` may make it a full-bleed ground, which is the only reason
    `allow_brand_background` is a field rather than a constant.
    """

    accent_role: Literal["accent", "bg", "ink"] = "accent"
    allow_brand_background: bool = False
    logo_treatment: Literal["mono", "full-color"] = "mono"
    # `auto` is not in the art-direction-system sketch and is the default here
    # for a reason v1 already found: `resolveBrand` picks its correction
    # direction from the ground's own luminance, which is strictly better than
    # an art direction declaring one and being wrong about it. The explicit
    # values stay for a direction that genuinely wants to override.
    contrast_strategy: Literal["lighten", "darken", "auto"] = "auto"


class ArtDirectionExtensions(Schema):
    """The semantic layer, under one reverse-domain key.

    `fluid` is the largest member and the one that exists because of the
    `dimension` unit restriction: clamp triples, `ch` measures and `svh` frames
    are the shape of a responsive type system and none of them are DTCG. Stored
    as the already-typed objects `web` uses, so nothing is re-modelled on the
    way through — a second model of a token is a second thing to keep in step.
    """

    budgets: ContentBudgets
    brand_mapping: BrandMapping
    default_motion: str = Field(min_length=1)
    # Kept as opaque-but-validated structure: the authoritative types are the
    # TypeScript ones the renderer reads, and re-declaring `Rhythm`, `Texture`
    # and `ImageTreatment` here would be a second definition that drifts. Phase
    # 03's linter is what walks inside them.
    fluid: dict[str, object] = Field(default_factory=dict)


class ArtDirectionRecord(Schema):
    """One version of one art direction.

    `(id, version)` is the identity, matching the primary key in migration
    0008. A version is not an audit column: a published page is pinned to one,
    so updating an art direction inserts a row and the old one has to remain
    readable byte for byte.
    """

    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9-]*$")
    version: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=120)
    author: Literal["system", "user"]
    # The DTCG document: a nested group structure of `DtcgToken` leaves. Typed
    # as a tree rather than a fixed record because that is what a token file
    # *is*, and because a designer's export will carry groups we did not name.
    tokens: dict[str, object] = Field(default_factory=dict)
    extensions: ArtDirectionExtensions
