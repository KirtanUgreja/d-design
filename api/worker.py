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
import json
import re
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
from engine.components import images as pictures
from engine.components import logo as logos
from engine.models import Pasted, SlidePlan
from engine.qa.sanitize import sanitize
from engine.studio import design as designer
from engine.studio.slide import prefix
from lib.result import Err
from looks import theme_of, with_language
from store.files import Job
from store.tenant import AnyStore, open_store

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


def _fail(store: AnyStore, deck: Deck, message: str, code: str) -> None:
    store.update(deck.id, status="error", error=message)
    store.append_event(deck.id, {"type": "error", "code": code, "message": message})


async def run(
    store: AnyStore,
    job: Job,
    *,
    make_seam: Callable[[str], Seam],
    writing: str,
    design: str,
    budget_usd: float,
    image: str = "",
    cheap: str = "",
) -> None:
    """Do one job. Every outcome is written to the deck and its event log.
    ``cheap`` writes the interview and the notes; empty = ``writing``."""
    deck = store.read(job.deck_id)
    seam = make_seam(deck.id)
    try:
        if job.kind == "interview":
            got = await interview.questions(seam, deck.brief, model=cheap or writing)
            if isinstance(got, Err):
                _fail(store, deck, human(got.error), got.error.kind)
                return
            store.save_questions(deck.id, got.value)
            store.update(deck.id, status="interview", error="")
            store.append_event(deck.id, {"type": "questions_ready", "count": len(got.value)})
        elif job.kind == "outline":
            # A change in words to an outline the person already has: kept in
            # the brief, so research looks for it and a later rewrite keeps it.
            change = json.loads(job.payload).get("change", "") if job.payload else ""
            current = deck.storyline if change else None
            if change:
                asked = Pasted(title="Asked for in the outline", text=change)
                deck = store.update(
                    deck.id,
                    brief=deck.brief.model_copy(update={"pasted": [*deck.brief.pasted, asked]}),
                )
            store.update(deck.id, status="outline", error="")
            store.append_event(deck.id, {"type": "stage", "name": "outline", "state": "started"})
            facts = await research.research(
                seam, deck.brief, model=writing, year=datetime.now(UTC).year
            )
            if isinstance(facts, Err):
                _fail(store, deck, human(facts.error), facts.error.kind)
                return
            # What research found, shown while the storyline is written: a count
            # and the publishers, never the facts themselves.
            cited = [f for f in facts.value if f.citation is not None]
            publishers = list(
                dict.fromkeys(
                    f.citation.publisher for f in cited if f.citation and f.citation.publisher
                )
            )
            store.append_event(
                deck.id,
                {"type": "research_done", "sources": len(cited), "publishers": publishers[:6]},
            )
            shots = {n: caption for n, (_, _, caption) in ready_screens(store, deck).items()}
            written = await storyline.write(
                seam,
                deck.brief,
                facts.value,
                model=writing,
                screens=shots,
                change=change,
                current=current,
            )
            if isinstance(written, Err):
                if current is not None:  # the old outline is still good: kept, not lost
                    store.update(deck.id, status="approve", error="")
                    store.append_event(
                        deck.id, {"type": "outline_refused", "message": human(written.error)}
                    )
                    return
                _fail(store, deck, human(written.error), written.error.kind)
                return
            story = written.value.story
            if current is not None and deck.title:  # the name the person has, kept
                story = story.model_copy(update={"title": deck.title})
            deck = store.update(
                deck.id,
                status="approve",
                storyline=story,
                facts=written.value.facts,
                title=story.title or deck.title,
                brief=deck.brief.model_copy(update={"slide_count": len(story.slides)}),
            )
            with_language(store, deck)  # the deck's look, drawn once and kept
            store.append_event(deck.id, {"type": "outline_ready"})
        elif job.kind == "logo":
            await _logo(store, deck)
        elif job.kind == "screens":
            _screens(store, deck)
        elif job.kind == "style":  # Another style or new colours: the card reads it again
            store.append_event(deck.id, {"type": "style_ready"})
        elif job.kind == "edit":
            op = ops.OP.validate_json(job.payload)
            if isinstance(op, ops.Ask):
                await _ask(store, deck, op, seam, model=design)
            elif isinstance(op, ops.AskDeck):
                await _ask_deck(store, deck, op, seam, model=design)
            else:
                await _edit(store, deck, op)
        else:
            await _build(
                store,
                deck,
                seam,
                design=design,
                notes_model=cheap or writing,
                budget_usd=budget_usd,
                image_model=image,
            )
    finally:
        store.append_ledger(deck.id, seam.ledger)


async def _build(
    store: AnyStore,
    deck: Deck,
    seam: Seam,
    *,
    design: str,
    notes_model: str,
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
        with_notes = await notes.write(seam, story, model=notes_model)
        if not isinstance(with_notes, Err):
            story = with_notes.value
            store.update(deck.id, storyline=story)
    # Where the person's screenshots go, saved in the outline, so an edit
    # later knows the slide shows one (an edit dropped one, 2026-10-10).
    shots = ready_screens(store, deck)
    placed = pipeline.place_screens(list(story.slides), shots)
    if placed != story.slides:
        story = story.model_copy(update={"slides": placed})
        store.update(deck.id, storyline=story)
    slides_dir = store.slides_dir(deck.id)
    deck = with_language(store, deck)
    theme = theme_of(deck)

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
        image_model=image_model,
        logo=await _clean_logo(store, deck),
        logo_on=deck.logo if deck.logo != "none" else "ends",
        screens=shots,
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


LOGO_UPLOAD = "logo-upload.bin"  # as received: never decoded by the API
LOGO_CLEAN = "logo.png"  # re-encoded here, the only form a slide ever sees


async def _logo(store: AnyStore, deck: Deck) -> None:
    """Hostile bytes in, a clean PNG out, or the refusal in words (phase 38)."""
    raw = store.export(deck.id, LOGO_UPLOAD)
    if raw is None:
        return
    made = await logos.ingest(raw)
    if isinstance(made, Err):
        store.update(
            deck.id, logo="none", logo_note=f"That file can't be used as a logo: {made.error}."
        )
        store.append_event(deck.id, {"type": "logo_refused", "message": made.error})
        return
    store.save_export(deck.id, LOGO_CLEAN, made.value.png)
    store.update(deck.id, logo_note="", logo_colour=made.value.colour or "")
    store.append_event(deck.id, {"type": "logo_ready", "colour": made.value.colour or ""})


def _screens(store: AnyStore, deck: Deck) -> None:
    """The person's screenshots: each re-encoded here, never trusted as
    uploaded, or refused in words."""
    screens = list(deck.screens)
    for n, screen in enumerate(screens, start=1):
        if screen.ready or screen.note:
            continue
        raw = store.export(deck.id, f"screen-{n}.bin")
        made = pictures.clean(raw) if raw is not None else None
        if made is None or isinstance(made, Err):
            why = made.error if made is not None else "the file is missing"
            screens[n - 1] = screen.model_copy(update={"note": f"That file can't be used: {why}."})
            continue
        webp, aspect = made.value
        store.save_export(deck.id, f"screen-{n}.webp", webp)
        screens[n - 1] = screen.model_copy(update={"ready": True, "aspect": aspect})
    store.update(deck.id, screens=screens)
    store.append_event(deck.id, {"type": "screens_ready"})


def ready_screens(store: AnyStore, deck: Deck) -> dict[int, tuple[str, str, str]]:
    """n -> (data URL, aspect, caption) for the screenshots ready to show."""
    out: dict[int, tuple[str, str, str]] = {}
    for n, screen in enumerate(deck.screens, start=1):
        data = store.export(deck.id, f"screen-{n}.webp") if screen.ready else None
        if data is not None:
            out[n] = (pictures.data_url(data), screen.aspect, screen.caption)
    return out


async def _clean_logo(store: AnyStore, deck: Deck) -> logos.Logo | None:
    """The deck's logo for the build: ingested again from our own clean PNG,
    so the build gets its measured size and luminance."""
    clean = store.export(deck.id, LOGO_CLEAN) if deck.logo != "none" else None
    if clean is None:
        return None
    made = await logos.ingest(clean)
    return None if isinstance(made, Err) else made.value


# Colour and type are the deck's look, not a slide's: asked of one slide they
# would break the deck, so they are refused in words, without a model call.
STYLE_ASK = re.compile(
    r"\b(colou?rs?|red|blue|green|yellow|purple|pink|orange|black|white|grey|gray|"
    r"fonts?|typefaces?|serif|italic|gradient|shadow|glow)\b",
    re.IGNORECASE,
)
STYLE_REFUSAL = (
    "Colour and type come from the look, so every slide stays one deck. Use New colours "
    "for the palette, or ask this slide for layout or emphasis instead."
)


def _proposal_name(slide_id: str, ext: str) -> str:
    return f"proposal-{slide_id}.{ext}"


async def _ask(store: AnyStore, deck: Deck, op: ops.Ask, seam: Seam, *, model: str) -> None:
    """A change in words: a proposal composed, measured and kept aside with
    its thumbnail. The deck itself does not change until it is accepted."""
    story = deck.storyline
    slide = store.kept(deck.id).get(op.slide)
    plan = next((p for p in story.slides if p.id == op.slide), None) if story else None
    if deck.status != "ready" or plan is None or slide is None:
        store.append_event(deck.id, {"type": "edit_refused", "message": "That slide isn't ready."})
        return
    if STYLE_ASK.search(op.instruction):
        store.append_event(deck.id, {"type": "edit_refused", "message": STYLE_REFUSAL})
        return
    theme = theme_of(deck)
    picture = _picture_for(plan, slide.composed.html, ready_screens(store, deck))
    current = Composed(pictures.strip(slide.composed.html), slide.composed.css)
    made = await designer.revise(
        seam, plan, current, op.instruction, prefix=prefix(theme), model=model
    )
    if isinstance(made, Err):
        store.append_event(deck.id, {"type": "edit_refused", "message": human(made.error)})
        return
    html = pictures.fill(made.value.html, picture) if picture else made.value.html
    proposal = Kept(Composed(html, made.value.css), "edited")
    shots = store.slides_dir(deck.id) / "proposal"
    shots.mkdir(parents=True, exist_ok=True)
    checked = await pipeline.remeasure(
        theme,
        [plan],
        {plan.id: proposal},
        work_file=str(shots / "qa.html"),
        shots_dir=str(shots),
    )
    (shots / "qa.html").unlink(missing_ok=True)
    if checked[plan.id].qa.status != "passed":
        store.append_event(
            deck.id,
            {
                "type": "edit_refused",
                "message": "That change didn't fit the slide. Try a smaller one.",
            },
        )
        return
    body = json.dumps({"html": proposal.composed.html, "css": proposal.composed.css})
    store.save_export(deck.id, _proposal_name(plan.id, "json"), body)
    store.save_export(
        deck.id, _proposal_name(plan.id, "png"), (shots / f"{plan.id}.png").read_bytes()
    )
    store.append_event(deck.id, {"type": "proposal_ready", "slide_id": plan.id})


def _picture_for(plan: SlidePlan, html: str, own: dict[int, tuple[str, str, str]]) -> str:
    """The picture an edit puts back: the slide's own, else the person's
    screenshot the slide was planned to show (its image box is required)."""
    shot = own.get(plan.screenshot) if plan.screenshot else None
    return pictures.picture_of(html) or (shot[0] if shot else "")


async def _ask_deck(
    store: AnyStore, deck: Deck, op: ops.AskDeck, seam: Seam, *, model: str
) -> None:
    """Every slide redesigned with one instruction, four at a time; a slide
    whose redesign fails QA keeps its old design. One version, so one undo
    returns the whole deck."""
    story = deck.storyline
    if story is None or deck.status != "ready":
        store.append_event(deck.id, {"type": "edit_refused", "message": "The deck isn't ready."})
        return
    if STYLE_ASK.search(op.instruction):
        store.append_event(deck.id, {"type": "edit_refused", "message": STYLE_REFUSAL})
        return
    theme = theme_of(deck)
    head = prefix(theme)
    kept = store.kept(deck.id)
    plans = [p for p in story.slides if p.id in kept]
    gate = asyncio.Semaphore(4)
    own = ready_screens(store, deck)

    async def one(plan: SlidePlan) -> tuple[str, Kept] | None:
        slide = kept[plan.id]
        picture = _picture_for(plan, slide.composed.html, own)
        current = Composed(pictures.strip(slide.composed.html), slide.composed.css)
        async with gate:
            made = await designer.revise(
                seam, plan, current, op.instruction, prefix=head, model=model
            )
        if isinstance(made, Err):
            return None
        html = pictures.fill(made.value.html, picture) if picture else made.value.html
        return plan.id, Kept(Composed(html, made.value.css), "edited")

    proposals = {
        sid: k for got in await asyncio.gather(*(one(p) for p in plans)) if got for sid, k in [got]
    }
    slides_dir = store.slides_dir(deck.id)
    checked = await pipeline.remeasure(
        theme,
        [p for p in plans if p.id in proposals],
        proposals,
        work_file=str(slides_dir / "qa-askdeck.html"),
        shots_dir=str(slides_dir / "askdeck"),
    )
    (slides_dir / "qa-askdeck.html").unlink(missing_ok=True)
    taken = [sid for sid, s in checked.items() if s.qa.status == "passed"]
    if not taken:
        store.append_event(
            deck.id,
            {
                "type": "edit_refused",
                "message": "No slide could take that change. Try a smaller one.",
            },
        )
        return
    for sid in taken:
        kept[sid] = proposals[sid]
        store.save_kept(deck.id, sid, kept[sid])
    fresh = await pipeline.remeasure(
        theme,
        [p for p in plans if p.id in taken],
        kept,
        work_file=str(slides_dir / "qa-edit.html"),
        shots_dir=str(slides_dir),
    )
    (slides_dir / "qa-edit.html").unlink(missing_ok=True)
    old = {s.id: s for s in deck.slides}
    slides = [fresh.get(p.id) or old[p.id] for p in story.slides if p.id in old or p.id in fresh]
    present, send = pipeline.export(theme, list(story.slides), kept, deck.title)
    store.save_export(deck.id, "export-present.html", present)
    store.save_export(deck.id, "export-send.html", send)
    store.save_export(deck.id, "export.pdf", await pdf.render(send))
    store.update(deck.id, slides=slides)
    store.snapshot(deck.id, ops.LABEL[op.kind])
    store.append_event(
        deck.id,
        {
            "type": "edit_done",
            "label": f"{ops.LABEL[op.kind]}: {len(taken)} of {len(plans)} slides",
            "flagged": [],
        },
    )


async def _edit(store: AnyStore, deck: Deck, op: ops.Op) -> None:
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
        store.drop_kept(deck.id, op.slide)
    elif isinstance(op, ops.Recolour):
        deck = deck.model_copy(update={"palette_nonce": deck.palette_nonce + 1})
        touched = [p.id for p in plans]
    elif isinstance(op, ops.Accept):
        raw = store.export(deck.id, _proposal_name(op.slide, "json"))
        if raw is None or op.slide not in by:
            store.append_event(
                deck.id, {"type": "edit_refused", "message": "There's no change waiting there."}
            )
            return
        parsed = json.loads(raw)
        # Checked again without the picture's bytes (a picture alone is over the
        # sanitizer's size cap); our own picture goes back in after it.
        picture = pictures.picture_of(str(parsed["html"]))
        names = frozenset(f.name for f in by[op.slide].fields)
        clean = sanitize(pictures.strip(str(parsed["html"])), names)
        if isinstance(clean, Err):  # it was ours, but it is read back from storage: checked again
            store.append_event(
                deck.id, {"type": "edit_refused", "message": "That change can't be applied."}
            )
            return
        html = pictures.fill(clean.value, picture) if picture else clean.value
        kept[op.slide] = Kept(Composed(html, str(parsed["css"])), "edited")
        touched = [op.slide]
    elif isinstance(op, (ops.Ask, ops.AskDeck)):  # handled by _ask / _ask_deck
        return
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


async def _beating(store: AnyStore, job: Job, work: asyncio.Task[None]) -> None:
    """Beat every BEAT_S until the work ends, and not a moment longer."""
    while not work.done():
        store.beat(job)
        await asyncio.wait({work}, timeout=BEAT_S)


async def once(
    store: AnyStore,
    *,
    make_seam: Callable[[str], Seam],
    writing: str,
    design: str,
    budget_usd: float,
    image: str = "",
    cheap: str = "",
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
            cheap=cheap,
        )
    )
    await asyncio.gather(work, _beating(store, job, work))
    store.finish(job)
    return True


def main() -> int:
    cfg = settings.load()
    store = open_store(cfg)
    print(f"worker: {cfg.data_dir}", flush=True)
    while True:
        try:
            did = asyncio.run(
                once(
                    store,
                    make_seam=lambda deck_id: Seam(
                        api_key=cfg.openrouter_api_key, providers=cfg.providers, deck_id=deck_id
                    ),
                    writing=cfg.model_writing,
                    design=cfg.model_design,
                    budget_usd=cfg.deck_budget_usd,
                    image=cfg.model_image,
                    cheap=cfg.model_cheap,
                )
            )
        except Exception as e:
            print(f"worker: job failed with {type(e).__name__}", flush=True)  # never content
            did = True
        if not did:
            time.sleep(1.0)


if __name__ == "__main__":
    sys.exit(main())
