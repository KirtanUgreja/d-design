"""Mapping prompts — versioned artifacts (ai-stack.md: "Prompts are versioned").

The mapping pass turns the approved Outline into a per-slide Deck. It generates
each slide's layout within the family's grammar (phase 10) — the model composes
a LayoutStructure from the grammar's legal roles, spans and density — and it
owns the through-line: the structural opener, the narrative arc, the CTA
placement.

The grammar is injected so the model composes within it and never invents a
role or span the family does not allow. This is the structured-diversity
finding from findings.md: constrain the discrete space, let the model fill it.
"""

from schema.deck import Slide
from schema.grammars import FamilyGrammar
from schema.outline import Outline

# The stable, cacheable system prefix. It never carries user content.
SYSTEM = """You are the mapping pass of a deck-generation pipeline.

You take an approved outline and turn it into a precise per-slide specification
— a Deck. Each slide gets a generated layout (an ordered set of regions, each
with a semantic role, a relative span, and an emphasis) and the content blocks
that fill it. You do not pick from a layout catalogue: you COMPOSE a layout
within the family's grammar, which defines the legal roles, spans and density.

Rules:
- Every claim in the outline becomes content in a slide. Nothing is dropped,
  nothing is invented. If the outline does not support a fact, do not assert it.
- The layout is generated, not copied: each slide's region sequence should
  differ from the ones around it. The grammar's signatures are starting points,
  not the whole space — compose new legal combinations where they serve the
  content.
- DISTRIBUTE the layouts. No layout may appear more than twice in a row, and
  a deck of N slides must use at least max(4, N-1) distinct layout signatures
  overall (5 slides -> at least 4 distinct; 10+ -> at least 5-6). Repeating
  the same two-region skeleton is a failure even if no run exceeds two.
  Variety within the deck is the point; cohesion comes from the design family,
  which is constant, and from the grammar, which bounds every slide to the
  same space.
- The first slide leads with a FULL-width region (headline or media) — it
  claims the topic. The last slide carries the CTA, on a full or prominent
  region. Section breaks appear where the outline's narrative turns.
- Every region you declare must be filled by a matching block, and every block
  must have a region: headline regions are filled by the headline, body regions
  by body text, stats by stat blocks, quote by a quote, media by an image,
  chart by a chart, aside by an eyebrow or caption.
- Each slide has exactly one headline, and it is the first block.
- The CTA appears once, on the closer (or the slide that earns it), and its
  destination must be one the user supplied or a plain https URL.
- Motion intent is a kind of reveal (reveal/emphasize/transition/none), never
  a duration or a style. The design family owns pacing.
- Character budgets: headline <= 60 characters, body <= 240. A headline longer
  than that is a rewrite, not a truncation.
- The deck reads as one authored thing: sections follow a narrative arc, not a
  list. The through-line is yours to keep."""

# The user block: the approved outline, the design family, the family's
# grammar, and (when a kit is mapped) the brand's semantic roles. The outline
# is trusted (it passed the human gate) but is still passed as data. The brand
# block names roles, never values — the renderer binds the hex, so the model
# never carries a presentational value (no_style backstop).
USER_TEMPLATE = """The approved outline:

<outline>
{outline}
</outline>

The design family for this deck: {family_id} — {family_name}.

The family's layout grammar (compose within it; never use a role or span that
is not listed):

{grammar}

{brand_block}
Produce the Deck now, as JSON matching the schema. Respect the distribution
rule above. Every claim in the outline must appear in the deck."""


def _format_brand(roles: list[str]) -> str:
    """The brand block: the kit's mapped semantic roles as names, not values.

    The model composes within these roles (a headline in the accent, body on
    paper); the renderer owns the actual token values.
    """
    return (
        "The brand kit maps to these semantic roles (values are applied by the "
        "renderer, never chosen by you): " + ", ".join(roles) + "."
    )


def build_user_prompt(
    outline: Outline,
    family_id: str,
    family_name: str,
    grammar: FamilyGrammar,
    brand_roles: list[str] | None = None,
) -> str:
    """Assemble the user-role block for the mapping call."""
    brand_block = _format_brand(brand_roles) if brand_roles else ""
    return USER_TEMPLATE.format(
        outline=_format_outline(outline),
        family_id=family_id,
        family_name=family_name,
        grammar=_format_grammar(grammar),
        brand_block=brand_block,
    )


def _format_outline(outline: Outline) -> str:
    """Serialize the approved outline for the prompt. Trusted data, shown as
    data."""
    return outline.model_dump_json(indent=2)


def _format_grammar(grammar: FamilyGrammar) -> str:
    lines = [
        f"- legal region roles: {', '.join(grammar.roles)}",
        f"- legal relative spans: {', '.join(grammar.spans)}",
        f"- at most {grammar.max_regions} regions per slide",
        "- canonical signatures (starting points, not the whole space):",
    ]
    for sig in grammar.signatures:
        lines.append(f"  - {', '.join(sig)}")
    return "\n".join(lines)


def slide_fits_grammar(slide: Slide, grammar: FamilyGrammar) -> bool:
    """A structural backstop for a mapped slide: every region is legal in the
    grammar. The Deck validator is the authority; this keeps a mapping pass
    from relying on it as the only line."""
    roles = {r.role for r in slide.layout.regions}
    spans = {r.span for r in slide.layout.regions}
    return (
        roles.issubset(set(grammar.roles))
        and spans.issubset(set(grammar.spans))
        and len(slide.layout.regions) <= grammar.max_regions
    )
