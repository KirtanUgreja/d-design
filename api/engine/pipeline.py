"""The orchestrator: plain functions, in order, with every next step decided
here. No framework, and the model decides nothing about control flow.

Phase 22 scope: a frozen storyline in, a measured deck out.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
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
from engine.qa import browser
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
) -> Built:
    started = time.monotonic()
    plans = planner.assign(storyline.slides)
    fields = {p.id: {f.name: f.text for f in p.fields} for p in plans}
    gate = asyncio.Semaphore(PARALLEL)
    origin: dict[str, str] = {}
    attempts: dict[str, int] = {}
    refusals: dict[str, str] = {}

    def affordable() -> bool:
        # Fails closed: once the cap is reached no further call is made.
        return seam.spent_usd < budget_usd

    # The seam asks too, before every call it makes, so no path skips the cap.
    seam.allow = affordable

    async def first(index: int, plan: SlidePlan) -> Composed:
        attempts[plan.id] = 1
        if not affordable():
            origin[plan.id] = "fallback"
            return author.fallback(plan)
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
        if isinstance(result, Err):
            origin[plan.id] = "fallback"
            refusals[plan.id] = f"{result.error.kind}: {result.error.detail[:300]}"
            return author.fallback(plan)
        origin[plan.id] = "authored"
        return result.value

    composed = dict(
        zip(
            (p.id for p in plans),
            await asyncio.gather(*(first(i, p) for i, p in enumerate(plans))),
            strict=True,
        )
    )

    async def measure() -> dict[str, browser.Measured]:
        frames = [_frame(p, composed[p.id]) for p in plans]
        return await browser.measure(theme, frames, fields, work_file, shots_dir)

    measured = await measure()
    bad = [p for p in plans if measured[p.id].errors or not measured[p.id].measured]
    clean_first = len(plans) - len(bad)

    async def fix(plan: SlidePlan) -> None:
        if origin[plan.id] == "fallback" or not affordable():
            return
        async with gate:
            result = await author.repair(
                seam,
                theme,
                plan,
                composed[plan.id],
                measured[plan.id].defects(),
                model=model,
                exemplars=exemplars,
            )
        attempts[plan.id] += 1
        if not isinstance(result, Err):
            composed[plan.id] = result.value
            origin[plan.id] = "repaired"

    def broken(plan: SlidePlan) -> bool:
        return bool(measured[plan.id].errors) or not measured[plan.id].measured

    # Rung 1: targeted repair from the measured defects, at most REPAIR_ROUNDS.
    for _ in range(REPAIR_ROUNDS):
        bad = [p for p in plans if broken(p)]
        if not bad:
            break
        await asyncio.gather(*(fix(p) for p in bad))
        measured = await measure()

    # Rung 2: exemplar-fill, no model call; then the code-built layout.
    still = [p for p in plans if broken(p)]
    for plan in still:
        codes = sorted({d.code for d in measured[plan.id].defects()})
        refusals[plan.id] = f"still defective after repair: {codes}"
        filled = None if plan.chart else _exemplar_fill(plan, fields[plan.id])
        composed[plan.id] = filled or author.fallback(plan)
        origin[plan.id] = "exemplar" if filled else "fallback"
    if still:
        measured = await measure()
        failed_fill = [p for p in still if origin[p.id] == "exemplar" and broken(p)]
        for plan in failed_fill:
            composed[plan.id] = author.fallback(plan)
            origin[plan.id] = "fallback"
        if failed_fill:
            measured = await measure()
    # Rung 3 is the flag, set below from what is still measured as broken.

    slides: list[Slide] = []
    for plan in plans:
        m = measured[plan.id]
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
    return Built(slides, html, send, time.monotonic() - started, clean_first, refusals)
