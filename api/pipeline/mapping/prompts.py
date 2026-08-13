"""Mapping prompts — versioned artifacts (ai-stack.md: "Prompts are versioned").

The mapping pass turns the approved Outline into a per-slide Deck. It assigns
each slide a layout archetype from the design family's catalogue, distributed
so the deck does not collapse onto one frame, and it owns the through-line —
the narrative arc, the section structure, the CTA placement.

The prompt is where the layout-grammar lives (v1 uses a curated catalogue, not
per-slide layout generation — that is v2). The catalogue is injected so the
model picks from it by id and never invents a shape.
"""

from schema.archetypes import LayoutArchetype
from schema.outline import Outline

# The stable, cacheable system prefix. It never carries user content.
SYSTEM = """You are the mapping pass of a deck-generation pipeline.

You take an approved outline and turn it into a precise per-slide specification
— a Deck. Each slide gets a layout archetype, content blocks, and a motion
intent. You do not design new layouts: you pick from the catalogue you are
given, by id.

Rules:
- Every claim in the outline becomes content in a slide. Nothing is dropped,
  nothing is invented. If the outline does not support a fact, do not assert it.
- DISTRIBUTE the layout archetypes. A deck must not use the same archetype more
  than twice in a row, and across a 10+ slide deck use at least 5-6 distinct
  archetypes. Variety within the deck is the point; cohesion comes from the
  design family, which is constant.
- The first slide is an opener and the last is a closer. Section breaks appear
  where the outline's narrative turns.
- Each slide has exactly one headline, and it is the first block.
- The CTA appears once, on the closer (or the slide that earns it), and its
  destination must be one the user supplied or a plain https URL.
- Motion intent is a kind of reveal (reveal/emphasize/transition/none), never
  a duration or a style. The design family owns pacing.
- Character budgets: headline <= 60 characters, body <= 240. A headline longer
  than that is a rewrite, not a truncation.
- The deck reads as one authored thing: sections follow a narrative arc, not a
  list. The through-line is yours to keep."""

# The user block: the approved outline, the design family, and the archetype
# catalogue. The outline is trusted (it passed the human gate) but is still
# passed as data.
USER_TEMPLATE = """The approved outline:

<outline>
{outline}
</outline>

The design family for this deck: {family_id} — {family_name}.

The layout-archetype catalogue (pick by id, never invent):

{archetypes}

Produce the Deck now, as JSON matching the schema. Respect the distribution
rule above. Every claim in the outline must appear in the deck."""


def _format_outline(outline: Outline) -> str:
    """Serialize the approved outline for the prompt. Trusted data, shown as
    data."""
    return outline.model_dump_json(indent=2)


def _format_archetypes(archetypes: tuple[LayoutArchetype, ...]) -> str:
    lines = []
    for a in archetypes:
        variants = ", ".join(a.variants)
        lines.append(f"- {a.id} — {a.name}: {a.intent} (variants: {variants})")
    return "\n".join(lines)


def build_user_prompt(
    outline: Outline,
    family_id: str,
    family_name: str,
    archetypes: tuple[LayoutArchetype, ...],
) -> str:
    """Assemble the user-role block for the mapping call."""
    return USER_TEMPLATE.format(
        outline=_format_outline(outline),
        family_id=family_id,
        family_name=family_name,
        archetypes=_format_archetypes(archetypes),
    )
