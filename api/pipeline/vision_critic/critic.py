"""The vision critic — a bounded loop, never an agent (phase 13).

Given a rendered slide screenshot, a vision model answers narrow structural
questions and outputs the small fixed verdict schema. A `revise` verdict
triggers at most one corrective revision, then the loop stops.

The bound is a literal, `MAX_REVISIONS = 1` — there is no `while`. This is
the ai-stack.md test: *can the model change how many times this runs?* No.
The moment it becomes a loop the model negotiates, it is an agent and the
no-framework rule is broken.

The critic is a rate, not a gate (13-vision-critic.md): it flags and
suggests; it does not block. The schema parse (CriticVerdict) is the
injection containment — findings are structural kinds, never instructions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ai.complete import ModelError, Seam
from lib.result import Err, Result, err, ok
from pipeline.review.review import revise_slide
from pipeline.vision_critic import prompts
from schema.critic import CriticFinding, CriticVerdict
from schema.deck import Deck, Slide
from schema.design_families import family_by_id
from schema.no_style import assert_no_presentational_values

# The documented bound: one corrective pass, then accept and move on. A
# literal, not a budget the model negotiates (ai-stack.md).
MAX_REVISIONS = 1


@dataclass(frozen=True)
class CriticOutcome:
    """The critic's answer for one slide: whether it revised, and why."""

    revised: bool
    deck: Deck
    findings: list[CriticFinding] = field(default_factory=list)


def run_critic(
    deck: Deck,
    slide_index: int,
    screenshot: str,
    seam: Seam,
    model: str,
    critic_model: str,
) -> Result[CriticOutcome, ModelError]:
    """Run the vision critic on one slide: screenshot -> verdict -> at most one
    revision.

    ``screenshot`` is a data URI of the rendered slide (the render service
    produces it in the real flow; tests inject a fixture). ``model`` is the
    text model used for a revision; ``critic_model`` is the vision model the
    screenshot is shown to — per-eval pick (ai-stack.md: vision is not scarce).
    """
    if slide_index < 0 or slide_index >= len(deck.slides):
        return err(ModelError("invalid", f"slide index {slide_index} out of range"))

    family = family_by_id(deck.family_id)
    if family is None:
        return err(ModelError("invalid", f"unknown family: {deck.family_id}"))

    user = prompts.USER.format(
        family_name=family.name,
        family_id=family.id,
    )

    verdict_result = seam.complete(
        phase="critic",
        schema=CriticVerdict,
        system=prompts.SYSTEM,
        user=user,
        model=critic_model,
        image=screenshot,
    )
    if isinstance(verdict_result, Err):
        return verdict_result

    verdict = verdict_result.value
    if verdict.verdict == "accept":
        return ok(CriticOutcome(revised=False, deck=deck, findings=[]))

    # The bounded loop: at most one corrective pass, then accept and move on.
    # The findings are the feedback; the reviewer's copy stays true to the
    # outline (the review phase's contract).
    feedback = _findings_summary(verdict.findings)
    revised_result = revise_slide(deck, slide_index, feedback, seam, model=model)
    if isinstance(revised_result, Err):
        return revised_result

    revised_deck = deck.model_copy(
        update={"slides": _replace_slide(deck, slide_index, revised_result.value)}
    )
    # The revision is a generated tree like any other — backstop-checked.
    assert_no_presentational_values(revised_deck.model_dump())

    return ok(
        CriticOutcome(
            revised=True,
            deck=revised_deck,
            findings=verdict.findings,
        )
    )


def _findings_summary(findings: list[CriticFinding]) -> str:
    """The findings as written feedback for the revision pass. Structural
    defect descriptions, never instructions — the revision model decides the
    fix within the family's grammar."""
    if not findings:
        return "the critic flagged this slide for revision (no specific finding listed)."
    lines = []
    for f in findings:
        lines.append(f"- {f.kind} ({f.severity}): {f.note}")
    return "the visual critic flagged:\n" + "\n".join(lines)


def _replace_slide(deck: Deck, index: int, slide: Slide) -> list[Slide]:
    """Swap one slide in the deck, preserving the rest."""
    slides = list(deck.slides)
    slides[index] = slide
    return slides
