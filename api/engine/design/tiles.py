"""Style tiles: each look shown as two exemplar compositions filled with the
deck's real words (docs/v4/design-engine.md -> "Style tiles"). $0, a few
seconds in Chromium. The real slides are composed after the pick.

- A field the deck has no words for is removed rather than keeping the
  exemplar's sample text: a preview must never show a number the user did not give.
- Each of the three looks starts from different exemplars, so a trio differs in
  composition and not only in type and colour; textures take the look's motif.
- A tile that fails QA is replaced by the next exemplar.
"""

from __future__ import annotations

import html
import re

from engine.compose.document import Frame
from engine.compose.exemplars import Exemplar, load_all
from engine.design.theme import Theme
from engine.models import Storyline
from engine.qa import browser

COVERS = ("poster-1", "corner-1", "poster-2", "band-1", "corner-2")


def fill(ex: Exemplar, words: dict[str, str], tile_id: str, texture: str) -> Frame:
    """The exemplar with each data-field's text replaced by the deck's words,
    and its pattern textures set to the look's motif."""

    def swap(m: re.Match[str]) -> str:
        text = words.get(m.group(3), "")
        # No words for this field: drop the element, not just its text.
        return f"{m.group(1)}{html.escape(text)}{m.group(4)}" if text else ""

    out = re.sub(
        r'(<(\w+)\b[^>]*\bdata-field="([\w-]+)"[^>]*>)(?:.*?)(</\2>)', swap, ex.html, flags=re.S
    )
    # The exemplar's decorations ("14", "03") are its own; a preview shows none.
    out = re.sub(r"<(\w+)\b[^>]*\bdata-deco\b[^>]*>.*?</\1>", "", out, flags=re.S)
    out = re.sub(r'kind="(?!solid)[\w-]+"', f'kind="{texture}"', out)
    return Frame(tile_id, out, ex.css)


def _words(story: Storyline, index: int) -> dict[str, str]:
    slide = story.slides[min(index, len(story.slides) - 1)]
    return {f.name: f.text for f in slide.fields}


def _candidates(story: Storyline, variant: int) -> list[tuple[Exemplar, Exemplar, int]]:
    library = {e.id: e for e in load_all()}
    second_index = next((i for i, s in enumerate(story.slides) if i and len(s.fields) > 2), 1)
    words = _words(story, second_index)
    seconds = sorted(
        (e for e in library.values() if not e.id.startswith("poster")),
        key=lambda e: (-len(set(e.fields) & set(words)), len(set(e.fields) - set(words)), e.id),
    )[:6]
    covers = [library[c] for c in COVERS if c in library]
    return [
        (
            covers[(variant + n) % len(covers)],
            seconds[(variant * 2 + n) % len(seconds)],
            second_index,
        )
        for n in range(3)
    ]


async def render(
    theme: Theme, story: Storyline, variant: int, work_file: str, shots_dir: str
) -> tuple[list[Frame], list[str]]:
    """Two QA-clean tiles for one look, or the last attempt and its errors."""
    texture = next((k for k in theme.textures if k != "solid"), "halftone")
    frames: list[Frame] = []
    errors: list[str] = []
    for cover, second, index in _candidates(story, variant):
        frames = [
            fill(cover, _words(story, 0), f"{theme.id}-t1", texture),
            fill(second, _words(story, index), f"{theme.id}-t2", texture),
        ]
        fields = {
            frames[0].slide_id: {k: v for k, v in _words(story, 0).items() if k in cover.fields},
            frames[1].slide_id: {
                k: v for k, v in _words(story, index).items() if k in second.fields
            },
        }
        measured = await browser.measure(theme, frames, fields, work_file, shots_dir)
        errors = [
            f"{k}: {sorted({d.code for d in m.errors})}"
            for k, m in measured.items()
            if m.errors or not m.measured
        ]
        if not errors:
            break
    return frames, errors
