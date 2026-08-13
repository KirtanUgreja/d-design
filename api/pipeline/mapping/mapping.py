"""The mapping orchestrator — a plain deterministic function.

Turns the approved Outline into a per-slide Deck via one schema-validated
model call through the seam. The Deck is validated at the boundary, backstop-
checked, and distribution-checked before it is trusted — a mapped deck that
collapses onto one frame is rejected even if the schema is happy.
"""

from __future__ import annotations

from ai.complete import ModelError, Seam
from lib.result import Err, Result, err, ok
from pipeline.mapping import prompts
from pipeline.mapping.distribution import distribution_violation
from schema.archetypes import LAYOUT_ARCHETYPES, archetype_by_id
from schema.deck import Deck
from schema.design_families import family_by_id
from schema.no_style import assert_no_presentational_values
from schema.outline import Outline


def run_mapping(
    outline: Outline,
    seam: Seam,
    model: str,
    family_id: str | None = None,
) -> Result[Deck, ModelError]:
    """Run the mapping pass: Outline -> schema-validated Deck.

    ``family_id`` selects the per-deck design system; it defaults to a
    deterministic pick so the same outline maps reproducibly.
    """
    if family_id is None:
        # Deterministic family selection: hash the outline title so the same
        # outline always samples the same family (reproducible acceptance runs)
        # while different outlines sample different families.
        family_id = _pick_family(outline.title)

    family = family_by_id(family_id)
    if family is None:
        return err(ModelError("invalid", f"unknown family: {family_id}"))

    user = prompts.build_user_prompt(
        outline=outline,
        family_id=family.id,
        family_name=family.name,
        archetypes=LAYOUT_ARCHETYPES,
    )

    result = seam.complete(
        phase="mapping",
        schema=Deck,
        system=prompts.SYSTEM,
        user=user,
        model=model,
    )

    if isinstance(result, Err):
        return result

    deck = result.value

    # Three checks, in order: the schema (done in the seam), the backstop
    # (a presentational value is a schema gap — bug), and the distribution
    # (the within-deck variety claim). The distribution check is the falsifier
    # for the core bet: a collapsed deck fails even though it is valid JSON.
    assert_no_presentational_values(deck.model_dump())

    # Every layout archetype the model chose must be one the catalogue defines.
    for slide in deck.slides:
        if archetype_by_id(slide.layout_archetype) is None:
            return err(
                ModelError(
                    "invalid",
                    f"unknown layout archetype: {slide.layout_archetype}",
                )
            )

    violation = distribution_violation(deck)
    if violation is not None:
        return err(ModelError("invalid", f"layout distribution: {violation}"))

    return ok(deck)


def _pick_family(title: str) -> str:
    """Deterministic family pick from the title, so a given outline maps
    reproducibly and different outlines differ."""
    from schema.design_families import DESIGN_FAMILIES

    total = 0
    for ch in title:
        total += ord(ch)
    return DESIGN_FAMILIES[total % len(DESIGN_FAMILIES)].id
