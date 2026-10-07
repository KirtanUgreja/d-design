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

import settings
from engine import (
    Deck,
    Kept,
    ModelError,
    Seam,
    build_theme,
    interview,
    look_for,
    notes,
    pdf,
    pipeline,
    research,
    storyline,
)
from lib.result import Err
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
            store.update(
                deck.id, status="approve", storyline=written.value.story, facts=written.value.facts
            )
            store.append_event(deck.id, {"type": "outline_ready"})
        else:
            await _build(store, deck, seam, design=design, writing=writing, budget_usd=budget_usd)
    finally:
        store.append_ledger(deck.id, seam.ledger)


async def _build(
    store: Store, deck: Deck, seam: Seam, *, design: str, writing: str, budget_usd: float
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
    look = look_for(
        deck.id,
        deck_type=deck.brief.deck_type,
        tone=deck.brief.tone,
        words=deck.brief.prompt,
        nonce=deck.look_nonce,
    )
    slides_dir = store.slides_dir(deck.id)

    def keep(slide_id: str, kept: Kept) -> None:
        store.save_kept(deck.id, slide_id, kept)

    def tell(event: dict[str, object]) -> None:
        store.append_event(deck.id, event)

    built = await pipeline.build(
        seam,
        story,
        build_theme(look),
        model=design,
        title=deck.title,
        work_file=str(slides_dir / "qa.html"),
        shots_dir=str(slides_dir),
        budget_usd=budget_usd,
        on_event=tell,
        prebuilt=store.kept(deck.id),
        on_final=keep,
        stop=lambda: store.aborted(deck.id),
    )
    for stray in slides_dir.glob("qa*.html"):
        stray.unlink()
    store.save_export(deck.id, "export-present.html", built.html)
    store.save_export(deck.id, "export-send.html", built.send)
    store.save_export(deck.id, "export.pdf", await pdf.render(built.send))
    aborted = store.aborted(deck.id)
    store.update(deck.id, status="aborted" if aborted else "ready", slides=built.slides)


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
                )
            )
        except Exception as e:
            print(f"worker: job failed with {type(e).__name__}", flush=True)  # never content
            did = True
        if not did:
            time.sleep(1.0)


if __name__ == "__main__":
    sys.exit(main())
