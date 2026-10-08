"""Record one real run as a fixture bundle (docs/design/principles.md § 7:
"the event log is worth recording and versioning from the first good bench run").

The UI prototype (phase 30) and, later, the homepage replay play it back
client-side: the same events at the same times, so it looks like a live
generation because it was one. Nothing in the bundle is invented: the
questions, outline, looks, slides, timings and the one before/after are all
real outputs.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from benchtools import files
from engine import Brief, Fact, Seam, Storyline, interview, pipeline
from engine.compose import author, references
from engine.design.sampler import look_for
from engine.design.theme import Theme
from engine.design.theme import build as build_theme
from engine.export import pdf as pdf_export
from engine.models import SlidePlan
from engine.qa import browser
from lib.result import Err

WEB = Path(__file__).resolve().parent.parent.parent / "web" / "public" / "fixtures"


def _look(theme: Theme, tile_png: list[str]) -> dict[str, object]:
    return {
        "id": theme.id,
        "look": theme.look,
        "tiles": tile_png,
        "fonts": [theme.display.family, theme.text.family, theme.label.family],
    }


async def record(
    seam: Seam,
    brief: Brief,
    story: Storyline,
    facts: list[Fact],
    *,
    writing: str,
    design: str,
) -> Path:
    out = WEB / brief.id
    if out.exists():
        shutil.rmtree(out)
    (out / "slides").mkdir(parents=True)

    qs = await interview.questions(seam, brief, model=writing)
    questions = [] if isinstance(qs, Err) else [q.model_dump() for q in qs.value]

    brand = brief.brand.colors[0] if brief.brand and brief.brand.colors else None
    # One look, generated from the deck's own words; never a menu of three.
    chosen = build_theme(
        look_for(
            brief.id,
            deck_type=brief.deck_type,
            tone=brief.tone,
            words=f"{brief.prompt} {story.governing_thought}",
            brand_hex=brand,
        )
    )
    looks = [_look(chosen, [])]
    events: list[dict[str, object]] = []
    archive = files.load_archive()
    built = await pipeline.build(
        seam,
        story,
        chosen,
        model=design,
        title=brief.prompt.split(".")[0],
        work_file=str(out / "slides" / "qa.html"),
        shots_dir=str(out / "slides"),
        budget_usd=0.5,
        archive=archive,
        on_event=events.append,
    )
    files.save_archive(archive)
    for stray in (out / "slides").glob("qa*.html"):
        stray.unlink()
    (out / "present.html").write_text(built.html)
    (out / "send.html").write_text(built.send)
    (out / "deck.pdf").write_bytes(await pdf_export.render(built.send))

    # One real before/after for the editor: slide 2 recomposed from another reference.
    before = built.slides[1]
    plan: SlidePlan = next(p for p in story.slides if p.id == before.id)
    # A different reference from the deck's language, never the one it used.
    other, _ = references.pick(chosen.language, plan, used_in_deck=frozenset({before.reference}))
    alt = await author.compose(
        seam,
        chosen,
        plan,
        model=design,
        position=2,
        total=len(story.slides),
        thought=story.governing_thought,
        reference=other,
    )
    proposal: dict[str, object] | None = None
    if not isinstance(alt, Err):
        frame = pipeline._frame(plan, alt.value)
        frame = type(frame)(f"{before.id}-alt", frame.html, frame.css)
        measured = await browser.measure(
            chosen,
            [frame],
            {frame.slide_id: before.fields},
            str(out / "slides" / "alt.html"),
            str(out / "slides"),
        )
        (out / "slides" / "alt.html").unlink(missing_ok=True)
        if not measured[frame.slide_id].errors:
            proposal = {
                "slide_id": before.id,
                "instruction": "Try a different layout",
                "after": f"slides/{frame.slide_id}.png",
            }

    manifest = {
        "brief": brief.model_dump(mode="json"),
        "questions": questions,
        "outline": story.model_dump(mode="json"),
        "facts": [f.model_dump(mode="json") for f in facts],
        "looks": looks,
        "chosen": chosen.id,
        "events": events,
        "slides": [
            {
                "id": s.id,
                "thumb": f"slides/{s.id}.png",
                "status": s.qa.status,
                "origin": s.origin,
                "fields": s.fields,
            }
            for s in built.slides
        ],
        "proposal": proposal,
        "exports": {"present": "present.html", "send": "send.html", "pdf": "deck.pdf"},
        "cost_usd": round(seam.spent_usd, 4),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    return out
