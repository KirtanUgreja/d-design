"""The Pydantic source of truth: Deck, Outline, Brief, DesignFamily, and the
layout-grammar registry.

The Deck schema is the boundary between the pipeline and the renderer. It
carries no presentational values — no hex, no px, no font name, no duration —
which is enforced structurally by the schema and by a runtime backstop. A
slide's layout is a generated structure constrained by the family's grammar
(v2, phase 10), not a pick from a curated catalogue (v1).
"""
