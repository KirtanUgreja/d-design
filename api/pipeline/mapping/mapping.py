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
from pipeline.mapping.brand_tokens import BrandFacts, map_brand_to_family
from pipeline.mapping.distribution import distribution_violation
from schema.deck import Deck
from schema.design_families import family_by_id
from schema.grammars import FamilyGrammar, grammar_for_family
from schema.no_style import assert_no_presentational_values
from schema.outline import Outline


def run_mapping(
    outline: Outline,
    seam: Seam,
    model: str,
    family_id: str | None = None,
    brand_facts: BrandFacts | None = None,
) -> Result[Deck, ModelError]:
    """Run the mapping pass: Outline -> schema-validated Deck.

    ``family_id`` selects the per-deck design system; it defaults to a
    deterministic pick so the same outline maps reproducibly. ``brand_facts``
    are the extracted kit facts (a logo's dominant color, etc.); they are
    mapped to the family's semantic roles with contrast enforced, and the
    model composes within those roles — it never sees a value.
    """
    if family_id is None:
        # Deterministic family selection: hash the outline title so the same
        # outline always samples the same family (reproducible acceptance runs)
        # while different outlines sample different families.
        family_id = _pick_family(outline.title)

    family = family_by_id(family_id)
    if family is None:
        return err(ModelError("invalid", f"unknown family: {family_id}"))

    grammar = grammar_for_family(family)
    if grammar is None:
        return err(
            ModelError(
                "invalid",
                f"family '{family_id}' has no grammar for layout character '{family.axis[5]}'",
            )
        )

    brand_roles: list[str] | None = None
    if brand_facts is not None:
        tokens = map_brand_to_family(
            brand_facts.accent_hex, brand_facts.paper_hex, brand_facts.ink_hex
        )
        brand_roles = list(tokens.overrides().keys())

    user = prompts.build_user_prompt(
        outline=outline,
        family_id=family.id,
        family_name=family.name,
        grammar=grammar,
        brand_roles=brand_roles,
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
    #
    # The live run (phase 20-era) showed the model reliably collapses onto a
    # repeated layout, and the gate returned a hard Err with no recovery. The
    # schema gets one repair inside the seam; the semantic checks here get the
    # same bounded treatment — one corrective call with the violation text,
    # then fail visibly (patterns.md rule 6: bounded loops stay bounded).
    issue = _first_semantic_issue(deck, grammar)
    if issue is not None:
        repair = seam.complete(
            phase="mapping",
            schema=Deck,
            system=prompts.SYSTEM,
            user=user
            + (
                "\n\nYour previous response passed the schema but failed a "
                f"design check: {issue}. Return a revised Deck that fixes "
                "this — vary the layouts, keep every block in a region."
            ),
            model=model,
        )
        if isinstance(repair, Err):
            return repair
        deck = repair.value

    assert_no_presentational_values(deck.model_dump())

    # The Deck validator enforces grammar-legality; this second line keeps the
    # mapping pass from trusting it as the only gate (a mapped deck that names
    # a role the grammar forbids must fail here even if the schema were looser).
    for slide in deck.slides:
        if not prompts.slide_fits_grammar(slide, grammar):
            return err(
                ModelError(
                    "invalid",
                    f"slide '{slide.id}' layout is not legal in grammar "
                    f"'{grammar.layout_character}'",
                )
            )

    violation = distribution_violation(deck)
    if violation is not None:
        return err(ModelError("invalid", f"layout distribution: {violation}"))

    return ok(deck)


def _first_semantic_issue(deck: Deck, grammar: FamilyGrammar) -> str | None:
    """The first post-schema design issue: grammar-legality or distribution.
    Returns a corrective message for the repair call, or None when clean."""
    for slide in deck.slides:
        if not prompts.slide_fits_grammar(slide, grammar):
            return f"slide '{slide.id}' layout is not legal in the family grammar"
    return distribution_violation(deck)


def _pick_family(title: str) -> str:
    """Deterministic family pick from the title, so a given outline maps
    reproducibly and different outlines differ."""
    from schema.design_families import DESIGN_FAMILIES

    total = 0
    for ch in title:
        total += ord(ch)
    return DESIGN_FAMILIES[total % len(DESIGN_FAMILIES)].id
