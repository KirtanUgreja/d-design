"""Layer 5, the deck review: a designer pins the whole deck on the wall and
looks at it as one piece (research of 2026-10-09: decks read as AI-made when
every slide carries the same weight and structure; a slide is judged against
its neighbours, which a per-slide critic cannot see).

One call sees a contact sheet of every slide and names at most two slides to
redo, each with a note. The improver redoes them with that note; QA keeps a
redo only if it measures no worse. Advice, never control flow."""

from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image, ImageDraw
from pydantic import BaseModel, Field

from engine.llm.openrouter import ModelError, Seam
from lib.result import Err, Result, ok

PROMPT_VERSION = "review.v1"
MAX_REDOS = 2
THUMB = (640, 360)
COLUMNS = 3

SYSTEM = """You are the design director reviewing a finished deck before it goes to the client.
You see every slide on one sheet, in order, each labelled with its id. Judge the DECK, not one
slide: does it have rhythm (a bold opener, a denser middle, an open close)? Does any slide look
like its neighbour, break the deck's style, feel empty or crowded, bury its one idea, or show
THE TELLS OF AN AI-MADE SLIDE (equal boxes, metric tiles, decorative bars, everything centred,
the same structure repeated)?

Name at most two slides that most need redoing, weakest first, each with one note a designer
can act on ("the headline fights the number: make 400+ the hero, headline smaller, top-left").
If the deck already works, name none. Answer as JSON."""


class Redo(BaseModel):
    id: str
    note: str


class Review(BaseModel):
    verdict: str  # one sentence on the deck as a whole
    redo: list[Redo] = Field(default_factory=list)


def sheet(shots: list[tuple[str, Path]]) -> str:
    """Every slide's screenshot on one labelled JPEG, as a data URL."""
    rows = (len(shots) + COLUMNS - 1) // COLUMNS
    w, h, pad, label = THUMB[0], THUMB[1], 16, 34
    board = Image.new("RGB", (COLUMNS * (w + pad) + pad, rows * (h + label + pad) + pad), "white")
    draw = ImageDraw.Draw(board)
    for n, (slide_id, path) in enumerate(shots):
        x = pad + (n % COLUMNS) * (w + pad)
        y = pad + (n // COLUMNS) * (h + label + pad)
        draw.text((x, y + 6), f"{slide_id}  (slide {n + 1})", fill="black")
        if path.exists():
            with Image.open(path) as shot:
                board.paste(shot.convert("RGB").resize(THUMB), (x, y + label))
    out = io.BytesIO()
    board.save(out, "JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode()


async def review(
    seam: Seam, shots: list[tuple[str, Path]], *, prefix: str, model: str, thought: str
) -> Result[Review, ModelError]:
    got = await seam.complete_json(
        "review",
        Review,
        system=SYSTEM,
        user=f"The deck argues: {thought}\nIds in order: {', '.join(s for s, _ in shots)}",
        model=model,
        prefix=prefix,
        prompt_version=PROMPT_VERSION,
        max_tokens=12000,
        images=(sheet(shots),),
    )
    if isinstance(got, Err):
        return got
    known = {s for s, _ in shots}
    redo = [r for r in got.value.redo if r.id in known][:MAX_REDOS]
    return ok(got.value.model_copy(update={"redo": redo}))
