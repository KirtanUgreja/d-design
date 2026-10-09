"""The build: an approved outline in, a designed and measured deck out. Plain
functions in order; the model decides nothing about control flow.

    direct (once) -> for each slide, concurrently:
      design -> measure -> improve (looks at the render) -> measure, keep the
      better -> repair what is still broken -> the code layout as the floor
      -> the logo and the picture placed by code -> flag what is left

Every slide is announced the moment it is final, so a watching user sees it
arrive, and persisted, so a restarted worker never pays for it twice.
"""

from __future__ import annotations

import asyncio
import dataclasses
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from engine.components import charts
from engine.components import images as pictures
from engine.components import logo as logos
from engine.design import languages
from engine.design.color import from_hex
from engine.design.theme import Theme
from engine.export.assemble import assemble
from engine.llm.openrouter import ModelError, Seam
from engine.models import Slide, SlidePlan, SlideQA, Storyline
from engine.qa import browser, metrics
from engine.studio import design, direct, improve, review
from engine.studio.direct import Direction, SlideDirection
from engine.studio.slide import Composed, Kept, frame, prefix
from lib.result import Err, Result

PARALLEL = 4  # slides designed at once
MEASURE_PARALLEL = 3  # Chromium processes at once
REPAIR_ROUNDS = 2
RETRY_AFTER_S = 3.0  # a design call the gateway refused is tried once more after this

Event = dict[str, object]
OnEvent = Callable[[Event], None]


@dataclass(frozen=True)
class Built:
    slides: list[Slide]
    html: str  # the "present" flavour, with speaker notes
    send: str  # the "send" flavour: no notes; the PDF is printed from it
    seconds: float
    first_pass_clean: int  # slides with no defect before any repair
    improved: int  # slides whose redesign the improver got kept
    refusals: dict[str, str]  # slide id -> why its design was refused (lint text only)


def _errors(m: browser.Measured) -> int:
    return len(m.errors) if m.measured else 10_000


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
    logo: logos.Logo | None = None,
    logo_on: Literal["cover", "ends", "all"] = "ends",
    on_event: OnEvent | None = None,
    prebuilt: dict[str, Kept] | None = None,
    on_final: Callable[[str, Kept], None] | None = None,
    stop: Callable[[], bool] | None = None,
    image_model: str = "",
    improving: bool = True,
    screens: Mapping[int, tuple[str, str, str]] | None = None,
) -> Built:
    started = time.monotonic()
    head = prefix(theme)
    if logo is not None:
        # The user's logo is the deck's signature: placed by code, so the
        # generated emblem steps back.
        theme = dataclasses.replace(theme, logo=logo.data_url())
        head += (
            "\nThe person's own logo is placed on the slides by our code: never use the "
            'dd-texture kind "mark".\n'
        )
    own = dict(screens or {})  # n -> (data URL, aspect, caption): the person's own images
    plans = _place_screens(list(storyline.slides), own)
    fields = {p.id: {f.name: f.text for f in p.fields} for p in plans}
    gate = asyncio.Semaphore(PARALLEL)
    browsers = asyncio.Semaphore(MEASURE_PARALLEL)
    composed: dict[str, Composed] = {}
    origin: dict[str, str] = {}
    attempts: dict[str, int] = {p.id: 0 for p in plans}
    measured: dict[str, browser.Measured] = {}
    refusals: dict[str, str] = {}
    first_clean: set[str] = set()
    improved: set[str] = set()
    resumed = prebuilt or {}
    work = Path(work_file)

    def emit(kind: str, **data: object) -> None:
        if on_event is not None:
            on_event({"type": kind, "t": round(time.monotonic() - started, 2), **data})

    def stopped() -> bool:
        return stop is not None and stop()

    def affordable() -> bool:
        # Fails closed: once the cap is reached, or the user aborts, no further call is made.
        return seam.spent_usd < budget_usd and not stopped()

    seam.allow = affordable  # the seam asks too, before every call, so no path skips the cap

    async def measure(plan: SlidePlan) -> browser.Measured:
        async with browsers:
            result = await browser.measure(
                theme,
                [frame(plan, composed[plan.id])],
                {plan.id: fields[plan.id]},
                str(work.with_name(f"{work.stem}-{plan.id}.html")),
                shots_dir,
            )
        return result[plan.id]

    def broken(m: browser.Measured) -> bool:
        return bool(m.errors) or not m.measured

    # Layer 3a: the art director plans every slide at once (skipped on a resume
    # that has nothing left to design).
    emit("stage", name="direction", state="started")
    direction: Direction = direct.plain(plans)
    if any(p.id not in resumed for p in plans) and affordable():
        lang = languages.get(theme.language) if theme.language else None
        appetite = lang.image.appetite if lang else 0.3
        wanted = max(1, round(appetite * len(plans))) if image_model else 0
        got = await direct.direct(seam, storyline, theme, model=model, prefix=head, pictures=wanted)
        if not isinstance(got, Err):
            direction = got.value
        else:
            refusals["direction"] = f"{got.error.kind}: {got.error.detail[:300]}"
    emit("stage", name="direction", state="done")

    # A motif on every slide reads as a template (the halftone on 6 of 10,
    # 2026-10-09): the pattern is kept for the cover, the ask and one slide
    # between them.
    patterned = {plans[0].id, plans[-1].id, plans[len(plans) // 2].id} if plans else set()

    def wants_picture(plan: SlidePlan) -> bool:
        d = direction.of(plan.id)
        return bool(image_model and d and d.image and plan.chart is None and plan.visual is None)

    def neighbours(index: int) -> str:
        around = plans[max(0, index - 1) : index + 2]
        near = [direction.of(p.id) for p in around if p.id != plans[index].id]
        return " | ".join(f"{d.hero} on {d.ground}" for d in near if d)

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
        if at is None:
            m.warnings.append(
                browser._Found(
                    code="W9",
                    measured="no empty safe-area corner for the logo",
                    threshold="a free corner",
                )
            )
            return m
        kept = composed[plan.id]
        tone = logos.variant(mark, theme.colors["ground"])
        composed[plan.id] = Composed(logos.insert(kept.html, at, tone), kept.css)
        placed = await measure(plan)
        if not broken(placed):
            return placed
        composed[plan.id] = kept
        m = await measure(plan)  # the slide without it, screenshot included
        m.warnings.append(
            browser._Found(
                code="W9",
                measured="the logo broke the slide, so it was left off",
                threshold="logo placed",
            )
        )
        return m

    async def picture(plan: SlidePlan, aspect: str) -> str:
        """The slide's picture as our own webp data URL, or "" (a quiet field)."""
        if not affordable():
            return ""
        style = theme.look.get("image", "editorial photography")
        made = await seam.complete_image(
            pictures.prompt(plan, style, theme.colors.get("accent", ""), deck=title),
            model=image_model,
            aspect=aspect,
            slide_id=plan.id,
        )
        if isinstance(made, Err):
            return ""
        tones = None
        if pictures.is_photo(style):
            c = theme.colors
            dark, light = sorted((c["ground"], c["ink"]), key=lambda h: from_hex(h).l)
            tones = (dark, c["accent"], light)
        treated = pictures.treat(made.value, aspect, tones)
        return "" if isinstance(treated, Err) else pictures.data_url(treated.value)

    async def with_picture(plan: SlidePlan, m: browser.Measured, own: str = "") -> browser.Measured:
        kept = composed[plan.id]
        if "<dd-image" not in kept.html:
            return m
        url = own or await picture(plan, pictures.aspect_of(kept.html))
        if not url:
            return m
        composed[plan.id] = Composed(pictures.fill(kept.html, url), kept.css)
        placed = await measure(plan)
        if not broken(placed):
            return placed
        composed[plan.id] = kept
        return await measure(plan)

    async def designed(
        index: int,
        plan: SlidePlan,
        d: SlideDirection | None,
        shot: tuple[str, str, str] | None,
        image: bool,
        note: str = "",
    ) -> Result[Composed, ModelError] | None:
        """One designer call; a gateway hiccup gets one more try, not the floor."""
        made: Result[Composed, ModelError] | None = None
        for tries in range(2):
            if not affordable():
                break
            async with gate:
                made = await design.compose(
                    seam,
                    plan,
                    d,
                    prefix=head,
                    model=model,
                    position=index + 1,
                    total=len(plans),
                    thought=storyline.governing_thought + note,
                    concept=direction.concept,
                    image=image,
                    pattern=plan.id in patterned,
                    screenshot=(shot[2], shot[1]) if shot else None,
                    title=storyline.title or title,
                    logo_room=logo is not None and wants_logo(index),
                )
            if not isinstance(made, Err) or made.error.kind != "transport" or tries:
                break
            await asyncio.sleep(RETRY_AFTER_S)
        return made

    async def make(index: int, plan: SlidePlan) -> None:
        if plan.id in resumed:  # finished before a restart: measured again, never paid twice
            composed[plan.id], origin[plan.id] = resumed[plan.id].composed, resumed[plan.id].origin
            finish(index, plan, await measure(plan), persist=False)
            return
        if stopped():  # aborted before this slide began: nothing made, nothing kept
            return
        d = direction.of(plan.id)
        shot = own.get(plan.screenshot) if plan.screenshot else None
        image = wants_picture(plan) or shot is not None

        # Layer 3b: the designer.
        emit("slide_step", slide_id=plan.id, step="design")  # the watch page's live feed
        attempts[plan.id] = 1
        made = await designed(index, plan, d, shot, image)
        if made is None or isinstance(made, Err):
            if made is not None:
                refusals[plan.id] = f"{made.error.kind}: {made.error.detail[:300]}"
            composed[plan.id], origin[plan.id] = design.fallback(plan, theme), "fallback"
        else:
            composed[plan.id], origin[plan.id] = made.value, "authored"
        m = await measure(plan)
        if not broken(m):
            first_clean.add(plan.id)

        # Layer 4: the improver looks at the render and redesigns it; kept only
        # if QA measures it no worse.
        if improving and origin[plan.id] == "authored" and affordable():
            emit("slide_step", slide_id=plan.id, step="improve")
            async with gate:
                better = await improve.improve(
                    seam,
                    plan,
                    composed[plan.id],
                    improve.shot(Path(shots_dir) / f"{plan.id}.png"),
                    m.defects(),
                    d,
                    prefix=head,
                    model=model,
                    neighbours=neighbours(index),
                )
            attempts[plan.id] += 1
            if not isinstance(better, Err):
                kept, composed[plan.id] = composed[plan.id], better.value[0]
                again = await measure(plan)
                if _errors(again) <= _errors(m):
                    m, origin[plan.id] = again, "improved"
                    improved.add(plan.id)
                else:
                    composed[plan.id] = kept
                    m = await measure(plan)  # the kept slide's screenshot back on disk

        # The safety net: targeted repairs, then the code layout.
        for _ in range(REPAIR_ROUNDS):
            if not broken(m) or origin[plan.id] == "fallback" or not affordable():
                break
            emit("slide_step", slide_id=plan.id, step="repair")
            async with gate:
                fixed = await design.repair(
                    seam, plan, composed[plan.id], m.defects(), prefix=head, model=model
                )
            attempts[plan.id] += 1
            if isinstance(fixed, Err):
                break
            composed[plan.id], origin[plan.id] = fixed.value, "repaired"
            m = await measure(plan)
        # The cover is the first thing anyone sees: before the code layout
        # stands in for it, one fresh design, told what failed (owner,
        # 2026-10-10: a code-built cover made a whole deck look old).
        if index == 0 and broken(m) and origin[plan.id] != "fallback" and affordable():
            failed = ", ".join(sorted({x.code for x in m.defects()}))
            kept_c, kept_o = composed[plan.id], origin[plan.id]
            emit("slide_step", slide_id=plan.id, step="design")
            again_made = await designed(
                index,
                plan,
                d,
                shot,
                image,
                note=f" (Your last cover failed the browser check: {failed}. Keep it simpler.)",
            )
            attempts[plan.id] += 1
            if again_made is not None and not isinstance(again_made, Err):
                composed[plan.id], origin[plan.id] = again_made.value, "repaired"
                fresh = await measure(plan)
                if _errors(fresh) <= _errors(m):
                    m = fresh
                else:
                    composed[plan.id], origin[plan.id] = kept_c, kept_o
                    m = await measure(plan)
        if broken(m) and origin[plan.id] != "fallback":
            refusals[plan.id] = f"still defective: {sorted({x.code for x in m.defects()})}"
            kept_c, kept_o = composed[plan.id], origin[plan.id]
            composed[plan.id], origin[plan.id] = design.fallback(plan, theme), "fallback"
            floor = await measure(plan)
            if _errors(floor) < _errors(m):
                m = floor
            else:
                composed[plan.id], origin[plan.id] = kept_c, kept_o
                m = await measure(plan)

        if logo is not None and not broken(m) and wants_logo(index):
            m = await with_logo(index, plan, m, logo)
        if image and not broken(m):
            m = await with_picture(plan, m, shot[0] if shot else "")
        finish(index, plan, m)  # whatever is still broken is flagged, never hidden

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
    # its call warms the prompt cache every other slide then reads.
    if plans:
        await make(0, plans[0])
    await asyncio.gather(*(make(i, p) for i, p in enumerate(plans) if i > 0))
    emit("stage", name="compose", state="done")

    # Layer 5: the deck review sees every slide at once and sends back at most
    # two, each redone by the improver with its note; kept only if no worse.
    if (
        improving
        and affordable()
        and len(measured) >= 3
        and any(p.id not in resumed for p in plans)
    ):
        emit("stage", name="review", state="started")
        order = [p for p in plans if p.id in measured]
        shots = [(p.id, Path(shots_dir) / f"{p.id}.png") for p in order]
        verdict = await review.review(
            seam, shots, prefix=head, model=model, thought=storyline.governing_thought
        )
        if not isinstance(verdict, Err):
            emit(
                "review",
                scores=verdict.value.scores.model_dump(),
                redo=[r.id for r in verdict.value.redo],
            )
            for redo in verdict.value.redo:
                plan = next(p for p in order if p.id == redo.id)
                # ponytail: a slide that already carries the logo or its picture is
                # left as it is: the redo is written from the code, which the sanitizer
                # strips of both. Upgrade: review before placing them.
                placed = "<dd-logo" in composed[plan.id].html or "<img" in composed[plan.id].html
                if plan.id in resumed or placed or not affordable():
                    continue
                before = measured[plan.id]
                better = await improve.improve(
                    seam,
                    plan,
                    composed[plan.id],
                    improve.shot(Path(shots_dir) / f"{plan.id}.png"),
                    before.defects(),
                    direction.of(plan.id),
                    prefix=head,
                    model=model,
                    note=redo.note,
                )
                attempts[plan.id] += 1
                if isinstance(better, Err):
                    continue
                kept_c, composed[plan.id] = composed[plan.id], better.value[0]
                again = await measure(plan)
                if _errors(again) <= _errors(before) and not broken(again):
                    measured[plan.id], origin[plan.id] = again, "improved"
                    improved.add(plan.id)
                    if on_final is not None:
                        on_final(plan.id, Kept(composed[plan.id], origin[plan.id]))
                else:
                    composed[plan.id] = kept_c
                    measured[plan.id] = await measure(plan)  # its screenshot back on disk
        emit("stage", name="review", state="done")

    plans = [p for p in plans if p.id in measured]  # an abort keeps only what is done
    rhythm = metrics.deck_warnings(
        [measured[p.id].fingerprint for p in plans], [measured[p.id].centred for p in plans]
    )
    slides: list[Slide] = []
    for index, plan in enumerate(plans):
        m = measured[plan.id]
        m.warnings += [browser._Found(**w.model_dump()) for w in rhythm.get(index, [])]
        slides.append(
            _slide(
                plan,
                composed[plan.id],
                origin[plan.id],
                m,
                attempts[plan.id],
                sum(e.cost_usd for e in seam.ledger if e.slide_id == plan.id),
            )
        )
    kept = {p.id: Kept(composed[p.id], origin[p.id]) for p in plans}
    html, send = export(theme, plans, kept, title)
    emit("done", seconds=round(time.monotonic() - started, 1))
    return Built(
        slides, html, send, time.monotonic() - started, len(first_clean), len(improved), refusals
    )


# Beats where a screenshot the outline did not place belongs (one uploaded
# after the outline was written).
_SHOW = ("demo", "product", "how it works", "user flow", "solution", "what is new")


def _place_screens(
    plans: list[SlidePlan], shots: Mapping[int, tuple[str, str, str]]
) -> list[SlidePlan]:
    """Every ready screenshot on a slide: the outline's choice first, then the
    rest in order on the slides whose beat shows the product."""
    placed = {p.screenshot for p in plans if p.screenshot}
    waiting = [n for n in sorted(shots) if n not in placed]
    out = []
    for p in plans:
        free = p.screenshot is None and p.chart is None
        if waiting and free and any(b in p.beat.lower() for b in _SHOW):
            p = p.model_copy(update={"screenshot": waiting.pop(0), "visual": None})
        out.append(p)
    return out


def _slide(
    plan: SlidePlan, c: Composed, origin: str, m: browser.Measured, attempts: int, cost: float
) -> Slide:
    status: Literal["passed", "flagged", "unmeasured"] = (
        "unmeasured" if not m.measured else "flagged" if m.errors else "passed"
    )
    return Slide(
        id=plan.id,
        plan_id=plan.id,
        html=frame(plan, c).html,  # with its chart and visual drawn
        css=c.css,
        fields={f.name: f.text for f in plan.fields},
        origin=origin,  # type: ignore[arg-type]  # set only to the literals
        attempts=attempts,
        qa=SlideQA(
            status=status,
            errors=m.defects(),
            warnings=m.warned(),
            fingerprint=m.fingerprint,
            screenshot=f"{plan.id}.png",
        ),
        cost_usd=cost,
    )


# --- after the build, no model: the worker's editor uses these ----------------


def export(
    theme: Theme, plans: list[SlidePlan], kept: dict[str, Kept], title: str
) -> tuple[str, str]:
    """Both flavours from finished slides. A chart's values ride in the notes
    too: the presenter can read them out, and readers of the sent file get
    them as text."""
    plans = [p for p in plans if p.id in kept]
    frames = [frame(p, kept[p.id].composed) for p in plans]
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
    frames = [frame(p, kept[p.id].composed) for p in plans]
    fields = {p.id: {f.name: f.text for f in p.fields} for p in plans}
    result = await browser.measure(theme, frames, fields, work_file, shots_dir)
    return {
        p.id: _slide(p, kept[p.id].composed, kept[p.id].origin, result[p.id], 0, 0.0) for p in plans
    }


def code_built(plan: SlidePlan, theme: Theme) -> Kept:
    """ "Fit to slide": the slide rebuilt by code, so its words fit by construction."""
    return Kept(design.fallback(plan, theme), "fallback")
