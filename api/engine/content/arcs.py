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
EVIDENCE: dict[str, tuple[str, ...]] = {
    "pitch": (
        "the cost of the problem today",
        "the market size",
        "why-now signals",
        "the competitive landscape",
    ),
    "sales": ("the cost of the status quo in the buyer's industry", "industry benchmarks"),
    "launch": ("how often the problem occurs for this audience", "adoption of the category"),
    "investor_update": ("market conditions relevant to the period",),
    "partnership": ("the size of the shared opportunity", "the partner's market position"),
}


def arc_for(deck_type: DeckType) -> str:
    return "pitch" if deck_type == "auto" else deck_type
