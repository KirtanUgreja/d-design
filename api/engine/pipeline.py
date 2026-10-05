"""The orchestrator: plain functions, in order, with every next step decided
here. No framework, and the model decides nothing about control flow.

Phase 22 scope: a frozen storyline in, a measured deck out.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from engine.components import charts
from engine.compose import author, planner
from engine.compose import exemplars as library
from engine.compose.author import Composed
from engine.compose.document import Frame
from engine.design.theme import Theme
from engine.export.assemble import assemble
from engine.llm.openrouter import Seam
from engine.models import Slide, SlidePlan, SlideQA, Storyline
from engine.qa import browser, metrics
from lib.result import Err

PARALLEL = 5
REPAIR_ROUNDS = 2


def _exemplar_fill(plan: SlidePlan, words: dict[str, str]) -> Composed | None:
    """The best exemplar that can hold every field, filled with them."""
    for ex in library.best_for(set(words), plan.intent, plan.archetype)[:1]:
        return Composed(library.fill(ex, words), ex.css)
    return None


@dataclass(frozen=True)
class Built:
    slides: list[Slide]
    html: str  # the "present" flavour, with speaker notes
    send: str  # the "send" flavour: no notes; the PDF is printed from it
    seconds: float
    first_pass_clean: int  # slides with no defect before any repair
    refusals: dict[str, str]  # slide id -> why its composition was refused (lint text only)


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
    exemplars: bool = True,
    on_event: OnEvent | None = None,
) -> Built:
    """Every slide climbs its own ladder, concurrently: compose, measure, up to
    REPAIR_ROUNDS repairs, exemplar-fill, the code layout, then the flag. A
    slide is announced the moment it is final, so a watch fills slot by slot
    with what really happened (docs/v4/engine.md -> "Generation jobs and events")."""
    started = time.monotonic()
    plans = planner.assign(storyline.slides)
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

    def affordable() -> bool:
        # Fails closed: once the cap is reached no further call is made.
        return seam.spent_usd < budget_usd

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

    async def ladder(index: int, plan: SlidePlan) -> None:
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
                    previous=plans[index - 1].archetype if index else "",
                    exemplars=exemplars,
                )
        if result is None or isinstance(result, Err):
            if result is not None:
                refusals[plan.id] = f"{result.error.kind}: {result.error.detail[:300]}"
            composed[plan.id], origin[plan.id] = author.fallback(plan), "fallback"
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
                    exemplars=exemplars,
                )
            attempts[plan.id] += 1
            if isinstance(fixed, Err):
                break
            composed[plan.id], origin[plan.id] = fixed.value, "repaired"
            m = await measure(plan)

        # Rung 2: exemplar-fill, no model call; then the code-built layout.
        if broken(m):
            refusals[plan.id] = (
                f"still defective after repair: {sorted({d.code for d in m.defects()})}"
            )
            filled = None if plan.chart else _exemplar_fill(plan, fields[plan.id])
            if filled is not None:
                composed[plan.id], origin[plan.id] = filled, "exemplar"
                m = await measure(plan)
            if broken(m) and origin[plan.id] != "fallback":
                composed[plan.id], origin[plan.id] = author.fallback(plan), "fallback"
                m = await measure(plan)

        # Rung 3, the flag: whatever is still broken is shown, never hidden.
        measured[plan.id] = m
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
    await asyncio.gather(*(ladder(i, p) for i, p in enumerate(plans)))
    emit("stage", name="compose", state="done")

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
    frames = [_frame(p, composed[p.id]) for p in plans]
    notes = {p.id: p.notes for p in plans if p.notes}
    html = assemble(theme, frames, title, flavour="present", notes=notes)
    send = assemble(theme, frames, title, flavour="send")
    emit("done", seconds=round(time.monotonic() - started, 1))
    return Built(slides, html, send, time.monotonic() - started, len(first_clean), refusals)
