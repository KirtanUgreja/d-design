"""api — the v1 pipeline package.

Interview → mapping → slide builder → export. Four plain sequential AI calls
driven by a deterministic orchestrator; no agent framework. Every model call
goes through ai.complete (the seam); the Deck schema in schema/ is the
Pydantic source of truth.
"""
