"""Mapping — the second pipeline phase.

Turns the approved Outline into a per-slide Deck via one schema-validated
model call. The Deck is the boundary between the pipeline and the renderer:
what the mapping produces and the slide builder consumes.
"""

from pipeline.mapping.mapping import run_mapping

__all__ = ["run_mapping"]
