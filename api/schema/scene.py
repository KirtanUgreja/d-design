"""The IR — the single contract between the AI, the editor, and the renderer.

**No block prop may contain a presentational value.** No hex codes, no pixels,
no rem, no durations, no easing curves, no font names, no z-index. A block says
`emphasis: "hero"`; the art direction decides that means
`clamp(3.5rem, 8vw, 8rem)`.

That is enforced structurally first — there is no field here that accepts one —
and by `no_style.py` second. When the backstop fires, the schema has a gap a
value slipped through: add the missing concept to the art direction, never an
exception to the check.

docs/v1/scene-schema.md is the specification. This file types it.
"""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from schema.base import Schema

Mode = Literal["scroll", "slides"]
SceneIntent = Literal["hook", "problem", "reveal", "proof", "cta"]
Layout = Literal["full-bleed", "split-left", "split-right", "centered", "stack", "grid"]
Motion = Literal["reveal", "emphasize", "parallax", "none"]
Region = Literal["bg", "content", "left", "right", "cells"]

# Each layout exposes named regions. A block's `region` says where it goes; the
# art direction says what that means spatially.
#
# `left` and `right` name authoring position, not screen position — the renderer
# resolves them through CSS logical properties, so an RTL locale mirrors the
# whole layout by setting `dir` and nothing in this schema changes.
LAYOUT_REGIONS: dict[Layout, frozenset[Region]] = {
    "full-bleed": frozenset({"bg", "content"}),
    "split-left": frozenset({"left", "right"}),
    "split-right": frozenset({"left", "right"}),
    "centered": frozenset({"content"}),
    "stack": frozenset({"content"}),
    "grid": frozenset({"cells"}),
}

DEFAULT_REGION: dict[Layout, Region] = {
    "full-bleed": "content",
    "split-left": "left",
    "split-right": "left",
    "centered": "content",
    "stack": "content",
    "grid": "cells",
}

# `javascript:`, `data:` and `vbscript:` are the classic injected-link schemes,
# and a protocol-relative `//host` inherits the page's scheme while pointing
# somewhere else entirely. Rejecting by allowlist makes an injected phishing
# link structurally impossible rather than filtered.
#
# A `Field(pattern=...)` rather than a `model_validator`, on purpose: a pattern
# is a JSON Schema keyword and a `model_validator` is not, so this is the
# difference between a check the generated Zod validator inherits and one that
# silently stays Python-only. The property panel patches `CTA.href` directly
# (docs/v1/scene-schema.md -> "What the property panel exposes"), so this is a
# check the editor needs offline, not only at Build's output boundary — which
# is what earns it the field-level form over the cross-field one below.
#
# Lowercase schemes only. A pasted `HTTPS://` is rejected rather than
# normalized — stricter than `urlparse().scheme.lower()` was, and safe to be:
# a validator that is too strict fails closed, never open.
#
# No lookahead: Pydantic's Rust regex engine does not support it, and the same
# pattern crosses into Zod's `.regex()` on the TypeScript side, so it has to
# stay in the portable subset both engines share. `/(?!/)` (single slash, not
# a second one) becomes `/($|[^/])` (a slash followed by end-of-string or any
# non-slash character) — same verdict, no look-around.
HREF_PATTERN = r"^(https?://|mailto:|tel:|#|/($|[^/]))"


# ---------------------------------------------------------------------------
# Block props — the tagged union, and the only place copy lives
# ---------------------------------------------------------------------------
#
# The spec draws `Block` with both a `type` field and a `props` object
# discriminated on it. Pydantic cannot discriminate a union by a field outside
# the union, and the duplicate buys nothing, so `type` lives on the props and
# `Block.props` is the union. The patch shape phase 09 depends on —
# `{sceneId, blockId, props}` — is unchanged, and the union stays nested inside
# an object, which is the shape strict structured-output validators handle
# cleanly (docs/coderules/python.md).
#
# Character caps will be violated routinely and rejected reliably. That is the
# design: LLMs write too much, and a 140-character headline destroys a
# cinematic layout no matter how good the tokens are.


class EyebrowProps(Schema):
    """A short kicker or label sitting above a headline — "CASE STUDY",
    "NEW IN 2026", a product name. A fragment, never a sentence, and never a
    place to put prose: if what you are writing is a sentence, it belongs in
    `body`, and if it is the point of the scene it belongs in `headline`.
    """

    type: Literal["eyebrow"]
    text: str = Field(min_length=1, max_length=24)


class HeadlineProps(Schema):
    """The one line the scene is about. Every scene wants at most one, and a
    scene with something to say should have it."""

    type: Literal["headline"]
    text: str = Field(min_length=1, max_length=60)
    emphasis: Literal["hero", "section"] | None = None


class BodyProps(Schema):
    """Supporting prose. The only block that takes more than one sentence, and
    the right home for any explanation, description or argument."""

    type: Literal["body"]
    text: str = Field(min_length=1, max_length=240)
    emphasis: Literal["lead", "normal", "muted"] | None = None


class QuoteProps(Schema):
    """A testimonial in a named person's own words. Only for something the
    brief actually quoted."""

    type: Literal["quote"]
    text: str = Field(min_length=1, max_length=200)
    # Caps on attribution and role are this phase's choice — the spec gives one
    # cap for the quote and leaves these open, and an unbounded field is one
    # the model will fill.
    attribution: str | None = Field(default=None, max_length=60)
    role: str | None = Field(default=None, max_length=60)


class ListItem(Schema):
    # Same: the spec caps the item count, not the item. Chosen here so the
    # constraint exists somewhere rather than nowhere.
    text: str = Field(min_length=1, max_length=80)
    detail: str | None = Field(default=None, max_length=120)


class ListProps(Schema):
    """Two to five short parallel items. Use it when the content is genuinely a
    set; three sentences about one idea are `body`, not a list."""

    type: Literal["list"]
    items: list[ListItem] = Field(min_length=2, max_length=5)
    style: Literal["bullets", "numbered", "checks"]


class StatProps(Schema):
    """One number and what it measures — `value` is the number itself, kept
    very short ("68%", "10min", "3x"), and `label` says what it counts. The
    number must already appear in the brief's approved copy."""

    type: Literal["stat"]
    # A string, not a number — "10x", "2.4M" and "<50ms" are all legitimate.
    # The renderer animates a count-up when it parses as numeric and holds it
    # static otherwise.
    value: str = Field(min_length=1, max_length=12)
    label: str = Field(min_length=1, max_length=40)
    prefix: str | None = Field(default=None, max_length=8)
    suffix: str | None = Field(default=None, max_length=8)


class ImageProps(Schema):
    """An uploaded image, referenced by the asset id it was given. Never invent
    an id; if no asset fits, use `abstract-visual`."""

    type: Literal["image"]
    asset_id: str = Field(min_length=1)
    # Required by the schema, not by convention. Generated experiences are
    # public web pages.
    alt: str = Field(min_length=1, max_length=160)
    fit: Literal["cover", "contain"]
    treatment: Literal["plain", "framed", "bleed"] | None = None


class VideoProps(Schema):
    """An uploaded video, referenced by the asset id it was given."""

    type: Literal["video"]
    asset_id: str = Field(min_length=1)
    poster_asset_id: str | None = None
    autoplay: bool
    loop: bool


class CtaProps(Schema):
    """The call to action. Its label and href come from the brief and are never
    composed here. At most one per experience."""

    type: Literal["cta"]
    label: str = Field(min_length=1, max_length=32)
    href: str = Field(min_length=1, max_length=2048, pattern=HREF_PATTERN)
    style: Literal["primary", "secondary"]


class AbstractVisualProps(Schema):
    """Rendered as code — CSS, SVG, canvas — using art-direction colours. Zero
    asset cost, always on-brand. This is what makes a sparse scene look
    designed rather than empty."""

    type: Literal["abstract-visual"]
    generator: Literal[
        "gradient-mesh", "particle-field", "grid-lines", "orb", "noise-veil"
    ]
    seed: int = Field(ge=0, le=2**31 - 1)
    intensity: Literal["subtle", "medium", "bold"]


class SlotProps(Schema):
    """The escape hatch. Runs in `<iframe srcdoc sandbox="allow-scripts">` with
    no `allow-same-origin` — no storage, no cookies, no parent DOM, no
    credentialed fetch.

    `description` is what the editor shows and what an AI edit operates on; the
    code itself is not user-editable in v1. The code fields are exempt from the
    no-styling walker for the obvious reason that CSS is presentational by
    definition — the sandbox is what contains them instead (see no_style.py)."""

    type: Literal["slot"]
    description: str = Field(min_length=1, max_length=200)
    html: str = Field(default="", max_length=20_000)
    css: str = Field(default="", max_length=20_000)
    js: str = Field(default="", max_length=20_000)
    height: Literal["viewport", "auto"]


BlockProps = Annotated[
    EyebrowProps
    | HeadlineProps
    | BodyProps
    | QuoteProps
    | ListProps
    | StatProps
    | ImageProps
    | VideoProps
    | CtaProps
    | AbstractVisualProps
    | SlotProps,
    Field(discriminator="type"),
]


class Block(Schema):
    id: str = Field(min_length=1)
    region: Region | None = None
    props: BlockProps
    # Stagger is derived from block index within a region. The AI picks
    # *whether* something moves and roughly *why*. Never how.
    motion: Motion = "reveal"


class Scene(Schema):
    id: str = Field(min_length=1)
    intent: SceneIntent
    layout: Layout
    blocks: list[Block] = Field(min_length=1, max_length=8)
    notes: str | None = Field(default=None, max_length=2000)  # unused in v1

    @model_validator(mode="after")
    def _structural_rules(self) -> "Scene":
        allowed = LAYOUT_REGIONS[self.layout]
        for block in self.blocks:
            if block.region is not None and block.region not in allowed:
                raise ValueError(
                    f"region {block.region!r} does not exist on layout {self.layout!r}"
                )

        headlines = sum(1 for b in self.blocks if b.props.type == "headline")
        if headlines > 1:
            raise ValueError(f"a scene has at most one Headline, found {headlines}")

        if self.layout == "grid":
            cells = sum(1 for b in self.blocks if (b.region or "cells") == "cells")
            if not 2 <= cells <= 4:
                raise ValueError(f"grid takes 2-4 blocks in cells, found {cells}")

        ids = [b.id for b in self.blocks]
        if len(set(ids)) != len(ids):
            raise ValueError("block ids must be unique within a scene")

        return self


def resolved_region(scene: Scene, block: Block) -> Region:
    """Where a block actually goes. One place, so the renderer and the editor
    cannot disagree about what an absent `region` means."""
    return block.region or DEFAULT_REGION[scene.layout]
