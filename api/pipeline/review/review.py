"""The visual review loop — plane 07.

plan/07: the review is human, not an AI judge. A person looks at the exported
deck in the browser and can send specific slides back for regeneration with
written feedback. The repair is a per-slide re-call — cheap and bounded.

This module is the deterministic half of that loop: given a slide, its deck
context, and written feedback, it makes one schema-validated model call that
regenerates the slide honoring the feedback. The human half is the review
screen (v1: the exported file + the CLI review command).
"""

from __future__ import annotations

from ai.complete import ModelError, Seam
from lib.result import Err, Result, err, ok
from pipeline.slide_builder import prompts as slide_prompts
from schema.deck import Deck, Slide
from schema.design_families import family_by_id
from schema.no_style import assert_no_presentational_values

# The system prompt for a revision: the feedback is authoritative, the slide's
# intent is preserved, the design family still owns the look.
REVISION_SYSTEM = """You are revising ONE slide of a deck in response to a reviewer's feedback.

The reviewer is a human who looked at the rendered slide. Their feedback is
the most important input you have: honor it first. If they say a headline is
too long, shorten it. If they say an image is off-message, describe a better
one. If they say the emphasis is wrong, change the motion intent.

Rules:
- Keep the slide's role in the deck: the layout archetype stays, the content
  stays true to the outline. You are revising, not replacing.
- You still never emit a presentational value — no hex, no size, no font, no
  duration. The schema has no field for one.
- Headline <= 60 characters and first. Body <= 240.
- If the reviewer's feedback conflicts with the outline, the outline wins —
  the reviewer is fixing presentation, not facts."""


def revise_slide(
    deck: Deck,
    slide_index: int,
    feedback: str,
    seam: Seam,
    model: str,
) -> Result[Slide, ModelError]:
    """Regenerate one slide in response to written feedback.

    ``slide_index`` is the slide's position in the deck (the review is
    slide-by-slide). The revision is one schema-validated call through the
    seam, backstop-checked, with the slide's id preserved.
    """
    if slide_index < 0 or slide_index >= len(deck.slides):
        return err(ModelError("invalid", f"slide index {slide_index} out of range"))

    slide = deck.slides[slide_index]
    family = family_by_id(deck.family_id)
    if family is None:
        return err(ModelError("invalid", f"unknown family: {deck.family_id}"))

    prev_title = deck.slides[slide_index - 1].title if slide_index > 0 else ""
    next_title = deck.slides[slide_index + 1].title if slide_index < len(deck.slides) - 1 else ""

    user = slide_prompts.build_user_prompt(
        index=slide_index + 1,
        total=len(deck.slides),
        deck_title=deck.slides[0].title if deck.slides else "the deck",
        family_name=family.name,
        family_id=family.id,
        family_character=", ".join(family.axis),
        archetype_id=slide.layout_archetype,
        archetype_intent=_intent(slide.layout_archetype),
        variants=_variants(slide.layout_archetype),
        content=slide.model_dump_json(indent=2),
        prev_headline=prev_title,
        next_headline=next_title,
    )
    user += f"\n\nReviewer feedback (honor this):\n{feedback}"

    result = seam.complete(
        phase="critic",
        schema=Slide,
        system=REVISION_SYSTEM,
        user=user,
        model=model,
    )
    if isinstance(result, Err):
        return result

    revised = result.value
    assert_no_presentational_values(revised.model_dump())
    return ok(revised.model_copy(update={"id": slide.id}))


def _intent(archetype_id: str) -> str:
    from schema.archetypes import archetype_by_id

    a = archetype_by_id(archetype_id)
    return a.intent if a else archetype_id


def _variants(archetype_id: str) -> list[str]:
    from schema.archetypes import archetype_by_id

    a = archetype_by_id(archetype_id)
    return list(a.variants) if a else []
