"""The engine's public surface. Every caller — the CLI, the worker, the bench —
imports from here and nowhere deeper (docs/coderules/README.md rule 4).

Pure by rule 6: nothing under ``engine`` imports a web framework or reads the
environment. The model client and the clock are injected.
"""

from engine import pipeline
from engine.compose.author import Composed
from engine.compose.edit import set_field
from engine.content import arcs, interview, notes, research, rules, storyline
from engine.content.interview import Question
from engine.design.sampler import look_for, recolour
from engine.design.theme import build as build_theme
from engine.export import pdf
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
from engine.pipeline import Built, Kept

__all__ = [
    "Brief",
    "Built",
    "Composed",
    "Deck",
    "Fact",
    "Kept",
    "LedgerEntry",
    "ModelError",
    "PlanField",
    "Question",
    "Reply",
    "Seam",
    "Slide",
    "SlidePlan",
    "Storyline",
    "Transport",
    "arcs",
    "build_theme",
    "interview",
    "look_for",
    "notes",
    "parse_fenced",
    "pdf",
    "pipeline",
    "recolour",
    "research",
    "rules",
    "set_field",
    "storyline",
]
