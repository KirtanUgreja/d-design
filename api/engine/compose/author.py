"""Compose one slide: the model writes HTML and CSS inside the theme.

The answer is parsed, sanitized and linted before it is accepted, so the
seam's one repair is spent on anything those refuse. Browser defects are a
second, separate repair (``repair``), because they need a render to find.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from html import escape

from engine.compose.exemplars import load_all
from engine.design.theme import Theme
from engine.llm.openrouter import ModelError, Reply, Seam, parse_fenced
from engine.models import Defect, SlidePlan
from engine.qa.lint import lint
from engine.qa.sanitize import sanitize
from lib.result import Err, Result, err, ok

PROMPT_VERSION = "compose.v1"

RULES = """You are a senior editorial designer. You design ONE presentation slide as HTML and CSS.
The slide is projected at exactly 1920x1080px. It must look designed by a person with a point of
view: confident scale contrast, a clear grid, deliberate empty space. It must not look like an
AI-made or template slide.

OUTPUT: exactly one ```html block and one ```css block. Nothing else.

HTML CONTRACT
- One root: <section class="s"> … </section>.
  No <html>, <body>, <style>, <script>, <img>, <a>, <svg>.
- Allowed tags: div section header footer h1 h2 h3 p span strong em small sup sub br hr ul ol li
  blockquote figure figcaption dd-texture.
- Every field you are given appears EXACTLY ONCE, in an element with data-field="<name>", with its
  text UNCHANGED. You may wrap words in <em> or <span class="…"> for emphasis and use <br>. You may
  not add, drop or rewrite words.
- Any other visible text must be decoration: at most 3 words, in an element with data-deco
  (a folio like "04", a big numeral). Do not invent labels, captions or numbers.
- <dd-texture kind="solid|halftone|hatch|grid" tone="accent|ink|surface"></dd-texture> is an empty
  block of flat colour or pattern. Size and place it with a class. Use at most two.
- Attributes allowed: class, data-field, data-deco, data-layer, data-bleed, and kind/tone on
  dd-texture. No style attribute, no id.

CSS CONTRACT
- Plain class selectors. No @-rules, no :root/html/body/:host, no nesting, no !important.
- Colour: only var(--c-…) tokens (or transparent / currentColor). Never a hex, rgb(), or a name.
- font-family: only var(--f-display), var(--f-text) or var(--f-label).
  font-size: only a var(--t-…) token. font-weight: only var(--w-display), var(--w-regular),
  var(--w-bold). Set them as separate properties — the `font` shorthand is banned.
- Banned: gradients, url(), filter, backdrop-filter, text-shadow, mask, opacity, animation,
  transition, position:fixed, vw/vh units, text in `content`.
- border-radius: only 0, 50% or var(--radius). box-shadow: only var(--shadow-hard).
- The root .s is 1920x1080 with overflow hidden. Layout (grid, flex, px positions, sizes) is yours.

DESIGN RULES
- Keep all text at least 64px from every edge; normally use var(--margin).
- Sizes: the headline at least 56px; body text at least 32px (--t-body or larger);
  labels, kickers and sources at least 22px (--t-label).
- Text must never overlap other text and never run outside its box. Long headlines need a smaller
  --t- step or a wider box: at most 4 lines, never one word per line.
- Contrast: --c-ink or --c-ink-2 on --c-ground/--c-surface; --c-on-accent on --c-accent;
  --c-ground on --c-ink. Use --c-accent as a TEXT colour only at 64px or larger.
- Make one thing on the slide much bigger than everything else. Align to a grid. Use rules
  (border with var(--rule)) and flat colour fields instead of boxes.
- NEVER: cards or boxes around each point, rounded panels, icon rows, pills or badges, drop
  shadows, centred-everything layouts, emoji, numbered circles.
"""


@dataclass(frozen=True)
class Composed:
    html: str
    css: str


def prefix(theme: Theme) -> str:
    """The stable, cacheable part of every compose call for one deck."""
    pack = "\n\n".join(e.prompt() for e in load_all())
    return (
        f"{RULES}\nTHEME TOKENS\n{theme.describe()}\n\n"
        "EXEMPLARS — compositions that pass every check. They show the contract and the level of "
        "craft. Learn from them; do not copy one. Compose for THIS slide's content.\n\n"
        f"{pack}"
    )


def _fields(plan: SlidePlan) -> str:
    return "\n".join(f'- {f.name}: "{f.text}"' for f in plan.fields)


def _parser(plan: SlidePlan) -> Callable[[Reply], Result[Composed, str]]:
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
    previous: str,
) -> Result[Composed, ModelError]:
    differ = (
        f"; the previous slide was '{previous}', so this one must look different.\n"
        if previous
        else ".\n"
    )
    user = (
        f"Slide {position} of {total}. The deck argues: {thought}\n"
        f"This slide's job: {plan.intent} ({plan.beat}).\n"
        f"Build it as a '{plan.archetype}' composition" + differ + f"\nFields:\n{_fields(plan)}"
    )
    return await seam.complete_text(
        "compose",
        _parser(plan),
        system="Follow the contract exactly.",
        user=user,
        model=model,
        prefix=prefix(theme),
        prompt_version=PROMPT_VERSION,
        max_tokens=12000,
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
        f"Defects:\n{listed}\n\nFields (text must stay unchanged):\n{_fields(plan)}\n\n"
        f"```html\n{current.html}\n```\n```css\n{current.css}\n```"
    )
    return await seam.complete_text(
        "repair",
        _parser(plan),
        system="Follow the contract exactly.",
        user=user,
        model=model,
        prefix=prefix(theme),
        prompt_version=PROMPT_VERSION,
        max_tokens=12000,
        reasoning="low",
        slide_id=plan.id,
    )


def fallback(plan: SlidePlan) -> Composed:
    """A plain composition built by code from the slide's fields. It is the
    last rung before a flag: not inspired, never broken.

    ponytail: one generic stack. Ceiling: every fallback slide looks alike.
    Upgrade path: fill the matching exemplar per archetype (phase 25).
    """
    by = {f.name: f.text for f in plan.fields}
    head = by.get("headline", "")
    size = "h1" if len(head.split()) <= 9 else "h2"
    parts = ['<section class="s">']
    if "kicker" in by:
        parts.append(f'<p class="k" data-field="kicker">{escape(by["kicker"])}</p>')
    parts.append(f'<h1 class="h" data-field="headline">{escape(head)}</h1>')
    rest = [f for f in plan.fields if f.name not in ("kicker", "headline", "source")]
    if rest:
        parts.append('<div class="r">')
        parts += [f'<p data-field="{f.name}">{escape(f.text)}</p>' for f in rest]
        parts.append("</div>")
    if "source" in by:
        parts.append(f'<p class="src" data-field="source">{escape(by["source"])}</p>')
    parts.append("</section>")
    css = (
        ".s{display:grid;grid-template-rows:auto auto 1fr auto;gap:var(--s-4);"
        "padding:var(--margin)}"
        ".k{font-family:var(--f-label);font-size:var(--t-label);color:var(--c-ink-2)}"
        f".h{{font-family:var(--f-display);font-weight:var(--w-display);font-size:var(--t-{size});"
        "line-height:1.02;max-width:1400px}"
        ".r{align-self:end;display:grid;border-top:var(--rule) solid var(--c-rule)}"
        ".r p{font-size:var(--t-body);padding:var(--s-3) 0;"
        "border-bottom:var(--rule) solid var(--c-rule)}"
        ".src{font-family:var(--f-label);font-size:var(--t-label);color:var(--c-ink-2)}"
    )
    return Composed("".join(parts), css)
