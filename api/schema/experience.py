"""The root of the tree, the things it references, and the two rules Pydantic
cannot own.

Those two live here as functions rather than as validators, because both need
data the model does not have — the asset table, and the Brief. Keeping them in
`schema/` keeps each rule next to the shape it guards; keeping them off the
model keeps this package free of a database import, which is also what keeps it
cleanly generatable. A validator that needs the database cannot cross to
TypeScript.
"""

import re
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


# The fonts a brand may choose from, by id. **Never a user-supplied family
# string** — docs/v1/plan/10-brand-and-uploads.md calls that "the most
# natural-looking free-text token in the whole system and the one that most
# easily carries a payload", and it is right: a family name is echoed into a
# stylesheet, so free text there is a CSS injection with a friendly label on
# it.
#
# A `Literal` rather than a validated string, because the two are not the same
# control. A validated string rejects a bad value at runtime; a Literal means
# `BrandKit` has no representation for one — it generates into a Zod enum and a
# TypeScript union, so the editor cannot offer a text input for it and the API
# cannot accept one. Same reasoning as `BriefDraft` having no `audience`.
#
# Adding a font is deliberately more than a row here: the family also needs a
# self-hosted `@fontsource` import in `web/src/app/globals.css`, or the name
# resolves to a system fallback. Two edits is the right amount of friction for
# a decision that changes every published page.
FontId = Literal["fraunces", "inter"]


class BrandKit(Schema):
    id: str = Field(min_length=1)
    display_font: FontId
    text_font: FontId
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


# English prose conventionally spells out numbers under twenty ("last three
# drops", "under nine minutes") rather than using digits — verified live as
# a real, not hypothetical, case: CI run 31079241915's ecommerce-drop fixture
# wrote a Stat "9m" against a proof point reading "nine minutes", which no
# amount of digit-boundary matching alone can see through. Bounded at twenty
# on purpose: past that, prose almost always uses digits already, so a larger
# table would be paying for cases that do not occur rather than the one that
# did.
_NUMBER_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "thirteen": "13",
    "fourteen": "14",
    "fifteen": "15",
    "sixteen": "16",
    "seventeen": "17",
    "eighteen": "18",
    "nineteen": "19",
    "twenty": "20",
}
_NUMBER_WORD = re.compile(r"\b(" + "|".join(_NUMBER_WORDS) + r")\b")
_LEADING_NUMBER = re.compile(r"\d[\d,.]*")


def _digitize(text: str) -> str:
    return _NUMBER_WORD.sub(lambda m: _NUMBER_WORDS[m.group(1)], text)


def assert_stats_are_supported(
    scenes: Sequence[Scene], approved_copy: frozenset[str]
) -> Result[None]:
    r"""Every `Stat.value` traces to the brief's own approved copy.

    `approved_copy` is `proof_points` **and** `key_messages` — both are
    "APPROVED copy... arrange and shorten, never invent" per the Brief's own
    docstring and docs/v1/plan/08-intake.md's claims rule; there was never a
    principled reason a Stat could compress one but not the other.
    `constraints` is deliberately excluded even though it is also
    user-supplied: it is the injection corpus's own payload field in two of
    seven fixtures (evals/injection/03-exfiltration.json,
    04-href-hijack.json), because the model reads it as an instruction, not
    copy to cite — treating it as a source a Stat may match against would
    let an injected constraint manufacture its own provenance.

    The weakest of the three, deliberately, and doubly so after CI run
    31079241915: a Stat's 12-character cap forces exactly the reformatting a
    whole-string substring check cannot see through — "processes over 2
    billion spans per day" has to become something like "2B spans/day" to
    fit, and "94 cents of every dollar" has to become "94%". Matching on the
    Stat's own leading number is what the docstring already claimed to do
    ("catches the invented number... does not try to catch paraphrase") —
    this makes the code actually do it, rather than requiring the surrounding
    words to match too. A value with no leading number (rare; the spec's own
    examples — "10x", "2.4M", "<50ms" — are all numeric) falls back to the
    original whole-value check.

    Bounded by "no adjacent digit", not `\b`: `\b` treats a digit and a
    letter as the same word class, so `\b50\b` does not match "50ms" — the
    very case the docstring above already uses as its worked example, and
    the first version of this fix broke it, caught by
    `test_valid_scene_passes` before this ever shipped. `(?<!\d)50(?!\d)`
    is the boundary actually wanted: "4" must not match inside "40" or "24"
    (a digit on either side), but "50" must match inside "50ms" or "68"
    inside "68%" (a letter or symbol on either side is fine). Commas
    stripped from both sides first, so "12,000" and "12000" are the same
    number; the decimal point is not stripped, because "2.4" and "24" are not.
    Spelled-out numbers under twenty are digitized before matching, for the
    same reason — see `_NUMBER_WORDS`.
    """
    haystack = _digitize(" ".join(approved_copy).lower()).replace(",", "")
    invented: list[str] = []
    for s in scenes:
        for b in s.blocks:
            if b.props.type != "stat":
                continue
            value = b.props.value.lower()
            number = _LEADING_NUMBER.search(value)
            if number:
                needle = number.group().replace(",", "")
                pattern = rf"(?<!\d){re.escape(needle)}(?!\d)"
                if not re.search(pattern, haystack):
                    invented.append(b.props.value)
            elif value not in haystack:
                invented.append(b.props.value)
    if invented:
        return err(
            "invalid_input",
            f"stats not traceable to the brief's approved copy: {sorted(set(invented))}",
        )
    return ok(None)
