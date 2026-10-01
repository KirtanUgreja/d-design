"""Speaker notes: one call after the outline is approved, so iterating on the
outline stays cheap (docs/v4/content.md -> Storyline, `notes`).

Every slide gets 40-120 words in a spoken register that add what the slide
does not say. A note too short, too long or repeating its headline is sent
back once with the reason.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from pydantic import BaseModel, ValidationError

from engine.llm.openrouter import ModelError, Reply, Seam, parse_fenced
from engine.models import Storyline
from lib.result import Err, Result, err, ok

PROMPT_VERSION = "notes.v1"
MIN_WORDS, MAX_WORDS = 40, 120
MAX_OVERLAP = 0.5

SYSTEM = f"""You write speaker notes for an approved presentation outline. For every slide, write
what the speaker says aloud: {MIN_WORDS}-{MAX_WORDS} words, spoken register, first person plural.
Add what the slide does not say — the story behind the claim, the example, the transition to the
next slide. Never read the headline back. Name the full source when the slide cites one. Never
invent a number, a customer or a quote that is not on the slides.

Answer with one ```json block: {{"notes": [{{"slide_id": "s01", "text": "..."}}]}}"""


class _Note(BaseModel):
    slide_id: str
    text: str


class _Notes(BaseModel):
    notes: list[_Note]


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", text.lower()))


def overlap(a: str, b: str) -> float:
    """Jaccard similarity of the two texts' word sets."""
    x, y = _words(a), _words(b)
    return len(x & y) / len(x | y) if x | y else 0.0


def _outline(story: Storyline) -> str:
    lines = [f"Governing thought: {story.governing_thought}"]
    for s in story.slides:
        lines.append(f"\n{s.id} ({s.beat})")
        lines += [f"  {f.name}: {f.text}" for f in s.fields]
    return "\n".join(lines)


def _parser(story: Storyline) -> Callable[[Reply], Result[dict[str, str], str]]:
    headlines = {
        s.id: next((f.text for f in s.fields if f.name == "headline"), "") for s in story.slides
    }

    def parse(reply: Reply) -> Result[dict[str, str], str]:
        blocks = parse_fenced(reply.text, "json")
        if isinstance(blocks, Err):
            return blocks
        try:
            notes = {
                n.slide_id: n.text for n in _Notes.model_validate_json(blocks.value["json"]).notes
            }
        except (ValidationError, json.JSONDecodeError) as exc:
            return err(str(exc)[:1000])
        problems = [f"{sid}: missing" for sid in headlines if sid not in notes]
        for sid, text in notes.items():
            if sid not in headlines:
                continue
            n = len(text.split())
            if not MIN_WORDS <= n <= MAX_WORDS:
                problems.append(f"{sid}: {n} words; write {MIN_WORDS}-{MAX_WORDS}")
            if overlap(text, headlines[sid]) >= MAX_OVERLAP:
                problems.append(f"{sid}: repeats its headline; add what the slide does not say")
        if problems:
            return err("fix these notes:\n- " + "\n- ".join(problems))
        return ok({sid: notes[sid] for sid in headlines})

    return parse


async def write(seam: Seam, story: Storyline, *, model: str) -> Result[Storyline, ModelError]:
    parse = _parser(story)
    result = await seam.complete_text(
        "notes",
        parse,
        system=SYSTEM,
        user=_outline(story),
        model=model,
        prompt_version=PROMPT_VERSION,
        max_tokens=6000,
    )
    if isinstance(result, Err):
        return result
    notes = result.value
    slides = [s.model_copy(update={"notes": notes[s.id]}) for s in story.slides]
    return ok(story.model_copy(update={"slides": slides}))
