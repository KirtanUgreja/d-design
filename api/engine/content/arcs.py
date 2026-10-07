"""The five arcs and the evidence each needs (docs/v4/content.md -> Arcs).

Research queries come from an arc's evidence needs, not from the topic alone.
"""

from __future__ import annotations

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
        "how often the problem occurs for this audience",
        "adoption of the category",
        SERIES,
    ),
    "investor_update": ("market conditions relevant to the period", SERIES),
    "partnership": ("the size of the shared opportunity", "the partner's market position", SERIES),
}


def arc_for(deck_type: DeckType) -> str:
    return "pitch" if deck_type == "auto" else deck_type
