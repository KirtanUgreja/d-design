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
colours, the fixed `px` spacing scale, font families and weights, and the
unitless numbers — real tokens a designer's tool can read. Fluid lengths, clamp
triples, the layout->fit table, texture structure, image treatment, budgets and
brand mapping all live under `$extensions`, because the spec has no concept of
them and inventing one would be proposing a standard rather than using one.

That is a smaller DTCG surface than the phase sketch implies, and it is the
honest one. The win was never a full Figma round-trip — it is choosing a shape
that does not have to be migrated later.

## Why the fluid layer is typed here, and not an opaque blob

The checkpoint that started this phase left `fluid` as `dict[str, object]`,
reasoning that re-declaring `Rhythm`, `Texture` and `ImageTreatment` in Python
would be a second definition of each and the drift would be silent. That was
right while the TypeScript constants were still the source of truth. It stops
being right at the step this phase ends on: the constants are deleted, the
record *is* the definition, and there is nothing left to drift against.

It is also what makes the switch possible at all. An opaque dict generates as
`z.record(z.unknown())`, so the TypeScript that turns a record back into an
`ArtDirection` would be casting rather than reading — one unchecked assertion
sitting between the database and every published page. Typed, `from-record.ts`
is a total mapping between two declared shapes, and a field added on either
side is a compile error on the other. The drift the checkpoint feared is
detected by the compiler instead of by a comment asking someone to be careful.

Where the two languages still have to agree by hand — a `fontFamily` naming a
family the TypeScript registry knows, a `defaultMotion` naming a vocabulary —
the agreement is checked at the boundary and fails closed, and the equality
fixture in `api/tests/test_art_direction_seed.py` is what proves the whole
record still renders the design it was migrated from.

## The DTCG document is a fixed record, not an open tree

A designer's export carries groups nobody here named, and this model forbids
them. That is deliberate for v2: there is no import path yet (user authoring is
`docs/v2/art-direction-system.md` -> "User-authored art directions", late v2 at
the earliest), and until there is, an open tree buys nothing and costs the type
safety above. The moment an import path exists, the honest shape is a separate
*imported document* model that this one is projected out of — a strict record
being fed by a lenient parser, which is the same arrangement `Scene` already
has with model output.
"""

from typing import Annotated, Literal, get_args

from pydantic import Field

from schema.base import Schema

# Reverse domain notation, as the spec requires. One namespace, so everything
# this project adds is discoverable in one place and nothing collides with a
# tool's own extensions.
EXTENSION_KEY = "com.d-design.v2"

# Ids are lower-kebab everywhere: art directions, motion vocabularies, and the
# `defaultMotion` that points from one to the other. A pattern rather than a
# length bound, because an id reaches a URL path and a JSON key.
_ID_PATTERN = r"^[a-z][a-z0-9-]*$"


# ---------------------------------------------------------------------------
# DTCG token values
# ---------------------------------------------------------------------------


class DtcgColorValue(Schema):
    """`{colorSpace, components, alpha, hex}`.

    `components` is authoritative and `hex` is the optional fallback — which is
    the right way round for us too: the linter's APCA and WCAG maths wants
    channels, and a hex string is a lossy serialization of them.

    Components are 0-1 per the spec, *not* 0-255. `to-css-vars.ts` still emits
    `rgb(r g b)` with 8-bit channels, so the scaling happens in one place on
    each side and the equality fixture is what proves the two agree.
    """

    color_space: Literal["srgb"] = "srgb"
    components: Annotated[
        list[Annotated[float, Field(ge=0, le=1)]], Field(min_length=3, max_length=3)
    ]
    alpha: float = Field(default=1.0, ge=0, le=1)
    hex: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class DtcgDimensionValue(Schema):
    """`px` or `rem`. The spec allows no other unit, which is why every
    viewport- or character-relative length in this system lives in
    `$extensions` instead of pretending to be one."""

    value: float
    unit: Literal["px", "rem"]


# ---------------------------------------------------------------------------
# DTCG tokens. One class per `$type` rather than one class with `value: object`,
# because a token whose value is `object` is exactly the "any string" token
# docs/v1/art-direction.md says will have to be redesigned — it just spells it
# in a different language.
#
# `$type` and `$value` are the spec's names, reached through an alias because a
# `$` cannot start a Python identifier. The wire format is the spec's, not ours.
# ---------------------------------------------------------------------------


class DtcgColorToken(Schema):
    type: Literal["color"] = Field(default="color", alias="$type")
    value: DtcgColorValue = Field(alias="$value")


class DtcgDimensionToken(Schema):
    type: Literal["dimension"] = Field(default="dimension", alias="$type")
    value: DtcgDimensionValue = Field(alias="$value")


# The families that exist, by name.
#
# **A `Literal`, not a validated string, and the two are not the same control.**
# A validated string rejects a bad value at runtime; a Literal means the model
# has no representation for one — it generates into a Zod enum and a TypeScript
# union, so `web`'s `FONT_REGISTRY` fails to compile if it names a family this
# list does not, and an uploaded token file naming one fails its parse before
# the linter runs. Exactly the reasoning `FontId` in `schema/experience.py`
# already spells out: a family name is echoed into a stylesheet, so free text
# there is a CSS injection with a friendly label on it.
#
# Adding a family is deliberately more than a row here: it also needs a
# self-hosted `@fontsource` import in `web/src/app/globals.css`, or the name
# resolves to a system fallback. Two edits is the right amount of friction for a
# decision that changes every published page.
#
# This is a *narrowing* of the DTCG spec, which lets a `fontFamily` be any
# string. We are consuming the format rather than defining it, and a consumer
# may be stricter than what it reads — the document we emit is still valid DTCG.
# `Syne` and `Space Grotesk` arrive with `bold-brutalist` in phase 04. Both are
# OFL-1.1 on Fontsource, which is the redistribution constraint rather than a
# taste one — these are served to our customers' audiences, not to visitors of
# our own site. Syne is the only one of the six that self-hosts a weight above
# 600, and that is why it is here: `clamp(4rem, 12vw, 14rem)` at weight 500 is
# not a brutalist headline, it is a large thin one.
FontFamilyName = Literal[
    "Fraunces", "Inter", "Newsreader", "Archivo", "Syne", "Space Grotesk"
]

VETTED_FONT_FAMILIES: frozenset[str] = frozenset(get_args(FontFamilyName))


class DtcgFontFamilyToken(Schema):
    """The family *name*, which is what the spec means and what a designer's
    tool round-trips. The id (`fraunces`) is the TypeScript registry's business;
    the name is what crosses the boundary."""

    type: Literal["fontFamily"] = Field(default="fontFamily", alias="$type")
    value: FontFamilyName = Field(alias="$value")


class DtcgFontWeightToken(Schema):
    type: Literal["fontWeight"] = Field(default="fontWeight", alias="$type")
    value: int = Field(ge=1, le=1000, alias="$value")


class DtcgNumberToken(Schema):
    type: Literal["number"] = Field(default="number", alias="$type")
    value: float = Field(alias="$value")


# ---------------------------------------------------------------------------
# The DTCG groups.
#
# `duration` and `cubicBezier` are the two standard types this document does
# not use, and their absence is not an oversight: motion is its own table and
# its own axis from phase 02 (docs/v2/plan/02-motion-axis.md), so emitting a
# duration here would be a second home for a number that lives there.
# ---------------------------------------------------------------------------


class DtcgPalette(Schema):
    bg: DtcgColorToken
    bg_elevated: DtcgColorToken
    ink: DtcgColorToken
    ink_muted: DtcgColorToken
    ink_faint: DtcgColorToken
    accent: DtcgColorToken
    accent_soft: DtcgColorToken
    veil: DtcgColorToken
    hairline: DtcgColorToken


class DtcgSpaceScale(Schema):
    """Seven fixed `px` steps. Named rather than indexed because DTCG groups are
    objects and an array is not a group — and named `step1..step7` rather than
    `1..7` so the keys are identifiers in both languages.

    Deliberately not semantic (`sm`, `md`): the same index means 8px in
    `cinematic-dark` and 4px in `editorial-light`, so a semantic name would be
    a claim about size that one of the two directions contradicts."""

    step1: DtcgDimensionToken
    step2: DtcgDimensionToken
    step3: DtcgDimensionToken
    step4: DtcgDimensionToken
    step5: DtcgDimensionToken
    step6: DtcgDimensionToken
    step7: DtcgDimensionToken


class DtcgFonts(Schema):
    display: DtcgFontFamilyToken
    text: DtcgFontFamilyToken


class DtcgTypeRole(Schema):
    """The part of a type role DTCG can express. The clamp triple that goes
    with it is in `$extensions.fluid.type`, and the split is the `dimension`
    unit restriction showing through — a `clamp(3.5rem, 8vw, 8rem)` is not a
    dimension and pretending otherwise is the one thing this format will not
    do."""

    leading: DtcgNumberToken
    tracking: DtcgNumberToken
    weight: DtcgFontWeightToken


class DtcgTypeScale(Schema):
    hero: DtcgTypeRole
    section: DtcgTypeRole
    lead: DtcgTypeRole
    normal: DtcgTypeRole
    muted: DtcgTypeRole
    eyebrow: DtcgTypeRole
    stat: DtcgTypeRole


class DtcgVisual(Schema):
    strength: DtcgNumberToken


class DtcgTokens(Schema):
    """The DTCG primitive layer. Serialized on its own it is a token file:
    every leaf carries `$type` and `$value`, every branch is a group.
    `features/art_direction/dtcg.py` is what adds the `$extensions` block and
    hands out the document."""

    color: DtcgPalette
    space: DtcgSpaceScale
    font: DtcgFonts
    type: DtcgTypeScale
    visual: DtcgVisual


# ---------------------------------------------------------------------------
# The `$extensions` payload: everything DTCG has no concept of.
# ---------------------------------------------------------------------------

Unit = Literal["px", "rem", "ch", "vw", "vh", "svh", "%"]

ColorRole = Literal[
    "bg",
    "bgElevated",
    "ink",
    "inkMuted",
    "inkFaint",
    "accent",
    "accentSoft",
    "veil",
    "hairline",
]

FontSlot = Literal["display", "text"]


class Length(Schema):
    """A one-part CSS length. The unit set is wider than DTCG's on purpose —
    `ch` is a measure, `svh` is a scene frame, `vw` is the middle of a clamp —
    and being wider is exactly why this is not a `dimension` token."""

    value: float
    unit: Unit


class ClampTriple(Schema):
    """`clamp(min, preferred, max)`, each part carrying its own unit because
    that is how the real values are written. A fixed size is the same value
    three times — one format, one parser, no branch for the fixed case."""

    min: Length
    preferred: Length
    max: Length


class FluidTypeRole(Schema):
    font: FontSlot
    size: ClampTriple
    case: Literal["uppercase"] | None = None
    color: ColorRole | None = None


class FluidTypeScale(Schema):
    hero: FluidTypeRole
    section: FluidTypeRole
    lead: FluidTypeRole
    normal: FluidTypeRole
    muted: FluidTypeRole
    eyebrow: FluidTypeRole
    stat: FluidTypeRole


SceneFit = Literal["viewport", "content"]
ScenePlace = Literal["center", "start", "end"]


class SceneFitTable(Schema):
    """Layout -> whether the scene owns the frame.

    A record with one field per layout rather than a map keyed by `Layout`, so
    that adding a layout to the schema without answering for it here is a type
    error on both sides — the same trick the TypeScript `Record<Layout, …>`
    played. The field names carry the layout's own spelling as their alias,
    because these are the values the AI writes.
    """

    full_bleed: SceneFit = Field(alias="full-bleed")
    split_left: SceneFit = Field(alias="split-left")
    split_right: SceneFit = Field(alias="split-right")
    centered: SceneFit
    stack: SceneFit
    grid: SceneFit


class FluidRhythm(Schema):
    """Everything in `Rhythm` except the seven-step space scale, which is fixed
    `px` and therefore lives in the DTCG layer."""

    scene_padding_y: ClampTriple
    scene_padding_x: ClampTriple
    measure: Length
    content_max: Length
    fit: SceneFitTable
    fit_min_block: Length
    fit_place: ScenePlace
    fit_scroll_margin: Length


Density = Literal[1, 2, 3, 4]
Steps = Literal[2, 3, 4]
RuleWeight = Literal["hairline", "thin", "thick"]


class TextureLayerBase(Schema):
    intensity: float = Field(ge=0, le=1)
    color: ColorRole
    scale: Length
    offset: Length


class GrainLayer(TextureLayerBase):
    kind: Literal["grain"]
    density: Density


class HalftoneLayer(TextureLayerBase):
    kind: Literal["halftone"]
    angle: float
    steps: Steps


class HatchLayer(TextureLayerBase):
    kind: Literal["hatch"]
    angle: float
    cross: bool
    density: Density


class DitherLayer(TextureLayerBase):
    kind: Literal["dither"]
    steps: Steps


class WeaveLayer(TextureLayerBase):
    kind: Literal["weave"]
    density: Density


class RuleLayer(TextureLayerBase):
    kind: Literal["rule"]
    axis: Literal["block", "inline"]
    weight: RuleWeight


# Closed on purpose, and it stays closed: the renderer has one implementation
# per kind and varies only intensity, so a seventh kind is a renderer change and
# therefore a real cost, not a token edit.
TextureLayer = Annotated[
    GrainLayer | HalftoneLayer | HatchLayer | DitherLayer | WeaveLayer | RuleLayer,
    Field(discriminator="kind"),
]

ImageTone = Literal["as-shot", "mono", "duotone", "posterize"]
ImageFrame = Literal["none", "hairline", "block", "inset"]


class Ratio(Schema):
    """A crop this art direction will accept, as `w / h`. Applied with
    `object-fit: cover` against a token `aspect-ratio`, never by re-encoding —
    so switching art directions re-crops instead of reprocessing."""

    w: int = Field(gt=0, le=100)
    h: int = Field(gt=0, le=100)


class ImageTreatment(Schema):
    """The art direction consuming a photograph. Same principle as brand
    colour — an uploaded image maps into the direction, it does not replace
    it."""

    tone: ImageTone
    overlay: TextureLayer | None = None
    frame: ImageFrame
    edge: Length
    veil: float = Field(ge=0, le=1)
    ratios: list[Ratio] = Field(min_length=1, max_length=6)


VisualBlend = Literal["screen", "multiply"]


class ArtDirectionFluid(Schema):
    """The half of the token set DTCG has no types for.

    Named `fluid` for the reason it exists — the `dimension` unit restriction —
    but it carries structure as well as lengths: a texture layer list and an
    image treatment are not lengths, they are shapes the spec has no concept
    of, and `$extensions` is the field that exists for exactly that.
    """

    type: FluidTypeScale
    rhythm: FluidRhythm
    texture: list[TextureLayer] = Field(max_length=8)
    image: ImageTreatment
    visual_blend: VisualBlend


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
    `bold-brutalist` makes it a full-bleed ground, which is the only reason
    `allow_brand_background` is a field rather than a constant.

    **Every field is required, and none of them had been until phase 04.** They
    carried defaults, which was fine while nothing read them and became a
    problem the moment something did: a Pydantic default generates into
    `z.enum(...).default(...).optional()`, so the value would have had to be
    written a second time in `from-record.ts` to fill the `undefined` — the same
    default in two languages, drifting silently, on the group that decides
    whether a customer's brand colour becomes a page's ground.

    Requiring them costs three constructor calls in `seed.py` and makes the wire
    form total, which is what lets the TypeScript boundary be a mapping rather
    than a mapping plus a set of guesses. It also reads better: an art direction
    *declaring* how it consumes a brand is the whole idea, and a declaration you
    can omit is a default wearing the word.
    """

    accent_role: Literal["accent", "bg", "ink"]
    allow_brand_background: bool
    logo_treatment: Literal["mono", "full-color"]
    # `auto` is not in the art-direction-system sketch and is what both v1
    # directions choose, for a reason v1 already found: `resolveBrand` picks its
    # correction direction from the ground's own luminance, which is strictly
    # better than an art direction declaring one and being wrong about it. The
    # explicit values are for a ground whose luminance sits near the crossover,
    # where the computation has no good answer and a designer does.
    contrast_strategy: Literal["lighten", "darken", "auto"]


class ArtDirectionExtensions(Schema):
    """The semantic layer, under one reverse-domain key."""

    budgets: ContentBudgets
    brand_mapping: BrandMapping
    # A `motion_vocabularies` id. Not a `Literal`, for the same reason
    # `ArtDirectionId` stops being one in this phase — the vocabularies are
    # rows from phase 02 onward, and a Literal here would be a second list of
    # them that goes stale silently. Resolution fails closed.
    default_motion: str = Field(min_length=1, max_length=64, pattern=_ID_PATTERN)
    fluid: ArtDirectionFluid


# ---------------------------------------------------------------------------
# The record, and the reference to it
# ---------------------------------------------------------------------------


class ArtDirectionRef(Schema):
    """What an `Experience` stores, and what replaces v1's `ArtDirectionId`.

    Not a looser string than the `Literal` it replaces — a *stronger* check,
    because it is validated against the store and therefore proves the version
    exists too, which a Literal never could. The compile-time exhaustiveness
    that a `Record<ArtDirectionId, …>` gave cannot survive a database read, and
    pretending otherwise is worse than losing it deliberately: an unknown
    reference is `not_found`, and the page that asked renders its designed
    empty state rather than an unstyled tree.
    """

    id: str = Field(min_length=1, max_length=64, pattern=_ID_PATTERN)
    version: int = Field(ge=1)


class ArtDirectionRecord(Schema):
    """One version of one art direction.

    `(id, version)` is the identity, matching the primary key in migration
    0008. A version is not an audit column: a published page is pinned to one,
    so updating an art direction inserts a row and the old one has to remain
    readable byte for byte.
    """

    id: str = Field(min_length=1, max_length=64, pattern=_ID_PATTERN)
    version: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=120)
    author: Literal["system", "user"]
    tokens: DtcgTokens
    extensions: ArtDirectionExtensions

    @property
    def ref(self) -> ArtDirectionRef:
        return ArtDirectionRef(id=self.id, version=self.version)


# ---------------------------------------------------------------------------
# The linter's report
# ---------------------------------------------------------------------------


class LintFinding(Schema):
    """One reason an art direction cannot be saved.

    **There is no severity field, and that absence is the design.** Every rule
    in this linter is a hard failure — "an AD that fails cannot be saved. Not a
    warning, not a badge" (docs/v2/plan/03-ad-linter.md). A severity enum is how
    a gate becomes decorative: the first inconvenient rule becomes a warning,
    and then the warnings are a list nobody reads.

    `message` is written for a person and is part of the feature. A linter that
    says `SCALE_RANGE_VIOLATION` teaches nobody anything; the rule code is for
    grepping and the message is for fixing.
    """

    rule: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z][A-Z0-9_]*$")
    # Dotted path into the record, so a finding points at a field rather than at
    # an art direction. Never carries the offending *value* — a token set is a
    # customer's design and this string reaches a log.
    path: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=500)


class LintReport(Schema):
    findings: list[LintFinding] = Field(default_factory=list, max_length=200)

    @property
    def ok(self) -> bool:
        return not self.findings
