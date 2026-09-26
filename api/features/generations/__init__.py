"""generations — the cost and reliability spine (v3).

One row per pipeline stage, recorded by the generation routes. The table is the
one `backend.md:214` specifies: phase, model, repair, latency, owner — and
nothing that could reconstruct a brief or a deck.

It is a feature rather than a helper on `generation` because it owns a table,
and its public surface is one function.
"""

from features.generations.generations_data import record_generation

__all__ = ["record_generation"]
