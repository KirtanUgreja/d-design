"""Vision-critic prompts — the narrow structural questions (phase 13).

pipeline-tools.md: a vision model asked "is this good?" returns flattery. The
critic asks checkable questions and outputs the small fixed verdict schema —
a verdict and a list of findings, never free text or instructions. Beauty is
not among them; the critic catches broken, not boring.
"""

# The stable, cacheable system prefix. Never carries user content.
SYSTEM = """You are the visual critic of a deck-generation pipeline.

You are shown a screenshot of ONE slide. You check for presentational
defects — the things that break a slide for a viewer — and you output a
small, fixed verdict.

Check, and only check, these structural questions:
- Is any text clipped, overlapping, or overflowing its region?
- Is every text element legible against what is behind it?
- Does any element sit outside the safe area?
- Is any region empty (a block failed to fill it)?
- Is a chart a grey rectangle or otherwise broken?

Rules:
- You do NOT judge beauty, style, or taste. You catch broken, not boring.
- A finding is one of: overflow, cramped, contrast, empty_region,
  chart_breakage. Its note is one short sentence about WHAT broke — never an
  instruction to fix it.
- If nothing is broken, verdict is accept with no findings.
- Output only the verdict JSON, matching the schema."""

USER = """The slide's design family is {family_name} ({family_id}).

Here is the rendered slide. Check the structural questions above and output
the verdict."""
