"""The slide builder — one model call per slide.

plan/04: the core claim. Each slide in the mapped Deck gets its own model call
with its own prompt (the slide spec, the design family, the design rules) and
returns a schema-validated slide. Because each slide is a separate call with a
distinct spec, the model cannot collapse the whole deck into one frame. The
design family provides the constant; the per-slide spec provides the variation.

This is where the "beautiful" happens — the craft budget. The per-slide prompt
is the most-tuned in the system, and the seam's single repair retry is what
makes a malformed slide cheap to fix rather than fatal.

Images: an image block is a seam action. The builder generates the image
within the design family's visual rules and stores it on the slide as a data
URI. v1 stores it on a parallel map so the Deck schema stays presentational-
free; the exporter (phase 05) inlines it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ai.complete import ModelError, Seam
from ai.images import ImageSeam
from lib.result import Err, Result, err, ok
from pipeline.slide_builder import prompts
from schema.deck import Deck, ImageBlock, Slide
from schema.design_families import family_by_id
from schema.no_style import assert_no_presentational_values


@dataclass
class BuildResult:
    """The built deck plus the generated image assets.

    The Deck schema has no field for a URL or a data URI (an image block
    expresses what the image is, not where it lives). The generated assets are
    carried beside the deck, keyed by slide id, and inlined by the exporter.
    """

    deck: Deck
    images: dict[str, str] = field(default_factory=dict)


def _slide_context(deck: Deck, index: int) -> tuple[str, str]:
    """The previous and next headlines, for narrative continuity."""
    prev = deck.slides[index - 1].title if index > 0 else ""
    next_ = deck.slides[index + 1].title if index < len(deck.slides) - 1 else ""
    return prev, next_


def _content_for_slide(slide: Slide) -> str:
    """Serialize the slide's mapped content for the prompt. This is the spec
    the model refines into final copy."""
    return slide.model_dump_json(indent=2)


def run_build(
    deck: Deck,
    seam: Seam,
    image_seam: ImageSeam,
    model: str,
    image_model: str = "openai/dall-e-3",
) -> Result[BuildResult, ModelError]:
    """Build every slide, one model call each, in order.

    A slide that fails after the seam's repair returns a typed error; the
    slides already built are not discarded (spec.md -> "Failure at slide 6 of
    8 keeps the five").
    """
    family = family_by_id(deck.family_id)
    if family is None:
        return err(ModelError("invalid", f"unknown family: {deck.family_id}"))

    # The deck's reference title for the prompts: the opener's title carries
    # the narrative the deck is named by.
    deck_title = deck.slides[0].title if deck.slides else "the deck"

    images: dict[str, str] = {}
    built: list[Slide] = []

    for i, slide in enumerate(deck.slides):
        prev_headline, next_headline = _slide_context(deck, i)

        user = prompts.build_user_prompt(
            index=i + 1,
            total=len(deck.slides),
            deck_title=deck_title,
            family_name=family.name,
            family_id=family.id,
            family_character=", ".join(family.axis),
            archetype_id=slide.layout_archetype,
            archetype_intent=_archetype_intent(slide.layout_archetype),
            variants=_archetype_variants(slide.layout_archetype),
            content=_content_for_slide(slide),
            prev_headline=prev_headline,
            next_headline=next_headline,
        )

        result = seam.complete(
            phase="slide",
            schema=Slide,
            system=prompts.SYSTEM,
            user=user,
            model=model,
        )
        if isinstance(result, Err):
            return result

        built_slide = result.value
        # The schema is the first line; the backstop is the second.
        assert_no_presentational_values(built_slide.model_dump())

        # Preserve the slide id from the mapping (the deck's slide ids are the
        # stable keys the exporter and review loop use).
        built_slide = built_slide.model_copy(update={"id": slide.id})

        # Generate images for any image blocks, within the family's visual
        # rules. An image failure fails the deck — a slide with a grey
        # rectangle is a visible defect, better surfaced now than at review.
        for block in built_slide.blocks:
            if isinstance(block, ImageBlock):
                image_result = image_seam.generate(
                    subject=block.subject,
                    visual_rules=", ".join(family.axis),
                    model=image_model,
                )
                if isinstance(image_result, Err):
                    return err(
                        ModelError(
                            "invalid",
                            f"image generation for slide {slide.id} failed: "
                            f"{image_result.error.detail}",
                        )
                    )
                images[slide.id] = image_result.value

        built.append(built_slide)

    return ok(BuildResult(deck=deck.model_copy(update={"slides": built}), images=images))


def _archetype_intent(archetype_id: str) -> str:
    from schema.archetypes import archetype_by_id

    a = archetype_by_id(archetype_id)
    return a.intent if a else archetype_id


def _archetype_variants(archetype_id: str) -> list[str]:
    from schema.archetypes import archetype_by_id

    a = archetype_by_id(archetype_id)
    return list(a.variants) if a else []
