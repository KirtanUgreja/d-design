"""The last rung before a flag: a slide built by code from its composition
target (docs/v4/plan/36-independent-design.md -> Make, 6). Replaces
exemplar-fill, so no stored layout exists anywhere in the compose path.

Every position and size is computed from the target's continuous values and
the deck's measured type, so two procedural slides share a method, not a
layout. Text is fitted before it is placed: the type steps down until the
estimate fits, and QA measures the result like any other slide.
"""

from __future__ import annotations

import math
from html import escape

from engine.compose import author
from engine.compose.author import Composed
from engine.compose.targets import Target
from engine.design.theme import Theme, display_width
from engine.models import SlidePlan

HERO_STEPS = ("h2", "h1", "d3", "d2", "d1", "mega")
_TEXT_ADVANCE = 0.52  # em, a text face's average advance; ponytail: measure per face
_FIGURE_ADVANCE = 0.58  # em; figures run wider than the average letter, in wide faces too
_SPECIAL = ("kicker", "headline", "source", "stat", "stat-label")


def _clamp(v: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, v))


SAFETY = 1.2  # word wrap wastes the end of every line; the estimate must not be short


def _lines(text: str, px: int, advance: float, width: float) -> int:
    return max(1, math.ceil(len(text) * px * advance * SAFETY / max(width, 1)))


def _figure_advance(text: str, advance: float) -> float:
    """A number's advance: figures run wider than the average letter, and
    capitals and signs ($, %, M) wider still. ponytail: estimated; measure
    figure and capital widths into meta.json when a face still overflows."""
    wide = sum(not c.isdigit() and not c.islower() for c in text) / max(len(text), 1)
    return max(advance * 1.15, _FIGURE_ADVANCE) * (1 + 0.6 * wide)


def _wanted(theme: Theme, target: Target) -> str:
    """The step the target asks for. 0 -> the headline floor, 0.5 -> about d2,
    1 -> mega: the reference decks (2026-10-05) are strongest where one thing
    is enormous."""
    px = theme.scale["h2"] * 6 ** target.point["hero"]
    return [s for s in HERO_STEPS if theme.scale[s] <= max(px, theme.scale["h2"])][-1]


def _hero_step(theme: Theme, target: Target, text: str, width: float, max_lines: int) -> str:
    """The largest step at or under the target's scale that fits in max_lines."""
    want = theme.scale[_wanted(theme, target)]
    advance = display_width(theme.display.family, theme.w_display)
    if max_lines == 1:  # a number: figures are wider than the average lowercase letter
        advance = _figure_advance(text, advance)
    longest = max((len(w) for w in text.split()), default=0)
    fits = [
        s
        for s in HERO_STEPS
        if theme.scale[s] <= max(want, theme.scale["h2"])
        and _lines(text, theme.scale[s], advance, width) <= max_lines
        and longest * theme.scale[s] * advance * SAFETY <= width
    ]
    return fits[-1] if fits else "h2"


def build(plan: SlidePlan, target: Target, theme: Theme) -> Composed:
    if plan.chart is not None:
        return author.fallback(plan)  # ponytail: the chart layout is not target-driven yet
    p = dict(target.point)
    if any(f.name == "stat" for f in plan.fields):
        # a number is the slide: it is set huge whatever the target's scale says
        p["hero"] = max(p["hero"], 0.75)
        target = Target(p)
    by = {f.name: escape(f.text) for f in plan.fields}
    rest = [f for f in plan.fields if f.name not in _SPECIAL]
    m = theme.margin
    avail = 1920 - 2 * m
    # A colour field always runs off the canvas edge: a padded field on the
    # ground reads as a card, which the design rules ban.
    panel = p["field"] > 0.25
    left = p["mass_x"] < 0.5

    width = _clamp(560 + p["axis"] * 1100, 560, avail)
    if len(rest) >= 4:
        width = max(width, min(avail, 1200))
    if panel:
        width = _clamp(p["field"] * 1920, 720, 1200) - 2 * m
    inner = width
    if not rest:  # a statement: the hero wins, so widen the measure before shrinking the type
        want = _wanted(theme, target)
        text = by.get("stat") or by.get("headline", "")
        lines = 1 if "stat" in by else 3
        adv = display_width(theme.display.family, theme.w_display)
        if lines == 1:
            adv = _figure_advance(text, adv)
        need = len(text) * theme.scale[want] * adv * SAFETY / lines
        width = inner = _clamp(max(width, need), width, avail)

    # The hero: the number if there is one, else the headline.
    hero_text = by.get("stat") or by.get("headline", "")
    hero = _hero_step(theme, target, hero_text, inner, 1 if "stat" in by else 3)
    head = "h1" if "stat" not in by else _hero_step(theme, target, by.get("headline", ""), inner, 3)
    if "stat" in by:
        head = head if HERO_STEPS.index(head) < HERO_STEPS.index(hero) else "h2"
    else:
        head = hero
    advance = display_width(theme.display.family, theme.w_display)
    body = theme.scale["body"]

    def height() -> float:
        h = sum(
            _lines(by[k], theme.scale[s], advance, inner)
            * theme.scale[s]
            * 1.25  # display ink overshoots a tight line box
            for k, s in (("stat", hero), ("headline", head))
            if k in by
        )
        h += sum(
            _lines(f.text, body, _TEXT_ADVANCE, inner) * body * 1.3 + 2 * theme.space[2]
            for f in rest
        )
        return h + theme.space[4] * (len(rest) + 3)

    # A headline that cannot fit three lines even at the floor step widens its measure.
    while _lines(by.get("headline", ""), theme.scale[head], advance, inner) > 3 and width < avail:
        width = inner = min(avail, width + 120)
    room = 1080 - 2 * m
    while height() > room and head != "h2":
        head = HERO_STEPS[max(0, HERO_STEPS.index(head) - 1)]
        if "stat" not in by:
            hero = head
    if height() > room:  # still too tall: take the full measure
        width = inner = avail
    while height() > room and HERO_STEPS.index(hero) > HERO_STEPS.index("h1"):
        hero = HERO_STEPS[HERO_STEPS.index(hero) - 1]

    on = "var(--c-on-accent)" if panel else "var(--c-ink)"
    quiet = "var(--c-on-accent)" if panel else "var(--c-ink-2)"
    rule = "var(--c-on-accent)" if panel else "var(--c-rule)"
    parts = []
    if "kicker" in by:
        parts.append(f'<p class="k" data-field="kicker">{by["kicker"]}</p>')
    if "stat" in by:
        parts.append(f'<p class="st" data-field="stat">{by["stat"]}</p>')
        if "stat-label" in by:
            parts.append(f'<p class="lb" data-field="stat-label">{by["stat-label"]}</p>')
    if "headline" in by:
        parts.append(f'<h1 class="h" data-field="headline">{by["headline"]}</h1>')
    if rest:
        items = "".join(f'<li data-field="{f.name}">{escape(f.text)}</li>' for f in rest)
        parts.append(f'<ul class="l">{items}</ul>')
    if "source" in by:
        parts.append(f'<p class="src" data-field="source">{by["source"]}</p>')
    block = f'<div class="b">{"".join(parts)}</div>'

    align = ("start", "center", "end")[min(2, int(p["mass_y"] * 3))]
    display = (
        "font-family:var(--f-display);font-weight:var(--w-display);"
        "line-height:var(--lh-display);letter-spacing:var(--track-display)"
    )
    css = [
        f".b{{display:grid;gap:var(--s-4);width:{inner:.0f}px;color:{on}}}",
        ".k,.src{font-family:var(--f-label);font-size:var(--t-label);"
        f"color:{quiet};letter-spacing:0.08em;text-transform:uppercase}}",
        f".st{{{display};font-size:var(--t-{hero})}}",
        f".lb{{font-family:var(--f-text);font-size:var(--t-body);color:{quiet}}}",
        f".h{{{display};font-size:var(--t-{head})}}",
        ".l{display:grid}",
        f".l li{{font-family:var(--f-text);font-size:var(--t-body);line-height:1.3;"
        f"padding:var(--s-2) 0;border-top:var(--rule) solid {rule}}}",
    ]
    if panel:
        cols = f"{width + 2 * m:.0f}px 1fr" if left else f"1fr {width + 2 * m:.0f}px"
        side = "1" if left else "2"
        html = f'<section class="s"><div class="p">{block}</div></section>'
        css += [
            f".s{{display:grid;grid-template-columns:{cols}}}",
            f".p{{grid-column:{side};background-color:var(--c-accent);padding:var(--margin);"
            f"display:grid;align-content:{align}}}",
        ]
    else:
        offset = (avail - width) * _clamp((p["mass_x"] - 0.2) / 0.6, 0, 1)
        html = f'<section class="s">{block}</section>'
        css += [
            f".s{{display:grid;padding:var(--margin);align-content:{align}}}",
            f".b{{margin-left:{offset:.0f}px}}",
        ]
    return Composed(html, "".join(css))
