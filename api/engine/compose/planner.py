"""Give each slide an archetype: how it is built, as distinct from what it is
for (docs/v4/design-engine.md -> Compositions).

Plain code. Variety inside a deck is decided here, not hoped for in a prompt:
no archetype twice in a row, and the least-used candidate wins.
"""

from __future__ import annotations

from engine.models import SlidePlan

_PREFER: dict[str, tuple[str, ...]] = {
    "cover": ("poster", "band", "corner"),
    "statement": ("poster", "stack", "corner"),
    "question": ("poster", "corner", "stack"),
    "quote": ("stack", "corner", "poster"),
    "number": ("split", "band", "corner"),
    "number-set": ("grid", "band", "split"),
    "chart": ("split", "band", "grid"),
    "points": ("split", "stack", "grid"),
    "comparison": ("grid", "split", "band"),
    "steps": ("grid", "split", "stack"),
    "timeline": ("band", "grid", "stack"),
    "team": ("corner", "grid", "split"),
    "case": ("split", "corner", "stack"),
    "image-led": ("poster", "split", "band"),
    "section": ("poster", "band", "corner"),
    "ask": ("band", "poster", "split"),
}
_DEFAULT = ("stack", "split", "corner")


def assign(plans: list[SlidePlan]) -> list[SlidePlan]:
    """Return the plans with ``archetype`` set."""
    used: dict[str, int] = {}
    previous = ""
    out: list[SlidePlan] = []
    for plan in plans:
        candidates = [a for a in _PREFER.get(plan.intent, _DEFAULT) if a != previous]
        choice = min(candidates, key=lambda a: (used.get(a, 0), candidates.index(a)))
        used[choice] = used.get(choice, 0) + 1
        previous = choice
        out.append(plan.model_copy(update={"archetype": choice}))
    return out
