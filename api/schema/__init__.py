"""The Pydantic source of truth: Deck, Outline, Brief, DesignFamily, and the
layout-archetype catalogue.

The Deck schema is the boundary between the pipeline and the renderer. It
carries no presentational values — no hex, no px, no font name, no duration —
which is enforced structurally by the schema and by a runtime backstop.
"""
