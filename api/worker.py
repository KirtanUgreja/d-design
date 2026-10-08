"""The worker (docs/v4/engine.md -> Jobs): the one process that holds the model
key and drives Chromium. It claims a job from the file store, heartbeats while
it works, appends events, and persists every slide the moment it is final, so
a worker killed mid-deck is resumed by the next one without paying for any
slide twice. The API never does any of this: it only enqueues and reads.

    cd api && uv run python worker.py

Expected failures become a human message on the deck and an ``error`` event;
never an exception string (the UI shows them). ponytail: one worker process.
"""

from __future__ import annotations

import asyncio
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime

import ops
import settings
from engine import (
    Composed,
    Deck,
    Kept,
    ModelError,
    Seam,
    interview,
    notes,
    pdf,
    pipeline,
    research,
    set_field,
    storyline,
)
from engine.compose import preview
from lib.result import Err
from looks import theme_of, usage, with_language
from store.files import Job, Store

BEAT_S = 10.0

HUMAN = {
    "transport": "The writing service didn't answer. Try again in a minute.",
    "truncated": "The writing service cut its answer short. Try again.",
    "refused": "The writing service declined this brief. Try rewording it.",
    "invalid": "The writing service sent back something we couldn't use. Try again.",
    "repair_exhausted": "The writing service sent back something we couldn't use. Try again.",
    "no_key": "The service isn't set up yet. This one is on us.",
    "budget": "This deck reached its spending cap.",
}


def human(error: ModelError) -> str:
    return HUMAN.get(error.kind, "Something went wrong on our side. Try again.")


def _fail(store: Store, deck: Deck, message: str, code: str) -> None:
    store.update(deck.id, status="error", error=message)
    store.append_event(deck.id, {"type": "error", "code": code, "message": message})


async def run(
    store: Store,
    job: Job,
    *,
    make_seam: Callable[[str], Seam],
    writing: str,
    design: str,
    budget_usd: float,
    image: str = "",
) -> None:
    """Do one job. Every outcome is written to the deck and its event log."""
    deck = store.read(job.deck_id)
    seam = make_seam(deck.id)
    try:
        if job.kind == "interview":
            got = await interview.questions(seam, deck.brief, model=writing)
            if isinstance(got, Err):
                _fail(store, deck, human(got.error), got.error.kind)
                return
            store.save_questions(deck.id, got.value)
            store.update(deck.id, status="interview", error="")
            store.append_event(deck.id, {"type": "questions_ready", "count": len(got.value)})
        elif job.kind == "outline":
            store.update(deck.id, status="outline", error="")
            store.append_event(deck.id, {"type": "stage", "name": "outline", "state": "started"})
            facts = await research.research(
                seam, deck.brief, model=writing, year=datetime.now(UTC).year
            )
            if isinstance(facts, Err):
                _fail(store, deck, human(facts.error), facts.error.kind)
                return
            written = await storyline.write(seam, deck.brief, facts.value, model=writing)
            if isinstance(written, Err):
                _fail(store, deck, human(written.error), written.error.kind)
                return
            deck = store.update(
                deck.id, status="approve", storyline=written.value.story, facts=written.value.facts
            )
            await _previews(store, with_language(store, deck))
            store.append_event(deck.id, {"type": "outline_ready"})
        elif job.kind == "style":
            await _previews(store, deck)
            store.append_event(deck.id, {"type": "style_ready"})
        elif job.kind == "edit":
            await _edit(store, deck, ops.OP.validate_json(job.payload))
        else:
            await _build(
                store,
                deck,
                seam,
                design=design,
                writing=writing,
                budget_usd=budget_usd,
                image_model=image,
            )
    finally:
        store.append_ledger(deck.id, seam.ledger)


async def _build(
    store: Store,
    deck: Deck,
    seam: Seam,
    *,
    design: str,
    writing: str,
    budget_usd: float,
    image_model: str = "",
) -> None:
    story = deck.storyline
    if story is None:
        _fail(store, deck, "Approve an outline first.", "no_outline")
        return
    store.clear_abort(deck.id)
    store.update(deck.id, status="building", error="")
    if not any(s.notes for s in story.slides):  # notes once; a resumed build reuses them
        with_notes = await notes.write(seam, story, model=writing)
        if not isinstance(with_notes, Err):
            story = with_notes.value
            store.update(deck.id, storyline=story)
    slides_dir = store.slides_dir(deck.id)
    deck = with_language(store, deck)
    theme = theme_of(deck)
    _, ref_usage = usage(store)

    def keep(slide_id: str, kept: Kept) -> None:
        store.save_kept(deck.id, slide_id, kept)

    def tell(event: dict[str, object]) -> None:
        store.append_event(deck.id, event)

    built = await pipeline.build(
        seam,
        story,
        theme,
        model=design,
        title=deck.title,
        work_file=str(slides_dir / "qa.html"),
        shots_dir=str(slides_dir),
        budget_usd=budget_usd,
        on_event=tell,
        prebuilt=store.kept(deck.id),
        on_final=keep,
        stop=lambda: store.aborted(deck.id),
        ref_usage=ref_usage,
        image_model=image_model,
    )
    for stray in slides_dir.glob("qa*.html"):
        stray.unlink()
    store.save_export(deck.id, "export-present.html", built.html)
    store.save_export(deck.id, "export-send.html", built.send)
    store.save_export(deck.id, "export.pdf", await pdf.render(built.send))
    aborted = store.aborted(deck.id)
    store.update(deck.id, status="aborted" if aborted else "ready", slides=built.slides)
    if not aborted:
        store.snapshot(deck.id, "Generated")  # the first version undo can return to


async def _previews(store: Store, deck: Deck) -> None:
    """The style card's three thumbnails, filled from the deck's references
    with its real words. No model call. A failure leaves the card without
    thumbnails, never the outline without its gate."""
    story = deck.storyline
    if story is None:
        return
    shots = store.slides_dir(deck.id) / "style"
    for old in shots.glob("preview-*.png"):
        old.unlink()
    names = await preview.render(theme_of(deck), story, shots)
    for name in names:
        store.save_export(deck.id, name, (shots / name).read_bytes())


async def _edit(store: Store, deck: Deck, op: ops.Op) -> None:
    """One editor operation, no model: change, run QA again on what it
    touched, re-export, and record a version. A slide the change breaks is
    kept and flagged, with "Fit to slide" offered; never saved silently."""
    story = deck.storyline
    if story is None or deck.status != "ready":
        _fail(store, deck, "This deck can't be edited until it is built.", "not_ready")
        return
    kept = store.kept(deck.id)
    plans = list(story.slides)
    by = {p.id: p for p in plans}
    touched: list[str] = []
    if isinstance(op, ops.TextEdit):
        plan, slide = by.get(op.slide), kept.get(op.slide)
        html = set_field(slide.composed.html, op.field, op.text) if slide else None
        if plan is None or slide is None or html is None:
            store.append_event(
                deck.id, {"type": "edit_refused", "message": "That text isn't on this slide."}
            )
            return
        fields = [
            f.model_copy(update={"text": op.text}) if f.name == op.field else f for f in plan.fields
        ]
        by[plan.id] = plan.model_copy(update={"fields": fields})
        kept[plan.id] = Kept(Composed(html, slide.composed.css), slide.origin)
        touched = [plan.id]
    elif isinstance(op, ops.Reorder):
        ids = [p.id for p in plans]
        if sorted(op.slides) != sorted(ids) or op.slides[0] != ids[0] or op.slides[-1] != ids[-1]:
            store.append_event(
                deck.id,
                {"type": "edit_refused", "message": "Keep the cover first and the ask last."},
            )
            return
        plans = [by[i] for i in op.slides]
    elif isinstance(op, ops.Delete):
        ends = (plans[0].id, plans[-1].id)
        if op.slide in ends or op.slide not in by or len(plans) <= 3:
            store.append_event(
                deck.id,
                {
                    "type": "edit_refused",
                    "message": "The cover and the ask stay, and a deck keeps three slides.",
                },
            )
            return
        plans = [p for p in plans if p.id != op.slide]
        kept.pop(op.slide, None)
        (store.slides_dir(deck.id) / f"{op.slide}.json").unlink(missing_ok=True)
    elif isinstance(op, ops.Recolour):
        deck = deck.model_copy(update={"palette_nonce": deck.palette_nonce + 1})
        touched = [p.id for p in plans]
    else:  # Fit
        if op.slide not in by:
            store.append_event(
                deck.id, {"type": "edit_refused", "message": "That slide isn't in this deck."}
            )
            return
        theme = theme_of(deck)
        kept[op.slide] = pipeline.code_built(by[op.slide], theme)
        touched = [op.slide]
    plans = [by.get(p.id, p) for p in plans]
    theme = theme_of(deck)
    slides_dir = store.slides_dir(deck.id)
    fresh = await pipeline.remeasure(
        theme,
        [p for p in plans if p.id in touched],
        kept,
        work_file=str(slides_dir / "qa-edit.html"),
        shots_dir=str(slides_dir),
    )
    (slides_dir / "qa-edit.html").unlink(missing_ok=True)
    old = {s.id: s for s in deck.slides}
    slides = [fresh.get(p.id) or old[p.id] for p in plans if p.id in old or p.id in fresh]
    for sid in touched:
        store.save_kept(deck.id, sid, kept[sid])
    present, send = pipeline.export(theme, plans, kept, deck.title)
    store.save_export(deck.id, "export-present.html", present)
    store.save_export(deck.id, "export-send.html", send)
    store.save_export(deck.id, "export.pdf", await pdf.render(send))
    store.update(
        deck.id,
        storyline=story.model_copy(update={"slides": plans}),
        slides=slides,
        palette_nonce=deck.palette_nonce,
    )
    store.snapshot(deck.id, ops.LABEL[op.kind])
    flagged = [s for s in touched if fresh[s].qa.status != "passed"]
    store.append_event(
        deck.id, {"type": "edit_done", "label": ops.LABEL[op.kind], "flagged": flagged}
    )


async def _beating(store: Store, job: Job, work: asyncio.Task[None]) -> None:
    """Beat every BEAT_S until the work ends, and not a moment longer."""
    while not work.done():
        store.beat(job)
        await asyncio.wait({work}, timeout=BEAT_S)


async def once(
    store: Store,
    *,
    make_seam: Callable[[str], Seam],
    writing: str,
    design: str,
    budget_usd: float,
    image: str = "",
) -> bool:
    """Claim and do one job; False when the queue is empty."""
    store.requeue_stale()
    job = store.claim()
    if job is None:
        return False
    work = asyncio.create_task(
        run(
            store,
            job,
            make_seam=make_seam,
            writing=writing,
            design=design,
            budget_usd=budget_usd,
            image=image,
        )
    )
    await asyncio.gather(work, _beating(store, job, work))
    store.finish(job)
    return True


def main() -> int:
    cfg = settings.load()
    store = Store(cfg.data_dir)
    print(f"worker: {cfg.data_dir}", flush=True)
    while True:
        try:
            did = asyncio.run(
                once(
                    store,
                    make_seam=lambda deck_id: Seam(api_key=cfg.openrouter_api_key, deck_id=deck_id),
                    writing=cfg.model_writing,
                    design=cfg.model_design,
                    budget_usd=cfg.deck_budget_usd,
                    image=cfg.model_image,
                )
            )
        except Exception as e:
            print(f"worker: job failed with {type(e).__name__}", flush=True)  # never content
            did = True
        if not did:
            time.sleep(1.0)


if __name__ == "__main__":
    sys.exit(main())
