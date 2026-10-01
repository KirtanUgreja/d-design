"""The engine's public surface. Every caller — the CLI, the worker, the bench —
imports from here and nowhere deeper (docs/coderules/README.md rule 4).

Pure by rule 6: nothing under ``engine`` imports a web framework or reads the
environment. The model client and the clock are injected.
"""

from engine.content import arcs, interview, notes, research, rules, storyline
from engine.llm.openrouter import (
    ModelError,
    Reply,
    Seam,
    Transport,
    parse_fenced,
)
from engine.models import (
    Brief,
    Deck,
    Fact,
    LedgerEntry,
    PlanField,
    Slide,
    SlidePlan,
    Storyline,
)

__all__ = [
    "Brief",
    "Deck",
    "Fact",
    "LedgerEntry",
    "ModelError",
    "PlanField",
    "Reply",
    "Seam",
    "Slide",
    "SlidePlan",
    "Storyline",
    "Transport",
    "arcs",
    "interview",
    "notes",
    "parse_fenced",
    "research",
    "rules",
    "storyline",
]
