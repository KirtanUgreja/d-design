"""Slide-builder prompts — the most-tuned prompts in the system.

plan/04: the per-slide prompt is the most-tuned prompt in the system — it is
versioned, eval'd, and repaired. Each slide gets its own call with its own
prompt carrying the design rules, the mapped layout structure, and the family's
grammar.

Phase 10: the builder refines the mapped layout *within* the grammar — it may
adjust spans and emphasis to serve the content, but it never leaves the family's
legal moves. The model emits *what* is on the slide (content blocks filling the
regions) and the layout. It never emits how it looks — no hex, no px, no font,
no duration. The design family's tokens in the renderer are the only styling.

The character budgets are restated here as hard numbers because structured
outputs widely ignore minLength/maxLength (python.md -> "The constraints that
do not survive the trip").
"""

from schema.deck import LayoutStructure
from schema.grammars import FamilyGrammar

# The stable, cacheable system prefix. Never carries user content.
SYSTEM = """You are the slide builder of a deck-generation pipeline.

You build ONE slide at a time. Each slide is a separate call, and you see only
this slide's specification — not the whole deck. This is deliberate: it is how
the deck reads as authored rather than assembled from repeated frames.

Rules:
- Emit the content blocks for this slide, filling its layout regions. The
  design family owns all styling — you never emit a colour, a size, a font, a
  duration, or any presentational value. The schema has no field for one.
- The layout was generated for this slide by the mapping pass. Keep its regions
  and roles; you may refine a span or emphasis within the family's grammar if
  the content earns it. You never invent a role the grammar forbids.
- Every region must be filled by a matching block, and every block must have a
  region: headline regions by the headline, body by body text, stats by stat
  blocks, quote by a quote, media by an image, chart by a chart, aside by an
  eyebrow or caption.
- The headline is first, and there is exactly one. Headline <= 60 characters.
  Body <= 240 characters. A headline that does not fit is a rewrite, not a
  truncation.
- If an image belongs on this slide — background, hero, illustration, or chart
  companion — emit an image block describing the subject in plain language.
  The image will be generated within the design family's visual rules. Never
  include text inside an image.
- Motion intent is a kind of reveal, never a duration.
- The slide serves the deck's through-line: it says the one thing this slide
  is for, and nothing else."""

USER_TEMPLATE = """You are building slide {index} of {total} for the deck "{deck_title}".

The design family: {family_name} ({family_id}).
Family character, as typed text: {family_character}.

The mapped layout for this slide (regions in reading order; keep the roles,
refine spans/emphasis within the grammar if the content earns it):

<layout>
{layout}
</layout>

The family's grammar (the legal space you may compose within):

<grammar>
{grammar}
</grammar>

The content this slide must carry (from the approved outline):

<content>
{content}
</content>

The previous slide's headline was: "{prev_headline}".
The next slide's headline is: "{next_headline}".

Produce the slide now, as JSON matching the schema. The headline must be <= 60
characters and the first block. Every region must be filled and every block
must belong to a region."""


def _format_layout(layout: LayoutStructure) -> str:
    """Serialize the mapped layout structure for the prompt."""
    return layout.model_dump_json(indent=2)


def _format_grammar(grammar: FamilyGrammar) -> str:
    """Serialize the family grammar as the legal space for this slide."""
    lines = [
        f"- legal region roles: {', '.join(grammar.roles)}",
        f"- legal relative spans: {', '.join(grammar.spans)}",
        f"- at most {grammar.max_regions} regions per slide",
    ]
    return "\n".join(lines)


def build_user_prompt(
    index: int,
    total: int,
    deck_title: str,
    family_name: str,
    family_id: str,
    family_character: str,
    layout: LayoutStructure,
    grammar: FamilyGrammar,
    content: str,
    prev_headline: str,
    next_headline: str,
) -> str:
    """Assemble the user-role block for one slide call."""
    return USER_TEMPLATE.format(
        index=index,
        total=total,
        deck_title=deck_title,
        family_name=family_name,
        family_id=family_id,
        family_character=family_character,
        layout=_format_layout(layout),
        grammar=_format_grammar(grammar),
        content=content,
        prev_headline=prev_headline,
        next_headline=next_headline,
    )
