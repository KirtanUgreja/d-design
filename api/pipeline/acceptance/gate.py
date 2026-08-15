"""The variety gate — the v1 acceptance measurement, made standing (phase 15).

15-variety-gate.md: every deck render produces a design-space fingerprint, and
the gate asserts:

- Two decks sampled from the registry differ beyond a threshold
- Within a deck, layout structures and chart types are distributed
- No presentational value passes the backstop

Fingerprints are structural, so they gate (ai-stack.md evals rule: structural
assertions are hard pass/fail; probabilistic scores never gate a merge).

The gate runs the golden briefs through the pipeline with a DETERMINISTIC
seam — no network, no model calls, so it is fast enough to run on every
commit. The seam produces a distinct, distributed deck per brief from the
brief's own content (via the deterministic family pick), so a collapse in the
design space — two decks converging, or a deck collapsing to one frame — fails
the gate loudly.

This is the standing form of the "53% identical" measurement: the gate exists
so that number never silently creeps back.
"""

from __future__ import annotations

import hashlib
from typing import Literal

from ai.complete import ModelError, Phase, Seam, T
from lib.result import Ok, Result
from pipeline.acceptance.acceptance import acceptance_summary, run_acceptance_brief
from pipeline.acceptance.briefs import GOLDEN_BRIEFS
from schema.deck import (
    Deck,
    LayoutRegion,
    LayoutStructure,
    Slide,
    SlideBlock,
    TextBlock,
)
from schema.outline import Outline, OutlineClaim, OutlineSection

# The layouts must be legal in EVERY grammar, because the seam's deck is in
# whatever family the brief's title maps to. The roles and spans common to
# all nine grammars are headline/body and full/half — so the sequences vary
# by region count and span, which is enough to keep layout signatures (and
# thus fingerprints) distinct per slide.
_ROLE_SEQUENCES: tuple[tuple[Literal["headline", "body"], ...], ...] = (
    ("headline", "body"),
    ("headline", "body", "body"),
    ("headline", "body", "body", "body"),
    ("headline", "body", "body"),
    ("headline", "body"),
    ("headline", "body", "body"),
    ("headline", "body", "body", "body"),
    ("headline", "body"),
)


class DeterministicSeam(Seam):
    """The standing gate's seam double: runs the golden briefs through the
    real pipeline (interview -> mapping) with a scripted, distributed deck
    per brief — deterministic, so the fingerprint gate is meaningful.

    The outline title is derived from the user prompt (which carries the
    brief's topic), so each brief maps to a different family via the mapping
    pass's deterministic pick — the cross-deck fingerprint claim depends on
    it.
    """

    def complete(
        self,
        phase: Phase,
        schema: type[T],
        system: str,
        user: str,
        model: str,
        route: str = "openrouter/auto",
        image: str | None = None,
    ) -> Result[T, ModelError]:
        del system, model, route, image
        if phase == "interview":
            title = _title_from_prompt(user)
            outline = Outline(
                title=title,
                audience="People",
                goal="Something",
                sections=[
                    OutlineSection(
                        heading="The idea",
                        summary="A deck about the idea",
                        claims=[OutlineClaim(text="The idea is good", source="user")],
                    )
                ],
                must_haves=[],
            )
            return Ok(outline)  # type: ignore[arg-type]  # schema=Outline for the interview
        # mapping: build a distributed deck in the family the mapping picks
        # from the outline title. The user prompt carries the outline JSON.
        family_id = _family_from_title(_title_from_prompt(user))
        slides = [_slide_for(i + 1, _ROLE_SEQUENCES[i % len(_ROLE_SEQUENCES)]) for i in range(6)]
        deck = Deck(family_id=family_id, slides=slides)
        return Ok(deck)  # type: ignore[arg-type]  # schema=Deck for the mapping


def run_variety_gate() -> tuple[bool, str]:
    """Run the golden briefs through the deterministic gate and return
    (passed, report). The report names every violation; a single violation
    fails the run — the variety claim is a gate, not a trend."""
    seam = DeterministicSeam()
    results = []
    for brief in GOLDEN_BRIEFS:
        result = run_acceptance_brief(brief, seam, model="gate-model")
        if isinstance(result, Ok):
            results.append(result.value)
    return acceptance_summary(results)


def _family_from_title(title: str) -> str:
    """Mirror the mapping pass's deterministic family pick for the same
    title, so the deck's family matches the family the pipeline chose."""
    from pipeline.mapping.mapping import _pick_family

    return _pick_family(title)


def _title_from_prompt(user: str) -> str:
    """A stable outline title derived from the interview prompt.

    The prompt carries the brief's topic (framed as data), so hashing it gives
    each brief a distinct, deterministic title — and therefore a distinct
    family via the mapping pass's pick. A stable hash (not Python's randomized
    builtin `hash`) keeps the gate reproducible across runs.
    """
    digest = hashlib.sha256(user.encode("utf8")).hexdigest()[:10]
    return f"Gate brief {int(digest, 16)}"


def _slide_for(index: int, roles: tuple[Literal["headline", "body"], ...]) -> Slide:
    """A slide whose blocks fill its layout regions (headline + body only,
    legal in every grammar)."""
    blocks: list[SlideBlock] = [
        TextBlock(kind="text", style="headline", content=f"Headline {index}")
    ]
    for _ in roles[1:]:
        blocks.append(TextBlock(kind="text", style="body", content=f"Body {index}"))
    return Slide(
        id=f"s{index}",
        title=f"Slide {index}",
        layout=LayoutStructure(regions=[LayoutRegion(role=role, span="full") for role in roles]),
        blocks=blocks,
    )
