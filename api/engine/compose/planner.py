"""Check each slide's job against its data and ration its ornament
(docs/v4/design-engine.md -> Compositions).

Plain code. How a slide is built is no longer chosen from a list here: each
slide gets a composition target in continuous space (compose/targets.py,
phase 36). The rules kept: the cover and the ask are the fixed ends; a chart
or number slide needs its data; section slides only in decks over 12 slides;
image-led slides at most 40%; texture on about one slide in three, never two
in a row, never on a dense slide.
"""

from __future__ import annotations

from engine.models import SlidePlan

IMAGE_SHARE = 0.4
TEXTURE_EVERY = 3  # a texture on about one slide in three, never two in a row
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
    """Return the plans with ``intent`` checked and ``ornament`` set."""
    images = 0
    since_texture = TEXTURE_EVERY - 1  # the first middle slide may carry one
    out: list[SlidePlan] = []
    for index, plan in enumerate(plans):
        intent = _intent(plan, index, len(plans), images)
        images += intent == "image-led"
        if intent in ("cover", "ask"):
            ornament = "mark"
        elif since_texture >= TEXTURE_EVERY - 1 and not _dense(plan):
            ornament, since_texture = "texture", -1
        else:
            ornament = "none"
        since_texture += 1
        out.append(plan.model_copy(update={"intent": intent, "ornament": ornament}))
    return out
