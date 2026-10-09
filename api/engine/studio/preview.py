"""The style preview at the outline gate: three slides of the deck (the cover,
a telling middle slide and the ask) in the deck's look, drawn by the
code-built layout with its real words. No model call, so it is free and can
be redrawn for Another style or new colours. The designed deck goes further;
this shows its type and colour.

One generated style, changeable; never a menu (owner, 2026-10-05).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.compose.document import Frame
from engine.design import languages
from engine.design.theme import Theme
from engine.models import SlidePlan, Storyline
from engine.qa import browser
from engine.studio.design import fallback

PREVIEWS = 3


@dataclass(frozen=True)
class Card:
    """What the style card shows beside the thumbnails."""

    language: str
    name: str
    idea: str
    display: str
    text: str
    colors: dict[str, str]
    image_style: str


def card(theme: Theme) -> Card:
    lang = languages.get(theme.language) if theme.language else None
    keep = ("ground", "surface", "ink", "accent")
    return Card(
        language=theme.language,
        name=lang.name if lang else "",
        idea=lang.idea if lang else "",
        display=theme.display.family,
        text=theme.text.family,
        colors={k: v for k, v in theme.colors.items() if k in keep},
        image_style=theme.look.get("image", "") if lang and lang.image.appetite else "",
    )


def chosen(story: Storyline) -> list[SlidePlan]:
    """The cover, the most telling middle slide (a number if there is one) and the ask."""
    plans = [p for p in story.slides if p.chart is None]
    if len(plans) <= PREVIEWS:
        return plans
    middle = plans[1:-1]
    pick = next((p for p in middle if any(f.name == "stat" for f in p.fields)), middle[0])
    return [plans[0], pick, plans[-1]]


async def render(theme: Theme, story: Storyline, shots_dir: Path) -> list[str]:
    """Draw the previews as ``preview-<n>.png`` in ``shots_dir``; return the
    names drawn, in order."""
    frames: list[Frame] = []
    fields: dict[str, dict[str, str]] = {}
    for n, plan in enumerate(chosen(story), start=1):
        plain = plan.model_copy(update={"visual": None})  # drawn in the deck, not here
        made = fallback(plain, theme)
        sid = f"preview-{n}"
        frames.append(Frame(sid, made.html, made.css))
        fields[sid] = {f.name: f.text for f in plan.fields}
    if not frames:
        return []
    shots_dir.mkdir(parents=True, exist_ok=True)  # noqa: ASYNC240 - one local folder
    await browser.measure(theme, frames, fields, str(shots_dir / "preview.html"), str(shots_dir))
    (shots_dir / "preview.html").unlink(missing_ok=True)
    return [f"{f.slide_id}.png" for f in frames if (shots_dir / f"{f.slide_id}.png").exists()]
