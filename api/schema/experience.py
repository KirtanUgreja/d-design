"""The root of the tree, the things it references, and the two rules Pydantic
cannot own.

Those two live here as functions rather than as validators, because both need
data the model does not have — the asset table, and the Brief. Keeping them in
`schema/` keeps each rule next to the shape it guards; keeping them off the
model keeps this package free of a database import, which is also what keeps it
cleanly generatable. A validator that needs the database cannot cross to
TypeScript.
"""

from collections.abc import Sequence
from typing import Literal

from pydantic import Field, model_validator

from lib.result import Result, err, ok
from schema.base import Schema
from schema.scene import Mode, Scene


class Asset(Schema):
    id: str = Field(min_length=1)
    kind: Literal["image", "video"]
    storage_key: str = Field(min_length=1)
    mime: str = Field(min_length=1, max_length=128)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    alt: str | None = Field(default=None, max_length=160)
    # Not decoration. Generated imagery carries different legal and brand risk
    # than an uploaded product shot, and a marketer needs to know which is
    # which before publishing.
    source: Literal["upload", "generated"]


class BrandKit(Schema):
    id: str = Field(min_length=1)
    display_font: str = Field(min_length=1, max_length=120)
    text_font: str = Field(min_length=1, max_length=120)
    primary: str = Field(min_length=1, max_length=32)
    secondary: str = Field(min_length=1, max_length=32)
    neutral: str = Field(min_length=1, max_length=32)
    logo_asset_id: str | None = None


class ExperienceMeta(Schema):
    created_at: str
    updated_at: str
    published_at: str | None = None


class Experience(Schema):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    mode: Mode
    brand_id: str = Field(min_length=1)
    art_direction: Literal["cinematic-dark"]  # v1: one value
    scenes: list[Scene] = Field(min_length=3, max_length=12)
    meta: ExperienceMeta

    @model_validator(mode="after")
    def _structural_rules(self) -> "Experience":
        hooks = [i for i, s in enumerate(self.scenes) if s.intent == "hook"]
        if hooks != [0]:
            raise ValueError(
                f"exactly one scene has intent 'hook' and it is first; found at {hooks}"
            )

        blocks = [b for s in self.scenes for b in s.blocks]

        if not any(b.props.type == "cta" for b in blocks):
            raise ValueError("an experience has at least one CTA")

        slots = sum(1 for b in blocks if b.props.type == "slot")
        if slots > 1:
            raise ValueError(f"an experience has at most one Slot, found {slots}")

        ids = [s.id for s in self.scenes]
        if len(set(ids)) != len(ids):
            raise ValueError("scene ids must be unique")

        return self


def assert_assets_resolve(
    scenes: Sequence[Scene], known_ids: frozenset[str]
) -> Result[None]:
    """Every `assetId` names a real asset the caller owns.

    Called at the pipeline boundary where the asset id set is available. An
    `assetId` that resolves to nothing is a validation failure rather than a
    broken image on someone's launch page — the same "arrange, never invent"
    rule that governs `CTA.href`.

    Takes `scenes` rather than a whole `Experience` because Build validates
    one streamed scene at a time (docs/v1/plan/06-model-seam-and-build.md);
    passing `[exp.scenes]` still works for whole-tree callers.
    """
    missing: list[str] = []
    for scene in scenes:
        for block in scene.blocks:
            props = block.props
            if props.type == "image":
                if props.asset_id not in known_ids:
                    missing.append(props.asset_id)
            elif props.type == "video":
                if props.asset_id not in known_ids:
                    missing.append(props.asset_id)
                if props.poster_asset_id and props.poster_asset_id not in known_ids:
                    missing.append(props.poster_asset_id)
    if missing:
        return err("invalid_input", f"unknown asset ids: {sorted(set(missing))}")
    return ok(None)


def assert_hrefs_are_supplied(
    scenes: Sequence[Scene], supplied: frozenset[str]
) -> Result[None]:
    """Every `CTA.href` traces back to a URL the user gave us.

    The scheme allowlist on `CtaProps` stops the dangerous shapes; this stops
    the plausible ones. The AI arranges URLs, it never composes them, so an
    injected phishing link has no route into a published page.
    """
    invented = [
        b.props.href
        for s in scenes
        for b in s.blocks
        if b.props.type == "cta" and b.props.href not in supplied
    ]
    if invented:
        return err(
            "invalid_input", f"hrefs not supplied by the brief: {sorted(set(invented))}"
        )
    return ok(None)


def assert_stats_are_supported(
    scenes: Sequence[Scene], proof_points: frozenset[str]
) -> Result[None]:
    """Every `Stat.value` appears somewhere in the brief's proof points.

    The weakest of the three, deliberately: it is a substring check, because a
    proof point reads "we cut latency to under 50ms" and the stat reads
    "<50ms". It catches the invented number, which is the failure that matters,
    and does not try to catch paraphrase.
    """
    haystack = " ".join(proof_points).lower()
    invented = [
        b.props.value
        for s in scenes
        for b in s.blocks
        if b.props.type == "stat" and b.props.value.lower() not in haystack
    ]
    if invented:
        return err(
            "invalid_input",
            f"stats not traceable to a proof point: {sorted(set(invented))}",
        )
    return ok(None)
