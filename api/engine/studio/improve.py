"""Layer 4, the improver: a creative director looks at the slide as it was
rendered (a screenshot, not the code alone), says what is weak, and
redesigns it. The redesign is kept only if QA measures it no worse, so the
improver can raise the ceiling but never break the floor."""

from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image

from engine.llm.openrouter import ModelError, Seam
from engine.models import Defect, SlidePlan
from engine.studio.direct import SlideDirection
from engine.studio.slide import Composed, fields_text, parser
from lib.result import Err, Result, ok

PROMPT_VERSION = "improve.v2"  # v2: names the AI tells it sees
SHOT_WIDTH = 1280  # what the critic sees: enough for layout, a third of the tokens

SYSTEM = """You are the creative director. A designer made this slide; you see it rendered
at 1920x1080 and you see its code. Your standard: a slide a top studio would put in its
portfolio. Not "fine". Not a template.

First, a critique of at most five short lines: what is weak in hierarchy (is there one clear
hero?), scale contrast, use of the canvas (dead space, cramped areas, things floating),
alignment, boldness, and every one of THE TELLS OF AN AI-MADE SLIDE you can see in it.

Then REDESIGN it: return the complete html and css of the better slide. Make the changes the
critique calls for — usually bigger and bolder, fewer competing elements, a stronger grid, a
colour field or a flat SVG drawing that makes the idea visible. Keep every field's text
exactly. Keep the chart, visual and picture boxes the slide has. Fix any measured defect
listed. Follow the contract exactly.

Answer with three fenced blocks: ```critique, ```html and ```css."""


def shot(path: str | Path) -> str:
    """A rendered slide as a small JPEG data URL for the critic."""
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        rgb.thumbnail((SHOT_WIDTH, SHOT_WIDTH))
        out = io.BytesIO()
        rgb.save(out, "JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode()


async def improve(
    seam: Seam,
    plan: SlidePlan,
    current: Composed,
    screenshot: str,
    defects: list[Defect],
    direction: SlideDirection | None,
    *,
    prefix: str,
    model: str,
    neighbours: str = "",
    note: str = "",
) -> Result[tuple[Composed, str], ModelError]:
    """The redesign and its critique. ``screenshot`` is a data URL (shot())."""
    measured = "\n".join(
        f"- {d.code} {d.field or 'slide'}: measured {d.measured}; required {d.threshold}"
        for d in defects[:12]
    )
    user = (
        (f"The design director sent this slide back: {note}\n\n" if note else "")
        + (f"The art director's plan for it: {direction.idea}\n\n" if direction else "")
        + (f"Its neighbours in the deck: {neighbours}\n\n" if neighbours else "")
        + (f"Measured defects to fix:\n{measured}\n\n" if measured else "")
        + f"Fields (text must stay unchanged):\n{fields_text(plan)}\n\n"
        f"```html\n{current.html}\n```\n```css\n{current.css}\n```"
    )
    got = await seam.complete_text(
        "improve",
        parser(plan, image="<dd-image" in current.html, extra=("critique",)),
        system=SYSTEM,
        user=user,
        model=model,
        prefix=prefix,
        prompt_version=PROMPT_VERSION,
        max_tokens=32000,
        reasoning="low",
        slide_id=plan.id,
        images=(screenshot,),
    )
    if isinstance(got, Err):
        return got
    composed, rest = got.value
    return ok((composed, rest.get("critique", "").strip()))
