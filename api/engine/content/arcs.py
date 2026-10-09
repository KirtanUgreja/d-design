"""The five arcs and the evidence each needs (docs/v4/content.md -> Arcs).

Research queries come from an arc's evidence needs, not from the topic alone.
"""

from __future__ import annotations

import re

from engine.models import DeckType

ARCS: dict[str, tuple[str, ...]] = {
    "pitch": (
        "hook",
        "problem",
        "why now",
        "solution",
        "how it works",
        "traction",
        "market",
        "business model",
        "competition",
        "team",
        "the ask",
    ),
    "sales": (
        "their pain, in their words",
        "the cost of doing nothing",
        "the new way",
        "how it works",
        "proof",
        "the offer",
        "the next step",
    ),
    "launch": (
        "the change",
        "who it is for",
        "what is new",
        "proof or demo",
        "availability",
        "call to action",
    ),
    "investor_update": (
        "the headline number",
        "KPIs vs plan",
        "wins",
        "misses and why",
        "burn and runway",
        "asks",
    ),
    "partnership": (
        "the shared opportunity",
        "what each side brings",
        "the model",
        "the plan",
        "the ask",
    ),
    # A college, course or hackathon project (owner, 2026-10-09).
    "project": (
        "title and team",
        "problem statement",
        "objectives",
        "existing solutions and their gaps",
        "proposed solution",
        "architecture",
        "tech stack",
        "user flow",
        "demo",
        "results",
        "future scope",
        "thank you",
    ),
}

# What an outside source can prove for each deck type. The user's own numbers
# (traction, pipeline, KPIs) come from the brief, never the web.
# Every arc also asks for one series — the same measure across years or items —
# because a chart needs one (phase 37), and research seldom returned one.
SERIES = "one measure over several years or across several items, with every value sourced"
EVIDENCE: dict[str, tuple[str, ...]] = {
    "pitch": (
        "the cost of the problem today",
        "the market size",
        "why-now signals",
        "the competitive landscape",
        SERIES,
    ),
    "sales": ("the cost of the status quo in the buyer's industry", "industry benchmarks", SERIES),
    "launch": (
        "how often the problem occurs for this audience, and what it costs them",
        "adoption of the category",
        SERIES,
    ),
    "investor_update": ("market conditions relevant to the period", SERIES),
    "partnership": ("the size of the shared opportunity", "the partner's market position", SERIES),
    "project": (
        "how common or costly the problem is for the people the project serves",
        "the existing tools or approaches and where they fall short",
        SERIES,
    ),
}


# Words in a brief left on "auto" that name its arc; first match wins.
# ponytail: keywords, not a model call. Upgrade: let the interview call name the type.
_NAMED = (
    (
        "investor_update",
        re.compile(r"\b(investor|board|monthly|quarterly) update|\bQ[1-4]\b", re.I),
    ),
    (
        "project",
        re.compile(
            r"\b(college|university|semester|final.year|capstone|hackathon|academic|"
            r"course project|mini project|major project|my project|our project|viva)\b",
            re.I,
        ),
    ),
    ("launch", re.compile(r"\blaunch", re.I)),
    ("sales", re.compile(r"\b(sales|prospect|customer pitch|proposal)\b", re.I)),
    ("partnership", re.compile(r"\bpartner", re.I)),
)


def arc_for(deck_type: DeckType, prompt: str = "") -> str:
    """The arc for a deck type. "auto" reads the brief's words, else a pitch."""
    if deck_type != "auto":
        return deck_type
    return next((arc for arc, words in _NAMED if words.search(prompt)), "pitch")
