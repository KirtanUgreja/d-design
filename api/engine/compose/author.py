"""Compose one slide: the model writes HTML and CSS inside the theme.

The answer is parsed, sanitized and linted before it is accepted, so the
seam's one repair is spent on anything those refuse. Browser defects are a
second, separate repair (``repair``), because they need a render to find.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from html import escape

from engine.compose.references import Reference
from engine.design.theme import Theme
from engine.llm.openrouter import ModelError, Reply, Seam, parse_fenced
from engine.models import Defect, SlidePlan
from engine.qa.lint import lint
from engine.qa.sanitize import sanitize
from lib.result import Err, Result, err, ok

PROMPT_VERSION = "compose.v11"  # v11: adapt a reference in the deck's visual language
PAIRS = (
    "  on --c-ground or --c-surface: --c-ink, or --c-ink-2 for quiet text\n"
    "  on --c-accent: --c-on-accent only, at every size\n"
    "  on --c-ink: --c-ground only"
)
# Hidden reasoning is billed out of max_tokens: at 12k and 20k a third of
# v10's calls were cut off (2026-10-07); 32k cut off none. A reference to
# adapt needs far less thought, but the ceiling costs nothing unused.
COMPOSE_MAX_TOKENS = 32000

# What a variant name in a reference's metadata asks for (phase 39 -> 4).
VARIATIONS: dict[str, str] = {
    "mirror": "Mirror the composition left to right.",
    "image-other-side": "Move the image to the other side; the text takes its place.",
    "dark-field": "Set the main block on a --c-ink or --c-accent field instead of the ground.",
    "accent-number": "Set the number in --c-accent (on --c-ground only).",
    "hero-number": "Make the number the hero: one step larger, the rest one step quieter.",
    "rule-top": "Move the structural rule above the title instead of below it.",
    "flip-vertical": "Flip the composition top to bottom.",
    "wide-headline": "Give the headline the full width; the rest sits below it.",
}


def variation_text(name: str) -> str:
    if not name:
        return "Keep the reference's composition; change proportions only to fit the words."
    return VARIATIONS.get(name, f"Apply this variation of the reference: {name}.")


def rules(*, shapes: bool) -> str:
    shape_rule = (
        '- <dd-shape kind="…" tone="accent|ink|surface|rule"></dd-shape> is a flat shape our\n'
        "  code draws into its box: kinds disc, ring, arc, half, quarter, diagonal, band, blob,\n"
        "  steps, plus. At most two, large and structural, as the reference uses them.\n"
        if shapes
        else "- No dd-shape: this deck's visual language does not use shapes.\n"
    )
    return f"""You are a senior designer. You adapt ONE presentation slide, as HTML and CSS, from a
REFERENCE slide in this deck's visual language. The slide is projected at exactly 1920x1080px. It
must look designed by a person in this language, never like a template or an AI-made slide.

OUTPUT: one ```html block and one ```css block. Nothing else.

HOW TO ADAPT THE REFERENCE
- Keep its system: the grid, how the type behaves (scale, weight, case, tracking), how the
  elements relate (alignment axes, rules, fields, the image slot's placement).
- Fit THIS slide's words: change proportions, type steps and spans only as the words need.
  Drop the reference's elements for fields this slide does not have and let the layout close.
- Apply the VARIATION you are given.
- The reference holds no words; use exactly the slide's fields.

HTML CONTRACT
- One root: <section class="s"> … </section>.
  No <html>, <body>, <style>, <script>, <img>, <a>, <svg>.
- Allowed tags: div section header footer h1 h2 h3 p span strong em small sup sub br hr ul ol li
  blockquote figure figcaption dd-texture dd-shape dd-chart dd-image.
- Every field you are given appears EXACTLY ONCE, in an element with data-field="<name>", with its
  text UNCHANGED. You may wrap words in <em> or <span class="…"> and use <br>. You may not add,
  drop or rewrite words.
- Any other visible text must be decoration: at most 3 words, in an element with data-deco
  (a folio like "04", a big numeral). Do not invent labels, captions or numbers.
- <dd-image aspect="…" class="…"></dd-image> is an image slot our code fills with this deck's
  picture. Keep it only when the slide says it has an image; otherwise remove it. Never put text
  directly over it: text near an image sits on a solid field.
- <dd-texture kind="…" tone="accent|ink|surface"></dd-texture> is flat colour ("solid") or a
  pattern; only the kinds THEME TOKENS lists, at most two, never under text.
{shape_rule}- <dd-chart class="…"></dd-chart> is an empty box our code draws a chart into.
  Place it only when the slide says it has a chart, at least 900x480px, and never write its
  numbers or labels.
- Attributes allowed: class, data-field, data-deco, data-layer, data-bleed, kind/tone on
  dd-texture and dd-shape, aspect on dd-image. No style attribute, no id.

CSS CONTRACT
- Plain class selectors. No @-rules, no :root/html/body/:host, no nesting, no !important.
- Colour: only var(--c-…) tokens (or transparent / currentColor). Never a hex, rgb(), or a name.
- font-family: only var(--f-display), var(--f-text) or var(--f-label).
  font-size: only a var(--t-…) token. font-weight: only var(--w-display), var(--w-regular),
  var(--w-bold). Set them as separate properties — the `font` shorthand is banned.
- Banned: gradients, url(), filter, backdrop-filter, text-shadow, mask, opacity, animation,
  transition, position:fixed, vw/vh units, text in `content`.
- border-radius: only 0, 50% or var(--radius). box-shadow: only var(--shadow-hard).

DESIGN RULES
- Keep all text at least 64px from every edge; normally use var(--margin).
- Sizes: the headline at least 56px; body text at least 32px (--t-body or larger);
  labels, kickers and sources at least 22px (--t-label).
- Text never overlaps other text and never runs outside its box. A long headline takes a smaller
  --t- step or a wider box: at most 4 lines, never one word per line.
- Contrast — text colour is decided by the ground it sits on:
{PAIRS}
  --c-accent as a TEXT colour only at 64px or larger, and only on --c-ground. Every text inside an
  accent field must be --c-on-accent: set color on the field.
- A rectangle of flat colour must carry something (the headline, the number, the list); an empty
  coloured rectangle is refused (E11).
- NEVER: cards or boxes around each point, icon rows, pills or badges, drop shadows, emoji.
"""


@dataclass(frozen=True)
class Composed:
    html: str
    css: str


def prefix(theme: Theme, *, shapes: bool = False) -> str:
    """The stable, cacheable part of every compose call for one deck: the
    contract and the theme, whose guidance leads with the visual language."""
    return f"{rules(shapes=shapes)}\nTHEME TOKENS\n{theme.describe()}\n"


def _fields(plan: SlidePlan) -> str:
    return "\n".join(f'- {f.name}: "{f.text}"' for f in plan.fields)


def _parser(plan: SlidePlan, *, image: bool = False) -> Callable[[Reply], Result[Composed, str]]:
    names = frozenset(f.name for f in plan.fields)

    def parse(reply: Reply) -> Result[Composed, str]:
        blocks = parse_fenced(reply.text, "html", "css")
        if isinstance(blocks, Err):
            return blocks
        clean = sanitize(blocks.value["html"], names)
        if isinstance(clean, Err):
            return clean
        problems = lint(blocks.value["css"])
        missing = [n for n in names if f'data-field="{n}"' not in clean.value]
        problems += [f'the field "{n}" has no data-field element' for n in missing]
        if plan.chart is not None and "<dd-chart" not in clean.value:
            problems.append("this slide has a chart: place one empty <dd-chart class=…>")
        if plan.chart is None and "<dd-chart" in clean.value:
            problems.append("this slide has no chart: remove the <dd-chart>")
        if not image and "<dd-image" in clean.value:
            problems.append("this slide has no image: remove the <dd-image>")
        if clean.value.count("<dd-image") > 1:
            problems.append("one <dd-image> at most")
        if problems:
            return err("fix these:\n- " + "\n- ".join(problems[:20]))
        return ok(Composed(clean.value, blocks.value["css"]))

    return parse


async def compose(
    seam: Seam,
    theme: Theme,
    plan: SlidePlan,
    *,
    model: str,
    position: int,
    total: int,
    thought: str,
    reference: Reference | None,
    variation: str = "",
    image: bool = False,
    shapes: bool = False,
    steer: str = "",
) -> Result[Composed, ModelError]:
    ref = (
        reference.prompt("REFERENCE")
        if reference
        else "No reference: design it from the visual language's brief."
    )
    user = (
        f"Slide {position} of {total}. The deck argues: {thought}\n"
        f"This slide's job: {plan.intent} ({plan.beat}).\n\n{ref}\n\n"
        f"VARIATION: {variation_text(variation)}\n"
        + (f"{steer}\n" if steer else "")
        + f"\nFields:\n{_fields(plan)}"
        + (
            "\nThis slide has an image: keep one <dd-image> where the reference places it."
            if image
            else "\nThis slide has no image."
        )
        + (
            f"\nThis slide has a {plan.chart.type} chart of {len(plan.chart.series[0].points)} "
            "values. Place one empty <dd-chart> for it, at least 900x480px."
            if plan.chart
            else ""
        )
    )
    return await seam.complete_text(
        "compose",
        _parser(plan, image=image),
        system="Follow the contract exactly.",
        user=user,
        model=model,
        prefix=prefix(theme, shapes=shapes),
        prompt_version=PROMPT_VERSION,
        max_tokens=COMPOSE_MAX_TOKENS,
        reasoning="low",
        slide_id=plan.id,
    )


async def repair(
    seam: Seam,
    theme: Theme,
    plan: SlidePlan,
    current: Composed,
    defects: list[Defect],
    *,
    model: str,
    shapes: bool = False,
) -> Result[Composed, ModelError]:
    """One targeted repair from measured defects: the smallest change that
    fixes them. The model is told what was measured, never asked to judge."""
    listed = "\n".join(
        f"- {d.code} {d.field or 'slide'}: measured {d.measured}; required {d.threshold}"
        for d in defects[:12]
    )
    user = (
        "This slide was rendered at 1920x1080 and measured. Fix ONLY these defects with the "
        "smallest change, keep the composition, and return the full html and css again.\n\n"
        f"Defects:\n{listed}\n"
        + (
            "E5 is contrast: give each listed field the text colour paired with the ground "
            f"actually behind it:\n{PAIRS}\n"
            if any(d.code == "E5" for d in defects)
            else ""
        )
        + f"\nFields (text must stay unchanged):\n{_fields(plan)}\n\n"
        f"```html\n{current.html}\n```\n```css\n{current.css}\n```"
    )
    return await seam.complete_text(
        "repair",
        _parser(plan, image="<dd-image" in current.html),
        system="Follow the contract exactly.",
        user=user,
        model=model,
        prefix=prefix(theme, shapes=shapes),
        prompt_version=PROMPT_VERSION,
        max_tokens=12000,
        reasoning="low",
        slide_id=plan.id,
    )


async def revise(
    seam: Seam,
    theme: Theme,
    plan: SlidePlan,
    current: Composed,
    instruction: str,
    *,
    model: str,
    shapes: bool = False,
) -> Result[Composed, ModelError]:
    """A change asked in words (phase 28 -> AI edit): the same contract, the
    same words, the person's instruction for layout and emphasis. The answer
    is a proposal; nothing is applied until it is accepted."""
    user = (
        "The person asked for this change to the slide below. Make it, keep everything "
        "else, and return the full html and css again. Layout, scale, emphasis and order "
        "may change; the words may not, and colour and type stay the theme's.\n\n"
        f"The change: {instruction}\n\n"
        f"Fields (text must stay unchanged):\n{_fields(plan)}\n\n"
        f"```html\n{current.html}\n```\n```css\n{current.css}\n```"
    )
    return await seam.complete_text(
        "revise",
        _parser(plan, image="<dd-image" in current.html),
        system="Follow the contract exactly.",
        user=user,
        model=model,
        prefix=prefix(theme, shapes=shapes),
        prompt_version=PROMPT_VERSION,
        max_tokens=COMPOSE_MAX_TOKENS,
        reasoning="low",
        slide_id=plan.id,
    )


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
    """The largest type step whose character budget the text fits."""
    return next((step for limit, step in steps if len(text) <= limit), last)


def fallback(plan: SlidePlan) -> Composed:
    """A composition built by code from the slide's fields: the last rung
    before a flag. Four layouts, chosen by what the slide has — a chart, a
    number, a list, or only a sentence — so a fallback still reads as designed.

    ponytail: four layouts. Ceiling: fallbacks of the same kind look alike.
    Now used only for chart slides; every other fallback is procedural.py.
    """
    by = {f.name: escape(f.text) for f in plan.fields}
    head = by.get("headline", "")
    rest = [f for f in plan.fields if f.name not in ("kicker", "headline", "source", "stat")]
    rest = [f for f in rest if f.name != "stat-label"]
    kicker = f'<p class="k" data-field="kicker">{by["kicker"]}</p>' if "kicker" in by else ""
    source = f'<p class="src" data-field="source">{by["source"]}</p>' if "source" in by else ""
    items = "".join(f'<li data-field="{f.name}">{escape(f.text)}</li>' for f in rest)
    base = f".k{{{_LABEL};color:var(--c-ink-2)}}{_SOURCE}"

    if plan.chart is not None:  # the claim above, the chart filling the rest
        hsize = _step(head, ((40, "h2"),), "h3")
        html = (
            f'<section class="s"><div class="t">{kicker}'
            f'<h1 class="h" data-field="headline">{head}</h1></div>'
            f'<dd-chart class="ch"></dd-chart>{source}</section>'
        )
        css = (
            ".s{display:grid;grid-template-rows:auto 1fr auto;gap:var(--s-5);"
            "padding:var(--margin)}.t{display:grid;gap:var(--s-3);max-width:1400px}"
            f".h{{{_DISPLAY};font-size:var(--t-{hsize});line-height:var(--lh-display)}}"
            ".ch{min-height:0}" + base
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
            f'<h1 class="h" data-field="headline">{head}</h1></div>'
            f'<ul class="l">{items}</ul>{source}</div></section>'
        )
        css = (
            ".s{display:grid;grid-template-columns:1fr 1fr}"
            ".f{background-color:var(--c-accent);color:var(--c-on-accent);padding:var(--margin);"
            "display:grid;align-content:end;gap:var(--s-3)}"
            f".st{{{_DISPLAY};font-size:var(--t-{size});line-height:var(--lh-display);letter-spacing:-0.02em}}"
            ".lb{font-size:var(--t-body);max-width:600px}"
            ".c{padding:var(--margin);display:grid;grid-template-rows:auto 1fr auto;"
            "gap:var(--s-4)}.t{display:grid;gap:var(--s-3)}"
            f".h{{{_DISPLAY};font-size:var(--t-{hsize});line-height:1.02}}"
            ".l{align-self:end;display:grid}"
            ".l li{font-size:var(--t-body);padding:var(--s-2) 0;"
            "border-top:var(--rule) solid var(--c-rule)}" + base
        )
        return Composed(html, css)

    if rest:  # a ruled list beside the headline
        hsize = _step(head, ((30, "h1"),), "h2")
        cols = "5fr 7fr" if hsize == "h1" else "7fr 5fr"
        html = (
            f'<section class="s"><div class="t">{kicker}'
            f'<h1 class="h" data-field="headline">{head}</h1></div>'
            f'<ul class="l">{items}</ul>{source}</section>'
        )
        css = (
            f".s{{display:grid;grid-template-columns:{cols};grid-template-rows:1fr auto;"
            "column-gap:var(--s-7);row-gap:var(--s-4);padding:var(--margin)}"
            ".t{display:grid;gap:var(--s-3);align-content:start}"
            f".h{{{_DISPLAY};font-size:var(--t-{hsize});line-height:1.02}}"
            ".l{display:grid;align-self:end}"
            ".l li{font-size:var(--t-h3);line-height:1.15;padding:var(--s-4) 0;"
            "border-top:var(--rule) solid var(--c-rule)}"
            ".src{grid-column:1 / 3}" + base
        )
        return Composed(html, css)

    # only a sentence: set it at poster scale against one hard accent bar
    hsize = _step(head, ((36, "d2"), (62, "d3")), "h1")
    html = (
        f'<section class="s">{kicker or "<span></span>"}'
        f'<h1 class="h" data-field="headline">{head}</h1>{source}'
        '<dd-texture class="bar" kind="halftone" tone="accent"></dd-texture></section>'
    )
    css = (
        ".s{display:grid;grid-template-rows:auto 1fr auto;gap:var(--s-4);"
        "padding:var(--margin);padding-right:420px}"
        f".h{{align-self:end;{_DISPLAY};font-size:var(--t-{hsize});line-height:var(--lh-display);"
        "letter-spacing:-0.015em}"
        ".bar{position:absolute;top:0;right:0;width:300px;height:1080px}" + base
    )
    return Composed(html, css)
