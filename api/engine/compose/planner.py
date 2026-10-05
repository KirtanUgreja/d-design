"""Give each slide an archetype: how it is built, as distinct from what it is
for (docs/v4/design-engine.md -> Compositions).

Plain code. Variety inside a deck is decided here, not hoped for in a prompt.
The rhythm rules: the cover and the ask are the fixed ends; a chart or number
slide needs its data; section slides only in decks over 12 slides; image-led
slides at most 40%; no archetype twice in a row; a dense slide never follows a
dense one; and the least-used candidate wins.
"""

from __future__ import annotations

from engine.models import SlidePlan

# How each archetype is built, for the compose prompt.
ARCHETYPES: dict[str, str] = {
    "poster": "type-dominant and full bleed; one element at enormous scale",
    "split": "two unequal fields side by side, one of them a colour field that carries content",
    "stack": "an editorial vertical rhythm: kicker, headline, body, set down a column",
    "grid": "modular cells on the grid; each cell holds one point, with rules not boxes",
    "band": "horizontal bands across the full width, each band a different weight",
    "corner": "content anchored to one corner, the rest of the field left empty on purpose",
    "margin": "a main column with notes and labels hung in a wide margin",
    "frame": "one element inset inside a ruled frame, the frame part of the design",
    "overlap": "type layered over a colour or texture field (mark the overlap with data-layer)",
    "columns": "two or three text columns of equal width, like a broadsheet page",
}
DENSE = frozenset({"grid", "band", "columns", "margin"})

_PREFER: dict[str, tuple[str, ...]] = {
    "cover": ("poster", "corner", "overlap", "band"),
    "statement": ("poster", "stack", "corner", "overlap"),
    "question": ("poster", "corner", "stack"),
    "quote": ("stack", "corner", "frame", "poster"),
    "number": ("split", "band", "corner", "frame"),
    "number-set": ("grid", "band", "columns", "split"),
    "chart": ("stack", "split", "margin", "band"),
    "points": ("split", "stack", "margin", "columns", "grid"),
    "comparison": ("columns", "split", "grid", "band"),
    "steps": ("grid", "columns", "band", "split"),
    "timeline": ("band", "grid", "columns", "stack"),
    "team": ("grid", "columns", "corner", "split"),
    "case": ("split", "margin", "frame", "stack"),
    "image-led": ("overlap", "poster", "split", "band"),
    "section": ("poster", "band", "corner"),
    "ask": ("band", "poster", "split", "frame"),
}
_DEFAULT = ("stack", "split", "corner", "margin")
IMAGE_SHARE = 0.4
SECTION_MIN_SLIDES = 13
_DENSE_WORDS = 30


def _intent(plan: SlidePlan, index: int, total: int, images: int) -> str:
    names = {f.name for f in plan.fields}
    if index == 0:
        return "cover"
    if index == total - 1:
        return "ask"
    intent = plan.intent
    if intent == "chart" and plan.chart is None:
        intent = "points"  # no approved data, no chart
    if intent == "number" and "stat" not in names:
        intent = "statement"
    if intent == "section" and total < SECTION_MIN_SLIDES:
        intent = "statement"
    if intent == "image-led" and images >= IMAGE_SHARE * total:
        intent = "statement"
    if intent == "points" and not any(n.startswith("point-") for n in names):
        intent = "statement"
    return intent


def _dense(plan: SlidePlan) -> bool:
    return sum(len(f.text.split()) for f in plan.fields) > _DENSE_WORDS


def assign(plans: list[SlidePlan]) -> list[SlidePlan]:
    """Return the plans with ``intent`` checked and ``archetype`` set."""
    used: dict[str, int] = {}
    previous = ""
    previous_dense = False
    images = 0
    out: list[SlidePlan] = []
    for index, plan in enumerate(plans):
        intent = _intent(plan, index, len(plans), images)
        images += intent == "image-led"
        dense = _dense(plan)
        candidates = [a for a in _PREFER.get(intent, _DEFAULT) if a != previous]
        if previous_dense and dense:
            candidates = [a for a in candidates if a not in DENSE] or candidates
        choice = min(candidates, key=lambda a: (used.get(a, 0), candidates.index(a)))
        used[choice] = used.get(choice, 0) + 1
        previous, previous_dense = choice, dense and choice in DENSE
        out.append(plan.model_copy(update={"intent": intent, "archetype": choice}))
    return out
