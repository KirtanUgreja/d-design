"""The reference library: strong slides in each visual language, adapted per
slide by the compose model (docs/v4/plan/39-design-reset.md -> Make, 2-3).

A reference is one file, ``library/references/<language>/<shape>-<n>.html``:
line one is an HTML comment holding its metadata as JSON, then a fenced
```html block (the slide contract, ``<section class="s">``) and a fenced ```css
block (theme tokens only). The format is the exemplars' own, so the same
loader rules and the same fill apply.

Every field the shape can hold appears in an element with ``data-field``; an
absent field is removed by ``fill`` without breaking the layout. A reference
never shows sample words: ``fill`` is the only way words reach it.

Pure: reads the library once; usage counts come in from the caller.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from engine.compose.exemplars import fill_html
from engine.llm.openrouter import parse_fenced
from engine.models import SlidePlan
from lib.result import Err

LIBRARY = Path(__file__).resolve().parent.parent.parent / "library" / "references"
KEPT = LIBRARY / "kept.json"

Shape = Literal["cover", "statement", "number", "points", "comparison", "sequence", "chart", "ask"]
ImageSlot = Literal["none", "half", "full", "inset", "background"]

# Every field a reference of a shape must hold (a superset of what plans of
# that shape carry, measured on the 12 bench outlines, 2026-10-08).
FIELDS: dict[str, frozenset[str]] = {
    "cover": frozenset({"kicker", "headline", "source"}),
    "statement": frozenset({"kicker", "headline", "point-1", "stat", "stat-label", "source"}),
    "number": frozenset(
        {"kicker", "headline", "stat", "stat-label", "source", "point-1", "point-2", "point-3"}
    ),
    "points": frozenset(
        {"kicker", "headline", "point-1", "point-2", "point-3", "stat", "stat-label", "source"}
    ),
    "comparison": frozenset(
        {"kicker", "headline", "point-1", "point-2", "point-3", "stat", "stat-label", "source"}
    ),
    "sequence": frozenset({"kicker", "headline", "point-1", "point-2", "point-3"}),
    "chart": frozenset({"kicker", "headline", "stat", "stat-label", "source"}),
    "ask": frozenset({"kicker", "headline", "point-1", "point-2", "point-3", "stat", "stat-label"}),
}
SHAPES: tuple[str, ...] = tuple(FIELDS)
# planner intent -> shape
INTENTS: dict[str, str] = {
    "cover": "cover",
    "statement": "statement",
    "question": "statement",
    "section": "statement",
    "quote": "statement",
    "image-led": "statement",
    "number": "number",
    "number-set": "number",
    "points": "points",
    "team": "points",
    "case": "points",
    "comparison": "comparison",
    "steps": "sequence",
    "timeline": "sequence",
    "chart": "chart",
    "ask": "ask",
}
ASPECTS = ("3:2", "2:3", "1:1", "16:9", "4:5")


class _Meta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: str
    shape: Shape
    idea: str  # the design idea it borrows, one line
    fields: list[str]
    image: ImageSlot = "none"
    variants: list[str] = Field(default_factory=list)  # e.g. mirror, dark-field


@dataclass(frozen=True)
class Reference:
    id: str  # "<language>/<shape>-<n>"
    language: str
    shape: str
    idea: str
    fields: frozenset[str]
    image: str
    variants: tuple[str, ...]
    html: str
    css: str

    def prompt(self, label: str = "Reference") -> str:
        return (
            f"### {label}: {self.id} — {self.idea}\n"
            f"```html\n{self.html}\n```\n```css\n{self.css}\n```"
        )


def _parse(path: Path, language: str) -> Reference:
    text = path.read_text()
    head, _, _ = text.partition("\n")
    meta = _Meta.model_validate(json.loads(head.strip().removeprefix("<!--").removesuffix("-->")))
    blocks = parse_fenced(text, "html", "css")
    if isinstance(blocks, Err):
        raise ValueError(f"{path}: {blocks.error}")  # a broken library is a bug
    if meta.language != language:
        raise ValueError(f"{path}: language {meta.language} in the {language} folder")
    return Reference(
        id=f"{language}/{path.stem}",
        language=language,
        shape=meta.shape,
        idea=meta.idea,
        fields=frozenset(meta.fields),
        image=meta.image,
        variants=tuple(meta.variants),
        html=blocks.value["html"],
        css=blocks.value["css"],
    )


@cache
def load_all(root: Path = LIBRARY) -> tuple[Reference, ...]:
    """Every reference on disk, kept or not (the wall shows them all)."""
    return tuple(
        _parse(path, folder.name)
        for folder in sorted(p for p in root.iterdir() if p.is_dir())
        for path in sorted(folder.glob("*.html"))
    )


@cache
def kept(root: Path = LIBRARY) -> frozenset[str]:
    """The ids the owner kept. No kept.json yet = every reference is kept;
    a dropped reference is never retrieved."""
    path = root / "kept.json"
    if not path.exists():
        return frozenset(r.id for r in load_all(root))
    return frozenset(json.loads(path.read_text()))


def shape_of(plan: SlidePlan) -> str:
    if plan.chart is not None:
        return "chart"
    return INTENTS.get(plan.intent, "statement")


def candidates(language: str, shape: str, *, root: Path = LIBRARY) -> list[Reference]:
    keep = kept(root)
    return [
        r for r in load_all(root) if r.language == language and r.shape == shape and r.id in keep
    ]


def pick(
    language: str,
    plan: SlidePlan,
    *,
    used_in_deck: frozenset[str] = frozenset(),
    usage: Mapping[str, int] | None = None,
    images_left: int = 0,
    root: Path = LIBRARY,
) -> tuple[Reference | None, Reference | None]:
    """The reference for this slide and an alternate. Never one already used
    in this deck while another fits; across decks the least used first; one
    with an image slot only while the deck's image budget lasts. A reference
    must hold every field the slide has."""
    shape = shape_of(plan)
    need = {f.name for f in plan.fields}
    fits = [r for r in candidates(language, shape, root=root) if need <= r.fields]
    if not fits:  # a shape this language lacks: any language's, same shape
        fits = [
            r
            for r in load_all(root)
            if r.shape == shape and need <= r.fields and r.id in kept(root)
        ]
    if images_left <= 0:
        fits = [r for r in fits if r.image == "none"] or fits
    used = usage or {}
    ranked = sorted(fits, key=lambda r: (r.id in used_in_deck, used.get(r.id, 0), r.id))
    first = ranked[0] if ranked else None
    second = ranked[1] if len(ranked) > 1 else None
    return first, second


_IMAGE = re.compile(r"<dd-image\b[^>]*>\s*</dd-image>")


def fill(ref: Reference, words: Mapping[str, str], *, image: bool = True) -> str:
    """The no-model fallback: the reference with the slide's words placed and
    every absent field removed. Design quality, because every reference passed
    QA filled long and short. ``image=False`` takes its image slot out."""
    out = fill_html(ref.html, words)
    return out if image else _IMAGE.sub("", out)


_FIELD = re.compile(r'data-field="([\w-]+)"')


def field_names(html: str) -> frozenset[str]:
    return frozenset(_FIELD.findall(html))
