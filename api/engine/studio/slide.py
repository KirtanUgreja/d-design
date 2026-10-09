"""A slide as the studio passes it around, and the contract every answer that
writes one must meet: the rules the designer, the critic and the repair all
read, and the one parser that checks what comes back."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from engine.components import charts, visuals
from engine.compose.document import Frame
from engine.design.theme import Theme
from engine.llm.openrouter import Reply, parse_fenced
from engine.models import SlidePlan
from engine.qa.lint import lint
from engine.qa.sanitize import sanitize
from lib.result import Err, Result, err, ok


@dataclass(frozen=True)
class Composed:
    html: str
    css: str


@dataclass(frozen=True)
class Kept:
    """A finished slide as the worker persists it: enough to resume for free."""

    composed: Composed
    origin: str


def frame(plan: SlidePlan, c: Composed) -> Frame:
    """Charts and visuals are drawn by our code after sanitizing, so QA
    measures them too; an empty visual box the plan did not ask for goes."""
    drawn = charts.fill(c.html, plan.chart)
    drawn = visuals.fill(drawn, plan.visual) if plan.visual else visuals.strip(drawn)
    return Frame(plan.id, drawn, c.css)


PAIRS = (
    "  on --c-ground or --c-surface: --c-ink, or --c-ink-2 for quiet text\n"
    "  on --c-accent: --c-on-accent only, at every size\n"
    "  on --c-ink: --c-ground only"
)

CONTRACT = f"""THE CANVAS: one slide, projected at exactly 1920x1080px.

OUTPUT: one ```html block and one ```css block. Nothing else, unless asked.

HTML
- One root: <section class="s"> … </section>. No <html>, <body>, <style>, <script>, <img>,
  <a>, no style attribute, no id.
- Tags: div section header footer h1 h2 h3 p span strong em small sup sub br hr ul ol li
  blockquote figure figcaption, our components (below) and flat SVG (below).
- Every field you are given appears EXACTLY ONCE, in an element with data-field="<name>", its
  text UNCHANGED. You may wrap words in <em> or <span class="…"> and break lines with <br>.
- Any other visible text is decoration: at most 6 words, in an element with data-deco: a folio
  ("04 — 10"), a giant numeral, a word set huge and cropped, or editorial chrome (tiny
  uppercase labels in the corners: the deck's name, the section, the year). Never invent a
  number, a claim or a caption.
- Attributes: class, data-field, data-deco, data-bleed, and the component attributes below.

OUR COMPONENTS — empty boxes our code fills after you; size and place them with CSS:
- <dd-chart class="…"></dd-chart>: the slide's chart, when it has one. At least 900x480px,
  fully on the canvas: a chart's labels are measured, so it never bleeds.
- <dd-visual class="…"></dd-visual>: a drawn picture of the product (waveform, phone, browser,
  chat, flow), when the slide has one. It is the HERO: big (720x520px or more; a phone at
  least 420x680px). Only a waveform may bleed off an edge; a phone, browser, chat or flow
  has words in it and stays fully on the canvas.
- <dd-image aspect="3:2|2:3|1:1|16:9|4:5" class="…"></dd-image>: the slide's picture, when it
  has one. Size its box to its aspect. Text never sits on it; text near it sits on a solid field.
- <dd-texture kind="…" tone="accent|ink|surface" class="…"></dd-texture>: a flat field or a
  pattern, of a kind THEME TOKENS lists; never under text.
- <dd-glow tone="accent|ink|surface" class="…"></dd-glow>: one soft glow, ONLY when THEME
  TOKENS says this look has one.

FLAT SVG — draw structure, diagrams and abstract product art yourself:
- <svg class="…" viewBox="…"> with g path rect circle ellipse line polyline polygon. Geometry
  attributes only (d, x, y, width, height, rx, ry, cx, cy, r, x1, y1, x2, y2, points,
  transform, viewBox, preserveAspectRatio). No text inside an SVG, no gradients, no filters.
- Colour every shape through a class in your CSS: fill and stroke only var(--c-…) or none.

CSS
- Plain class selectors (and .s itself). No @-rules, no :root/html/body, no nesting, no
  !important, no `content` text.
- Colour only var(--c-…), transparent or currentColor. font-family only var(--f-display),
  var(--f-text), var(--f-label). font-size only a var(--t-…) token. font-weight only
  var(--w-display), var(--w-regular), var(--w-bold). No `font` shorthand.
- Banned: gradients, url(), filter, backdrop-filter, text-shadow, mask, opacity, animation,
  transition, position:fixed, vw/vh. border-radius: 0, 50% or var(--radius). box-shadow:
  only var(--shadow-hard).

TYPOGRAPHY (open-design's craft rules)
- ALL CAPS text always gets letter-spacing of 0.06em to 0.12em; display type 64px and up gets
  var(--track-display) or tighter. Body text at most about 65 characters a line.
- The accent appears at most twice on a slide. About 80% of every slide is neutral.
- Cards only as an UNEQUAL bento grid carrying real numbers or pictures (one large, the rest
  smaller); never equal boxes around bullet points.

READABILITY (measured after you; a failure is sent back)
- All text at least 64px from every edge (var(--margin) is the norm). Text never overlaps text
  and never leaves its box. A headline is at most 4 lines.
- Sizes: headline 56px or more; body 32px or more (--t-body and up); labels 22px or more.
- Text colour by the ground behind it:
{PAIRS}
  --c-accent as text only at 64px or larger and only on --c-ground.
- A flat colour rectangle carries something (a headline, a number, a list, a drawing).
"""


# What makes a slide read as AI-made, from designers' teardowns and Gamma 5's
# own fix for "AI smell" (docs/v4/design-engine.md -> The studio, research of
# 2026-10-09). The art director, the designer and the critic all check it.
AI_TELLS = """THE TELLS OF AN AI-MADE SLIDE — never do these:
- three (or four) equal boxes or cards side by side; dashboard-style metric tiles
- a coloured bar or rule beside every text block; decoration that could be deleted with no loss
- every slide the same weight, the same margins, the same structure with only the words changed
- everything centred; small text floating in a big empty field
- an italic serif word as a flourish in every headline; a pale cream ground by default
- icons or clip art standing in for an idea; a generic picture that could sit in any deck
- a number in a box with a label under it, repeated slide after slide
- a kicker or label that says the headline again in other words; the same label style on
  every slide whatever it says
What a designer does instead: ONE dominant element per slide that the eye lands on first, the rest
clearly demoted; a rhythm across the deck (a bold opener, denser middle, an open close); real
evidence (the product, the data) instead of decoration; whitespace that is one deliberate field."""


# The five dimensions a design is scored on (open-design's critique skill,
# after huashu-design), with its discipline: evidence for every score, the
# worst sustained band, no grade inflation.
SCORING = """Score it on five dimensions, 0-10 each, with one line of evidence naming a specific
element: CONSISTENCY (one direction in every choice), HIERARCHY (a stranger knows what to read
first, second, third), DETAIL (alignment, baselines, leading, spacing rhythm), READABILITY
(legible from the back of a room, nothing cramped), INNOVATION (one move that is not the
median). The score is the worst sustained band, not the average. A 7 means strong; every
score at 7 or more means you are not looking hard enough."""


def fields_text(plan: SlidePlan) -> str:
    return "\n".join(f'- {f.name}: "{f.text}"' for f in plan.fields)


def parser(
    plan: SlidePlan, *, image: bool = False, extra: tuple[str, ...] = ()
) -> Callable[[Reply], Result[tuple[Composed, dict[str, str]], str]]:
    """The one check on an answer that writes a slide: fenced blocks, the
    sanitizer, the CSS lint, every field present, and components only where
    the plan has them. ``extra`` names more blocks to return (a critique)."""
    names = frozenset(f.name for f in plan.fields)

    def parse(reply: Reply) -> Result[tuple[Composed, dict[str, str]], str]:
        blocks = parse_fenced(reply.text, "html", "css", *extra)
        if isinstance(blocks, Err):
            return blocks
        clean = sanitize(blocks.value["html"], names)
        if isinstance(clean, Err):
            return clean
        html = clean.value
        problems = lint(blocks.value["css"])
        problems += [
            f'the field "{n}" has no data-field element'
            for n in names
            if f'data-field="{n}"' not in html
        ]
        for tag, planned in (("dd-chart", plan.chart), ("dd-visual", plan.visual)):
            if planned is not None and f"<{tag}" not in html:
                problems.append(f"this slide has one: place one empty <{tag} class=…>")
            if planned is None and f"<{tag}" in html:
                problems.append(f"this slide has none: remove the <{tag}>")
        if not image and "<dd-image" in html:
            problems.append("this slide has no image: remove the <dd-image>")
        if html.count("<dd-image") > 1:
            problems.append("one <dd-image> at most")
        if problems:
            return err("fix these:\n- " + "\n- ".join(problems[:20]))
        rest = {k: v for k, v in blocks.value.items() if k not in ("html", "css")}
        return ok((Composed(html, blocks.value["css"]), rest))

    return parse


def prefix(theme: Theme) -> str:
    """The stable, cacheable start of every design call for one deck."""
    return f"{CONTRACT}\n{AI_TELLS}\n\nTHEME TOKENS\n{theme.describe()}\n"
