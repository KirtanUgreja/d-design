"""Layer 3b, the designer: each slide written in HTML, CSS and flat SVG from
the art director's plan, with no template and no reference library (owner,
2026-10-09: "don't limit it to simple shapes"). Also the targeted repair, the
edit asked in words, and the code-built layout every slide can fall back to.
"""

from __future__ import annotations

from html import escape

from engine.design.theme import Theme
from engine.llm.openrouter import ModelError, Seam
from engine.models import Defect, SlidePlan
from engine.studio.direct import SlideDirection
from engine.studio.slide import PAIRS, Composed, fields_text, parser
from lib.result import Err, Result, ok

PROMPT_VERSION = "design.v1"
# Hidden reasoning is billed out of max_tokens; a ceiling costs nothing unused.
MAX_TOKENS = 32000

SYSTEM = """You are a senior presentation designer. You design ONE slide, in HTML, CSS and flat
SVG, inside the deck's design system, from your art director's plan. Every slide you make
must look designed by a person with taste: bold, specific to its content, unlike a template.

How you work:
- One hero, set BIG: the plan names it. Scale contrast is your main tool — the hero 4 to 8
  times the body text. Then the headline, then the rest, each clearly smaller.
- Use the whole 1920x1080 canvas: an asymmetric grid of 12 columns, fields of colour that run
  off the edge, a giant numeral or word as decoration (data-deco), crops and bleeds. Leave one
  large quiet area rather than many small gaps.
- Draw when it helps: a flat SVG diagram of the idea (a loop, layers, a funnel, a timeline, a
  network, a device, abstract product art) in theme colours, large and structural, not clip art.
- Type: the display face for the hero and headline, tight leading; the label face for kickers
  and sources, small caps-style (uppercase, tracked); the text face for body and points.
  Points are a ruled list, numbered columns or a typographic run — never boxed cards.
- Follow the plan; where you can make it better, do.
Follow the contract exactly."""


async def compose(
    seam: Seam,
    plan: SlidePlan,
    direction: SlideDirection | None,
    *,
    prefix: str,
    model: str,
    position: int,
    total: int,
    thought: str,
    concept: str,
    image: bool,
) -> Result[Composed, ModelError]:
    idea = (
        f"Hero: {direction.hero}. Main field: {direction.ground}.\n{direction.idea}"
        if direction
        else "No plan for this slide: design it from the deck's look."
    )
    user = (
        f"Slide {position} of {total}. The deck argues: {thought}\n"
        + (f"The deck's visual idea: {concept}\n" if concept else "")
        + f"This slide's job: {plan.intent} ({plan.beat}).\n\n"
        f"YOUR ART DIRECTOR'S PLAN FOR THIS SLIDE\n{idea}\n\n"
        f"Fields:\n{fields_text(plan)}\n"
        + (
            "\nThis slide has a picture: place one <dd-image aspect=…> where the plan says."
            if image
            else "\nThis slide has no picture."
        )
        + (
            f"\nThis slide has a {plan.chart.type} chart of "
            f"{len(plan.chart.series[0].points)} values: place one empty <dd-chart>."
            if plan.chart
            else ""
        )
        + (
            f"\nThis slide has a {plan.visual.kind} visual: place one empty <dd-visual> as "
            "the hero."
            if plan.visual
            else ""
        )
    )
    got = await seam.complete_text(
        "compose",
        parser(plan, image=image),
        system=SYSTEM,
        user=user,
        model=model,
        prefix=prefix,
        prompt_version=PROMPT_VERSION,
        max_tokens=MAX_TOKENS,
        reasoning="low",
        slide_id=plan.id,
    )
    return got if isinstance(got, Err) else ok(got.value[0])


async def repair(
    seam: Seam,
    plan: SlidePlan,
    current: Composed,
    defects: list[Defect],
    *,
    prefix: str,
    model: str,
) -> Result[Composed, ModelError]:
    """One targeted repair from measured defects: the smallest change that
    fixes them. The model is told what was measured, never asked to judge."""
    listed = "\n".join(
        f"- {d.code} {d.field or 'slide'}: measured {d.measured}; required {d.threshold}"
        for d in defects[:12]
    )
    user = (
        "This slide was rendered at 1920x1080 and measured. Fix ONLY these defects with the "
        "smallest change, keep the design, and return the full html and css again.\n\n"
        f"Defects:\n{listed}\n"
        + (
            "E5 is contrast: give each listed field the text colour paired with the ground "
            f"actually behind it:\n{PAIRS}\n"
            if any(d.code == "E5" for d in defects)
            else ""
        )
        + f"\nFields (text must stay unchanged):\n{fields_text(plan)}\n\n"
        f"```html\n{current.html}\n```\n```css\n{current.css}\n```"
    )
    got = await seam.complete_text(
        "repair",
        parser(plan, image="<dd-image" in current.html),
        system="You repair one slide. Follow the contract exactly.",
        user=user,
        model=model,
        prefix=prefix,
        prompt_version=PROMPT_VERSION,
        max_tokens=16000,
        reasoning="low",
        slide_id=plan.id,
    )
    return got if isinstance(got, Err) else ok(got.value[0])


async def revise(
    seam: Seam,
    plan: SlidePlan,
    current: Composed,
    instruction: str,
    *,
    prefix: str,
    model: str,
) -> Result[Composed, ModelError]:
    """A change asked in words (the editor's "Ask"): layout, scale, emphasis
    and order may change; the words may not. A proposal, applied only when
    the person accepts it."""
    user = (
        "The person asked for this change to the slide below. Make it, keep everything "
        "else, and return the full html and css again. Layout, scale, emphasis and order "
        "may change; the words may not, and colour and type stay the theme's.\n\n"
        f"The change: {instruction}\n\n"
        f"Fields (text must stay unchanged):\n{fields_text(plan)}\n\n"
        f"```html\n{current.html}\n```\n```css\n{current.css}\n```"
    )
    got = await seam.complete_text(
        "revise",
        parser(plan, image="<dd-image" in current.html),
        system=SYSTEM,
        user=user,
        model=model,
        prefix=prefix,
        prompt_version=PROMPT_VERSION,
        max_tokens=MAX_TOKENS,
        reasoning="low",
        slide_id=plan.id,
    )
    return got if isinstance(got, Err) else ok(got.value[0])


# --- the floor: a layout built by code, so its words fit by construction -----

_LABEL = (
    "font-family:var(--f-label);font-size:var(--t-label);letter-spacing:0.08em;"
    "text-transform:uppercase"
)
_DISPLAY = "font-family:var(--f-display);font-weight:var(--w-display)"
_SOURCE = (
    ".src{font-family:var(--f-label);font-size:var(--t-label);color:var(--c-ink-2);"
    "border-top:var(--rule) solid var(--c-rule);padding-top:var(--s-2)}"
)


def _step(text: str, steps: tuple[tuple[int, str], ...], last: str) -> str:
    """The largest type step whose length limit the text is within."""
    return next((name for limit, name in steps if len(text) <= limit), last)


def fallback(plan: SlidePlan, theme: Theme | None = None) -> Composed:
    """The code-built layout: no model, words that fit by construction. Used
    when a slide cannot be designed or repaired, and by "Fit to slide"."""
    by = {f.name: escape(f.text) for f in plan.fields}
    head = by.get("headline", "")
    skip = ("kicker", "headline", "source", "stat", "stat-label", "body")
    rest = [f for f in plan.fields if f.name not in skip]
    kicker = f'<p class="k" data-field="kicker">{by["kicker"]}</p>' if "kicker" in by else ""
    source = f'<p class="src" data-field="source">{by["source"]}</p>' if "source" in by else ""
    body = f'<p class="b" data-field="body">{by["body"]}</p>' if "body" in by else ""
    items = "".join(f'<li data-field="{f.name}">{escape(f.text)}</li>' for f in rest)
    base = (
        f".k{{{_LABEL};color:var(--c-ink-2)}}{_SOURCE}"
        ".b{font-family:var(--f-text);font-size:var(--t-body);line-height:1.35;max-width:900px}"
    )
    component = (
        '<dd-chart class="ch"></dd-chart>'
        if plan.chart
        else '<dd-visual class="ch"></dd-visual>'
        if plan.visual
        else ""
    )

    if len(by.get("headline", "")) > 90 and not component:
        # A long claim (an edit can make one): the full width, at the smallest
        # headline step, so it stays within four lines; the rest in a row below.
        stat = (f'<p class="st" data-field="stat">{by["stat"]}</p>' if "stat" in by else "") + (
            f'<p class="lb" data-field="stat-label">{by["stat-label"]}</p>'
            if "stat-label" in by
            else ""
        )
        html = (
            f'<section class="s">{kicker}<h1 class="h" data-field="headline">{head}</h1>'
            f'<div class="r"><div class="n">{stat}{body}</div><ul class="l">{items}</ul></div>'
            f"{source}</section>"
        )
        css = (
            ".s{display:grid;grid-template-rows:auto auto 1fr auto;gap:var(--s-4);padding:64px}"
            f".h{{{_DISPLAY};font-size:var(--t-h2);line-height:1.05}}"
            ".r{display:grid;grid-template-columns:1fr 1fr;gap:var(--s-6);align-items:end}"
            ".n{display:grid;gap:var(--s-2)}"
            f".st{{{_DISPLAY};font-size:var(--t-d3);line-height:var(--lh-display);color:var(--c-ink)}}"
            ".lb{font-size:var(--t-body)}"
            ".l{display:grid}.l li{font-size:var(--t-body);padding:var(--s-2) 0;"
            "border-top:var(--rule) solid var(--c-rule)}" + base
        )
        return Composed(html, css)

    if component:  # the claim on the left, the chart or visual filling the right
        dense = bool(rest) and bool(body)  # points and a body line: the claim steps down
        hsize = "h2" if dense else _step(head, ((40, "h1"),), "h2")
        cols = "6fr 6fr" if dense else "5fr 7fr"
        stat = (f'<p class="st" data-field="stat">{by["stat"]}</p>' if "stat" in by else "") + (
            f'<p class="lb" data-field="stat-label">{by["stat-label"]}</p>'
            if "stat-label" in by
            else ""
        )
        html = (
            f'<section class="s"><div class="t">{kicker}'
            f'<h1 class="h" data-field="headline">{head}</h1>{body}{stat}'
            f'<ul class="l">{items}</ul>{source}</div>{component}</section>'
        )
        css = (
            f".s{{display:grid;grid-template-columns:{cols};gap:var(--s-6);"
            "padding:var(--margin);align-items:center}"
            ".t{display:grid;gap:var(--s-3);align-content:center}"
            f".h{{{_DISPLAY};font-size:var(--t-{hsize});line-height:1.02}}"
            f".st{{{_DISPLAY};font-size:var(--t-d3);line-height:var(--lh-display);"
            "color:var(--c-ink)}.lb{font-size:var(--t-body)}"
            ".l{display:grid}.l li{font-size:var(--t-body);padding:var(--s-2) 0;"
            "border-top:var(--rule) solid var(--c-rule)}"
            ".ch{height:820px;min-width:0}" + base
        )
        return Composed(html, css)

    if "stat" in by:  # a colour field carries the number; the claim sits beside it
        size = _step(by["stat"], ((3, "mega"), (5, "d1"), (8, "d2")), "d3")
        hsize = _step(head, ((36, "h1"),), "h2")
        label = (
            f'<p class="lb" data-field="stat-label">{by["stat-label"]}</p>'
            if "stat-label" in by
            else ""
        )
        html = (
            f'<section class="s"><div class="f"><p class="st" data-field="stat">{by["stat"]}</p>'
            f'{label}</div><div class="c"><div class="t">{kicker}'
            f'<h1 class="h" data-field="headline">{head}</h1>{body}</div>'
            f'<ul class="l">{items}</ul>{source}</div></section>'
        )
        css = (
            ".s{display:grid;grid-template-columns:1fr 1fr}"
            ".f{background-color:var(--c-accent);color:var(--c-on-accent);padding:var(--margin);"
            "display:grid;align-content:end;gap:var(--s-3)}"
            f".st{{{_DISPLAY};font-size:var(--t-{size});line-height:var(--lh-display);"
            "letter-spacing:-0.02em}"
            ".lb{font-size:var(--t-body);max-width:600px}"
            ".c{padding:var(--margin);display:grid;grid-template-rows:auto 1fr auto;"
            "gap:var(--s-4)}.t{display:grid;gap:var(--s-3)}"
            f".h{{{_DISPLAY};font-size:var(--t-{hsize});line-height:1.02}}"
            ".l{align-self:end;display:grid}"
            ".l li{font-size:var(--t-body);padding:var(--s-2) 0;"
            "border-top:var(--rule) solid var(--c-rule)}" + base
        )
        return Composed(html, css)

    if rest or body:  # a ruled list beside the headline
        hsize = _step(head, ((30, "h1"),), "h2")
        cols = "5fr 7fr" if hsize == "h1" else "7fr 5fr"
        html = (
            f'<section class="s"><div class="t">{kicker}'
            f'<h1 class="h" data-field="headline">{head}</h1>{body}</div>'
            f'<ul class="l">{items}</ul>{source}</section>'
        )
        css = (
            f".s{{display:grid;grid-template-columns:{cols};grid-template-rows:1fr auto;"
            "column-gap:var(--s-7);row-gap:var(--s-4);padding:var(--margin)}"
            ".t{display:grid;gap:var(--s-4);align-content:start}"
            f".h{{{_DISPLAY};font-size:var(--t-{hsize});line-height:1.02}}"
            ".l{display:grid;align-self:end}"
            ".l li{font-size:var(--t-h3);line-height:1.15;padding:var(--s-4) 0;"
            "border-top:var(--rule) solid var(--c-rule)}"
            ".src{grid-column:1 / 3}" + base
        )
        return Composed(html, css)

    # only a sentence: set it at poster scale on the accent field
    hsize = _step(head, ((36, "d2"), (62, "d3")), "h1")
    html = (
        f'<section class="s">{kicker or "<span></span>"}'
        f'<h1 class="h" data-field="headline">{head}</h1>{source}</section>'
    )
    css = (
        ".s{display:grid;grid-template-rows:auto 1fr auto;gap:var(--s-4);"
        "padding:var(--margin);background-color:var(--c-accent);color:var(--c-on-accent)}"
        f".h{{align-self:end;{_DISPLAY};font-size:var(--t-{hsize});"
        "line-height:var(--lh-display);letter-spacing:-0.015em;max-width:1500px}"
        ".s .k,.s .src{color:var(--c-on-accent)}" + base
    )
    return Composed(html, css)
