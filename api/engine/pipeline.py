"""The orchestrator: plain functions, in order, with every next step decided
here. No framework, and the model decides nothing about control flow.

Phase 22 scope: a frozen storyline in, a measured deck out.
"""

from __future__ import annotations

import asyncio
import dataclasses
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from engine.components import charts
from engine.components import logo as logos
from engine.compose import author, planner, procedural, targets
from engine.compose.archive import Archive
from engine.compose.author import Composed
from engine.compose.document import Frame
from engine.design.theme import Theme
from engine.export.assemble import assemble
from engine.llm.openrouter import Seam
from engine.models import Slide, SlidePlan, SlideQA, Storyline
from engine.qa import browser, metrics
from engine.qa.descriptors import Descriptors, describe, distance
from lib.result import Err

PARALLEL = 5
REPAIR_ROUNDS = 2
# Closer than this to any archived slide, or any slide in the deck, is a
# near-repeat. ponytail: provisional; tuned on the sameness bench (phase 36).
NOVELTY_EPSILON = 0.08
STEER = (
    "This composition came out too close to one already made (distance {d:.2f} of 1). Keep "
    "the content and the target; move the visual mass and the open field somewhere else, "
    "change the split, and change the scale relation."
)


@dataclass(frozen=True)
class Kept:
    """A finished slide as the worker persists it: enough to resume for free."""

    composed: Composed
    origin: str


@dataclass(frozen=True)
class Built:
    slides: list[Slide]
    html: str  # the "present" flavour, with speaker notes
    send: str  # the "send" flavour: no notes; the PDF is printed from it
    seconds: float
    first_pass_clean: int  # slides with no defect before any repair
    refusals: dict[str, str]  # slide id -> why its composition was refused (lint text only)
    descriptors: dict[str, Descriptors]  # slide id -> its composition, for the archive
    novelty_retries: int
    near_repeats: int


def _frame(plan: SlidePlan, c: Composed) -> Frame:
    # Charts are drawn by our code after sanitizing, so QA measures them too.
    return Frame(plan.id, charts.fill(c.html, plan.chart), c.css)


Event = dict[str, object]
OnEvent = Callable[[Event], None]
MEASURE_PARALLEL = 3  # Chromium processes at once


async def build(
    seam: Seam,
    storyline: Storyline,
    theme: Theme,
    *,
    model: str,
    title: str,
    work_file: str,
    shots_dir: str,
    budget_usd: float,
    archive: Archive | None = None,
    logo: logos.Logo | None = None,
    logo_on: Literal["cover", "ends", "all"] = "ends",
    on_event: OnEvent | None = None,
    prebuilt: dict[str, Kept] | None = None,
    on_final: Callable[[str, Kept], None] | None = None,
    stop: Callable[[], bool] | None = None,
) -> Built:
    """Every slide climbs its own ladder, concurrently: compose, measure, up to
    REPAIR_ROUNDS repairs, one fresh composition toward another target (with
    one repair), the code-built layout, then the flag. A
    slide is announced the moment it is final, so a watch fills slot by slot
    with what really happened (docs/v4/engine.md -> "Generation jobs and events").

    For the worker: ``prebuilt`` slides (finished before a crash) are only
    measured again, never paid for twice; ``on_final`` hears each slide the
    moment it is final, so it can be persisted; ``stop`` (an abort) starts no
    new slide and no new model call, and the deck keeps what is done."""
    started = time.monotonic()
    plans = planner.assign(storyline.slides)
    if logo is not None:
        # The user's logo is the deck's signature now: the generated mark steps back.
        plans = [
            p.model_copy(update={"ornament": "none"}) if p.ornament == "mark" else p for p in plans
        ]
        theme = dataclasses.replace(theme, logo=logo.data_url())
    archive = archive if archive is not None else Archive()
    # Every slide's target, drawn in order so each moves away from the last.
    rng = random.Random(f"{title}/{storyline.governing_thought}")  # noqa: S311 - layout, not security
    aims: dict[str, targets.Target] = {}
    previous: targets.Target | None = None
    for plan in plans:
        previous = aims[plan.id] = targets.draw(
            rng, archive, plan.intent, len(plan.fields), previous
        )
    accepted: dict[str, Descriptors] = {}
    steered: set[str] = set()
    fields = {p.id: {f.name: f.text for f in p.fields} for p in plans}
    gate = asyncio.Semaphore(PARALLEL)
    browsers = asyncio.Semaphore(MEASURE_PARALLEL)
    origin: dict[str, str] = {}
    attempts: dict[str, int] = {p.id: 0 for p in plans}
    refusals: dict[str, str] = {}
    composed: dict[str, Composed] = {}
    measured: dict[str, browser.Measured] = {}
    first_clean: set[str] = set()
    work = Path(work_file)

    def emit(kind: str, **data: object) -> None:
        if on_event is not None:
            on_event({"type": kind, "t": round(time.monotonic() - started, 2), **data})

    resumed = prebuilt or {}

    def stopped() -> bool:
        return stop is not None and stop()

    def affordable() -> bool:
        # Fails closed: once the cap is reached, or the user aborts, no further call is made.
        return seam.spent_usd < budget_usd and not stopped()

    # The seam asks too, before every call it makes, so no path skips the cap.
    seam.allow = affordable

    async def measure(plan: SlidePlan) -> browser.Measured:
        async with browsers:
            result = await browser.measure(
                theme,
                [_frame(plan, composed[plan.id])],
                {plan.id: fields[plan.id]},
                str(work.with_name(f"{work.stem}-{plan.id}.html")),
                shots_dir,
            )
        return result[plan.id]

    def broken(m: browser.Measured) -> bool:
        return bool(m.errors) or not m.measured

    def wants_logo(index: int) -> bool:
        ends = index in (0, len(plans) - 1)
        return logo_on == "all" or (index == 0 if logo_on == "cover" else ends)

    async def with_logo(
        index: int, plan: SlidePlan, m: browser.Measured, mark: logos.Logo
    ) -> browser.Measured:
        """Placed by code in the emptiest safe corner, in the variant that
        reads on the ground; measured again, and taken off if anything broke."""
        occupied = [(b.l, b.t, b.r, b.b) for b in m.boxes]
        occupied += [(s.l, s.t, s.r, s.b) for s in m.shapes]
        ends = index in (0, len(plans) - 1)
        at = logos.place(occupied, mark, height=96 if ends else 56, prefer_top=index == 0)
        warn = "no empty safe-area corner for the logo"
        if at is not None:
            kept = composed[plan.id]
            tone = logos.variant(mark, theme.colors["ground"])
            composed[plan.id] = Composed(logos.insert(kept.html, at, tone), kept.css)
            placed = await measure(plan)
            if not broken(placed):
                return placed
            composed[plan.id] = kept
            m = await measure(plan)  # the slide without it, screenshot included
            warn = "the logo broke the slide, so it was left off"
        m.warnings.append(browser._Found(code="W9", measured=warn, threshold="logo placed"))
        return m

    methods: dict[int, str] = {}  # deck position -> the code-built method used there

    def code_built(plan: SlidePlan) -> Composed:
        index = next(i for i, p in enumerate(plans) if p.id == plan.id)
        avoid = {m for i, m in methods.items() if abs(i - index) == 1}
        aim = procedural.vary(aims[plan.id], avoid)
        methods[index] = procedural.method(aim)
        return procedural.build(plan, aim, theme)

    def nearest(d: Descriptors, slide_id: str) -> float:
        deck = [distance(d, e) for k, e in accepted.items() if k != slide_id]
        return min([archive.nearest(d), *deck])

    async def novelty(index: int, plan: SlidePlan, m: browser.Measured) -> browser.Measured:
        """One steered retry for a near-repeat; then accept it, warned and
        counted. Cost stays bounded: never a loop."""
        d = describe(m.boxes, m.shapes)
        near = nearest(d, plan.id)
        if near < NOVELTY_EPSILON and origin[plan.id] != "fallback" and affordable():
            steered.add(plan.id)
            async with gate:
                retry = await author.compose(
                    seam,
                    theme,
                    plan,
                    model=model,
                    position=index + 1,
                    total=len(plans),
                    thought=storyline.governing_thought,
                    target=aims[plan.id],
                    steer=STEER.format(d=near),
                )
            attempts[plan.id] += 1
            if not isinstance(retry, Err):
                kept, composed[plan.id] = composed[plan.id], retry.value
                again = await measure(plan)
                d2 = describe(again.boxes, again.shapes)
                if not broken(again) and nearest(d2, plan.id) > near:
                    m, d, near = again, d2, nearest(d2, plan.id)
                    origin[plan.id] = "authored"
                else:
                    composed[plan.id] = kept
                    m = await measure(plan)  # the kept slide's screenshot back on disk
        if near < NOVELTY_EPSILON:
            m.warnings.append(
                browser._Found(
                    code="W8",
                    measured=f"distance {near:.2f} to an earlier composition",
                    threshold=f"{NOVELTY_EPSILON}",
                )
            )
        accepted[plan.id] = d
        return m

    async def ladder(index: int, plan: SlidePlan) -> None:
        if plan.id in resumed:  # finished before a restart: measured again, never paid twice
            composed[plan.id], origin[plan.id] = resumed[plan.id].composed, resumed[plan.id].origin
            attempts[plan.id] = 0
            finish(index, plan, await measure(plan), persist=False)
            return
        if stopped():  # aborted before this slide began: nothing made, nothing kept
            return
        # The first rung: compose (or the code layout if the budget is spent).
        attempts[plan.id] = 1
        result = None
        if affordable():
            async with gate:
                result = await author.compose(
                    seam,
                    theme,
                    plan,
                    model=model,
                    position=index + 1,
                    total=len(plans),
                    thought=storyline.governing_thought,
                    target=aims[plan.id],
                )
        if result is None or isinstance(result, Err):
            if result is not None:
                refusals[plan.id] = f"{result.error.kind}: {result.error.detail[:300]}"
            composed[plan.id], origin[plan.id] = code_built(plan), "fallback"
        else:
            composed[plan.id], origin[plan.id] = result.value, "authored"
        m = await measure(plan)
        if not broken(m):
            first_clean.add(plan.id)

        # Rung 1: targeted repair from the measured defects.
        for _ in range(REPAIR_ROUNDS):
            if not broken(m) or origin[plan.id] == "fallback" or not affordable():
                break
            async with gate:
                fixed = await author.repair(
                    seam,
                    theme,
                    plan,
                    composed[plan.id],
                    m.defects(),
                    model=model,
                )
            attempts[plan.id] += 1
            if isinstance(fixed, Err):
                break
            composed[plan.id], origin[plan.id] = fixed.value, "repaired"
            m = await measure(plan)

        # Rung 2: one fresh composition toward a different target, and one repair.
        # A code-built slide is the last resort, so a failed first answer gets this too.
        if (broken(m) or origin[plan.id] == "fallback") and result is not None and affordable():
            aims[plan.id] = targets.draw(rng, archive, plan.intent, len(plan.fields), aims[plan.id])
            async with gate:
                fresh = await author.compose(
                    seam,
                    theme,
                    plan,
                    model=model,
                    position=index + 1,
                    total=len(plans),
                    thought=storyline.governing_thought,
                    target=aims[plan.id],
                )
            attempts[plan.id] += 1
            if not isinstance(fresh, Err):
                kept, composed[plan.id] = composed[plan.id], fresh.value
                again = await measure(plan)
                if broken(again) and affordable():
                    async with gate:
                        fixed = await author.repair(
                            seam, theme, plan, composed[plan.id], again.defects(), model=model
                        )
                    attempts[plan.id] += 1
                    if not isinstance(fixed, Err):
                        composed[plan.id] = fixed.value
                        again = await measure(plan)
                if broken(again):
                    composed[plan.id] = kept
                    m = await measure(plan)  # the kept slide's screenshot back on disk
                else:
                    m, origin[plan.id] = again, "authored"

        # Rung 3: the code-built layout, from the slide's target. No stored layout.
        if broken(m):
            refusals[plan.id] = (
                f"still defective after repair: {sorted({d.code for d in m.defects()})}"
            )
            if origin[plan.id] != "fallback":
                composed[plan.id], origin[plan.id] = code_built(plan), "fallback"
                m = await measure(plan)

        # The novelty gate: quality first, then distance from everything made.
        if not broken(m):
            m = await novelty(index, plan, m)
        if logo is not None and not broken(m) and wants_logo(index):
            m = await with_logo(index, plan, m, logo)

        # Rung 4, the flag: whatever is still broken is shown, never hidden.
        finish(index, plan, m)

    def finish(index: int, plan: SlidePlan, m: browser.Measured, *, persist: bool = True) -> None:
        measured[plan.id] = m
        if persist and on_final is not None:
            on_final(plan.id, Kept(composed[plan.id], origin[plan.id]))
        status = "unmeasured" if not m.measured else "flagged" if m.errors else "passed"
        emit(
            "slide_ready",
            slide_id=plan.id,
            position=index + 1,
            status=status,
            origin=origin[plan.id],
            thumb=f"{plan.id}.png",
        )
        if status != "passed":
            emit("slide_flagged", slide_id=plan.id, defects=sorted({d.code for d in m.defects()}))
        emit("cost", total_usd=round(seam.spent_usd, 4))

    emit("stage", name="compose", state="started", slides=[p.id for p in plans])
    # The cover first, alone: it is the first thing a watching user sees, and
    # its call warms the prompt cache every other slide then reads (phase 32).
    if plans:
        await ladder(0, plans[0])
    await asyncio.gather(*(ladder(i, p) for i, p in enumerate(plans) if i > 0))
    emit("stage", name="compose", state="done")
    for d in accepted.values():
        archive.add(d)

    plans = [p for p in plans if p.id in measured]  # an abort keeps only what is done
    rhythm = metrics.deck_warnings(
        [measured[p.id].fingerprint for p in plans], [measured[p.id].centred for p in plans]
    )
    slides: list[Slide] = []
    for index, plan in enumerate(plans):
        m = measured[plan.id]
        m.warnings += [browser._Found(**w.model_dump()) for w in rhythm.get(index, [])]
        status: Literal["passed", "flagged", "unmeasured"] = (
            "unmeasured" if not m.measured else "flagged" if m.errors else "passed"
        )
        slides.append(
            Slide(
                id=plan.id,
                plan_id=plan.id,
                html=_frame(plan, composed[plan.id]).html,  # with its chart drawn
                css=composed[plan.id].css,
                fields=fields[plan.id],
                origin=origin[plan.id],  # type: ignore[arg-type]  # set only to the literals
                attempts=attempts[plan.id],
                qa=SlideQA(
                    status=status,
                    errors=m.defects(),
                    warnings=m.warned(),
                    fingerprint=m.fingerprint,
                    screenshot=f"{plan.id}.png",
                ),
                cost_usd=sum(e.cost_usd for e in seam.ledger if e.slide_id == plan.id),
            )
        )
    html, send = export(
        theme, plans, {p.id: Kept(composed[p.id], origin[p.id]) for p in plans}, title
    )
    emit("done", seconds=round(time.monotonic() - started, 1))
    return Built(
        slides,
        html,
        send,
        time.monotonic() - started,
        len(first_clean),
        refusals,
        accepted,
        len(steered),
        sum(any(w.code == "W8" for w in s.qa.warnings) for s in slides),
    )


# --- edits without a model (phase 28): the worker's edit job uses these -------


def export(
    theme: Theme, plans: list[SlidePlan], kept: dict[str, Kept], title: str
) -> tuple[str, str]:
    """Both flavours from finished slides. A chart's values ride in the notes
    too: the presenter can read them out, and the send flavour's readers get
    them as text (phase 37)."""
    plans = [p for p in plans if p.id in kept]
    frames = [_frame(p, kept[p.id].composed) for p in plans]
    notes = {
        p.id: "\n\n".join(x for x in (p.notes, charts.describe(p.chart) if p.chart else "") if x)
        for p in plans
        if p.notes or p.chart
    }
    present = assemble(theme, frames, title, flavour="present", notes=notes)
    return present, assemble(theme, frames, title, flavour="send")


async def remeasure(
    theme: Theme,
    plans: list[SlidePlan],
    kept: dict[str, Kept],
    *,
    work_file: str,
    shots_dir: str,
) -> dict[str, Slide]:
    """QA again for the given slides, screenshots refreshed: after a text edit,
    a recolour or a fit. No model call. Every slide comes back measured."""
    frames = [_frame(p, kept[p.id].composed) for p in plans]
    fields = {p.id: {f.name: f.text for f in p.fields} for p in plans}
    result = await browser.measure(theme, frames, fields, work_file, shots_dir)
    out: dict[str, Slide] = {}
    for plan, frame in zip(plans, frames, strict=True):
        m = result[plan.id]
        status: Literal["passed", "flagged", "unmeasured"] = (
            "unmeasured" if not m.measured else "flagged" if m.errors else "passed"
        )
        out[plan.id] = Slide(
            id=plan.id,
            plan_id=plan.id,
            html=frame.html,
            css=frame.css,
            fields=fields[plan.id],
            origin=kept[plan.id].origin,  # type: ignore[arg-type]  # set only to the literals
            attempts=0,
            qa=SlideQA(
                status=status,
                errors=m.defects(),
                warnings=m.warned(),
                fingerprint=m.fingerprint,
                screenshot=f"{plan.id}.png",
            ),
        )
    return out


def code_built(plan: SlidePlan, theme: Theme) -> Kept:
    """ "Fit to slide": the slide rebuilt by code from a target of its own, so
    its words fit by construction (the same code the ladder falls back to)."""
    rng = random.Random(f"fit/{plan.id}")  # noqa: S311 - layout, not security
    aim = targets.draw(rng, Archive(), plan.intent, len(plan.fields))
    return Kept(procedural.build(plan, aim, theme), "fallback")
