"""Slide-builder prompts — the most-tuned prompts in the system.

plan/04: the per-slide prompt is the most-tuned prompt in the system — it is
versioned, eval'd, and repaired. Each slide gets its own call with its own
prompt carrying the design rules, the layout archetype, and the chart shape.

The model emits *what* is on the slide (content blocks) and *which archetype*
it is building for. It never emits how it looks — no hex, no px, no font, no
duration. The design family's tokens in the renderer are the only styling.

The character budgets are restated here as hard numbers because structured
outputs widely ignore minLength/maxLength (python.md -> "The constraints that
do not survive the trip").
"""

# The stable, cacheable system prefix. Never carries user content.
SYSTEM = """You are the slide builder of a deck-generation pipeline.

You build ONE slide at a time. Each slide is a separate call, and you see only
this slide's specification — not the whole deck. This is deliberate: it is how
the deck reads as authored rather than assembled from repeated frames.

Rules:
- Emit only the content blocks for this slide and its layout archetype. The
  design family owns all styling — you never emit a colour, a size, a font, a
  duration, or any presentational value. The schema has no field for one.
- The headline is first, and there is exactly one. Headline <= 60 characters.
  Body <= 240 characters. A headline that does not fit is a rewrite, not a
  truncation.
- The layout archetype must be exactly the one you were given. You pick the
  variant, but you do not invent a new layout.
- If a chart belongs on this slide, spec the chart (what it says). The
  renderer owns how it looks.
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

The layout archetype for this slide: {archetype_id} — {archetype_intent}.
Choose one of these variants: {variants}.

The content this slide must carry (from the approved outline):

<content>
{content}
</content>

The previous slide's headline was: "{prev_headline}".
The next slide's headline is: "{next_headline}".

Produce the slide now, as JSON matching the schema. The headline must be <= 60
characters and the first block. You may use an image block or a chart block if
the content earns it — a data slide wants a chart, a product slide may want a
hero image. Do not force either."""


def build_user_prompt(
    index: int,
    total: int,
    deck_title: str,
    family_name: str,
    family_id: str,
    family_character: str,
    archetype_id: str,
    archetype_intent: str,
    variants: list[str],
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
        archetype_id=archetype_id,
        archetype_intent=archetype_intent,
        variants=", ".join(variants),
        content=content,
        prev_headline=prev_headline,
        next_headline=next_headline,
    )
