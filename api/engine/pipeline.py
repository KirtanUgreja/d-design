"""The orchestrator: plain functions, in order, with every next step decided
here. No framework, and the model decides nothing about control flow.

Phase 22 scope: a frozen storyline in, a measured deck out.
"""

from __future__ import annotations

import asyncio
import dataclasses
import random
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from engine.components import charts, visuals
from engine.components import images as pictures
from engine.components import logo as logos
from engine.compose import author, planner, procedural, references, targets
from engine.compose.archive import Archive
from engine.compose.author import Composed
from engine.compose.document import Frame
from engine.compose.planner import TEXTURE_EVERY
from engine.compose.references import Reference
from engine.design import languages
from engine.design.theme import Theme
from engine.export.assemble import assemble
from engine.llm.openrouter import ModelError, Seam
from engine.models import Slide, SlidePlan, SlideQA, Storyline
from engine.qa import browser, metrics
from engine.qa import score as scoring
from engine.qa.descriptors import Descriptors, describe, distance
from engine.qa.sanitize import sanitize
from lib.result import Err, Ok, Result

PARALLEL = 5
REPAIR_ROUNDS = 2
# Closer than this to any archived slide, or any slide in the deck, is a
# near-repeat. ponytail: provisional; tuned on the sameness bench (phase 36).
NOVELTY_EPSILON = 0.08
STEER = (
    "This composition came out too close to another slide in this deck (distance {d:.2f} of "
    "1). Keep the reference's system and the words; move the visual mass and the open field "
    "somewhere else, and change the scale relation."
)
# Each language has one reference per shape for most shapes, so a deck with two
# number slides reuses one (live deck, 2026-10-09: three alike in a row).
REPEAT = (
    "Slide {n} of this deck was already adapted from this reference. Keep its system and the "
    "words, but make this slide clearly different from slide {n}: put the hero on another side "
    "or above instead of beside, give the colour field to another block, and change the scale "
    "relation between the figure and the headline."
)
# A language's signature shape on every slide reads as a template (live deck,
# 2026-10-09: the same circle on 8 of 10). After this many, slides go without.
SHAPE_CAP = 3
NO_SHAPE = (
    "Leave out the reference's dd-shape on this slide: this deck already has enough of them. "
    "Carry the composition with type scale, a colour field and the grid instead."
)
IMAGE_CAP = 6  # images in one deck, at most (phase 39 -> 5)


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
    # Charts and visuals are drawn by our code after sanitizing, so QA measures them too.
    drawn = charts.fill(c.html, plan.chart)
    drawn = visuals.fill(drawn, plan.visual) if plan.visual else visuals.strip(drawn)
    return Frame(plan.id, drawn, c.css)


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
    ref_usage: Mapping[str, int] | None = None,
    image_model: str = "",
    candidates: int = 1,
) -> Built:
    """Every slide climbs its own ladder, concurrently: compose from its
    reference, measure, up to REPAIR_ROUNDS repairs, one fresh composition from
    the alternate reference (with one repair), the reference filled by code,
    the code-built layout, then the flag (phase 39 -> 4). A
    slide is announced the moment it is final, so a watch fills slot by slot
    with what really happened (docs/v4/engine.md -> "Generation jobs and events").

    For the worker: ``prebuilt`` slides (finished before a crash) are only
    measured again, never paid for twice; ``on_final`` hears each slide the
    moment it is final, so it can be persisted; ``stop`` (an abort) starts no
    new slide and no new model call, and the deck keeps what is done."""
    started = time.monotonic()
    # The deck's visual language (design/languages.py) sets its texture policy,
    # whether it may use shapes, its image budget and its references.
    lang = languages.get(theme.language) if theme.language else None
    every = {"never": 0, "rare": 4, "often": 2}[lang.texture] if lang else TEXTURE_EVERY
    shapes = bool(lang and lang.shapes)
    plans = planner.assign(storyline.slides, every)
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
    # Every slide's reference and alternate, picked in deck order: no reference
    # twice in a deck, the least used across decks, images within the budget,
    # and never the same variation twice in a row.
    refs: dict[str, tuple[Reference | None, Reference | None]] = {}
    variation: dict[str, str] = {}
    image_on: dict[str, bool] = {}
    # No image model (offline runs, the bench without images): no image slots.
    appetite = lang.image.appetite if lang and image_model else 0.0
    images_left = min(IMAGE_CAP, max(1, round(appetite * len(plans)))) if appetite else 0
    used: set[str] = set()
    first_use: dict[str, tuple[int, str]] = {}  # reference id -> (slide number, its variation)
    shaped = 0  # slides whose reference carries a dd-shape
    repeat: dict[str, str] = {}  # slide id -> how to tell it apart from the earlier use
    last = ""
    for n, plan in enumerate(plans, start=1):
        pair = (
            references.pick(
                lang.id,
                plan,
                used_in_deck=frozenset(used),
                usage=ref_usage,
                images_left=images_left,
            )
            if lang
            else (None, None)
        )
        refs[plan.id] = pair
        first = pair[0]
        earlier = first_use.get(first.id) if first is not None else None
        # A slide with a drawn visual takes no picture: the visual is its hero.
        image_on[plan.id] = bool(
            first and first.image != "none" and images_left > 0 and plan.visual is None
        )
        images_left -= image_on[plan.id]
        options = [v for v in (first.variants if first else ()) if v != last]
        if earlier is not None:  # the only reference for its shape, used again
            options = [v for v in options if v != earlier[1]] or options
            repeat[plan.id] = REPEAT.format(n=earlier[0])
        if first is not None and "<dd-shape" in first.html:
            shaped += 1
            if shaped > SHAPE_CAP:
                repeat[plan.id] = f"{repeat.get(plan.id, '')} {NO_SHAPE}".strip()
        variation[plan.id] = last = rng.choice((options if earlier else []) or ["", *options])
        if first is not None:
            used.add(first.id)
            first_use.setdefault(first.id, (n, variation[plan.id]))
    accepted: dict[str, Descriptors] = {}
    steered: set[str] = set()
    fields = {p.id: {f.name: f.text for f in p.fields} for p in plans}
    gate = asyncio.Semaphore(PARALLEL)
    browsers = asyncio.Semaphore(MEASURE_PARALLEL)
    origin: dict[str, str] = {}
    ref_used: dict[str, str] = {}  # slide id -> the reference its composition came from
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
        """Within this deck only: across decks, reference rotation and the
        language draw do that job, and retrying a reference's own geometry
        would only spend money (phase 39 -> 4)."""
        return min((distance(d, e) for k, e in accepted.items() if k != slide_id), default=1.0)

    def ref_filled(plan: SlidePlan, ref: Reference) -> Composed | None:
        """The reference with this slide's words, no model: the rung before
        the code layout. None when it cannot hold this slide."""
        html = references.fill(ref, fields[plan.id], image=image_on[plan.id])
        clean = sanitize(html, frozenset(fields[plan.id]))
        if isinstance(clean, Err) or (plan.chart is not None) != ("<dd-chart" in clean.value):
            return None
        return Composed(clean.value, ref.css + references.fit_css(ref, fields[plan.id]))

    async def compose_from(
        index: int, plan: SlidePlan, ref: Reference | None, var: str, steer: str = ""
    ) -> Result[Composed, ModelError]:
        steer = steer or repeat.get(plan.id, "")
        async with gate:
            return await author.compose(
                seam,
                theme,
                plan,
                model=model,
                position=index + 1,
                total=len(plans),
                thought=storyline.governing_thought,
                reference=ref,
                variation=var,
                image=image_on[plan.id],
                shapes=shapes,
                steer=steer,
            )

    async def novelty(index: int, plan: SlidePlan, m: browser.Measured) -> browser.Measured:
        """One steered retry for a near-repeat; then accept it, warned and
        counted. Cost stays bounded: never a loop."""
        d = describe(m.boxes, m.shapes)
        near = nearest(d, plan.id)
        if near < NOVELTY_EPSILON and origin[plan.id] in ("authored", "repaired") and affordable():
            steered.add(plan.id)
            retry = await compose_from(
                index, plan, refs[plan.id][0], variation[plan.id], STEER.format(d=near)
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

    async def picture(plan: SlidePlan) -> str:
        """The slide's image as our own webp data URL, or "" (a quiet field).
        Drawn while the slide is composed, never before or after it."""
        first = refs[plan.id][0]
        if first is None or not affordable():
            return ""
        style = theme.look.get("image", "editorial photography")
        made = await seam.complete_image(
            pictures.prompt(plan, style, theme.colors.get("accent", ""), deck=title),
            model=image_model,
            aspect=pictures.aspect_of(first.html),
            slide_id=plan.id,
        )
        if isinstance(made, Err):
            return ""
        treated = pictures.treat(made.value, pictures.aspect_of(first.html))
        return "" if isinstance(treated, Err) else pictures.data_url(treated.value)

    async def with_picture(plan: SlidePlan, m: browser.Measured, url: str) -> browser.Measured:
        """The picture into its slot, measured again; taken out if anything broke."""
        kept = composed[plan.id]
        if not url or "<dd-image" not in kept.html:
            return m
        composed[plan.id] = Composed(pictures.fill(kept.html, url), kept.css)
        placed = await measure(plan)
        if not broken(placed):
            return placed
        composed[plan.id] = kept
        return await measure(plan)

    async def best_of(index: int, plan: SlidePlan) -> Result[Composed, ModelError]:
        """The first composition, or the best of ``candidates`` by the measured
        design score (qa/score.py): each drawn with its own variation, all
        measured, a clean one always beating a broken one."""
        first = refs[plan.id][0]
        if candidates <= 1:
            return await compose_from(index, plan, first, variation[plan.id])
        options = [variation[plan.id], *(first.variants if first else ())]
        tries = await asyncio.gather(
            *(
                compose_from(index, plan, first, options[n % len(options)])
                for n in range(candidates)
            )
        )
        made = [t.value for t in tries if not isinstance(t, Err)]
        if not made:
            return tries[0]
        ranked: list[tuple[float, Composed]] = []
        for option in made:
            composed[plan.id] = option
            m = await measure(plan)
            ranked.append((scoring.score(m.boxes, m.shapes, errors=len(m.errors)).total, option))
        return Ok(max(ranked, key=lambda r: r[0])[1])

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
        drawing = asyncio.create_task(picture(plan)) if image_on[plan.id] else None
        result = None
        if affordable():
            result = await best_of(index, plan)
        if result is None or isinstance(result, Err):
            if result is not None:
                refusals[plan.id] = f"{result.error.kind}: {result.error.detail[:300]}"
            first = refs[plan.id][0]
            filled = ref_filled(plan, first) if first else None
            if filled is not None:
                composed[plan.id], origin[plan.id] = filled, "reference"
                ref_used[plan.id] = first.id if first else ""  # set: filled needs it
            else:
                composed[plan.id], origin[plan.id] = code_built(plan), "fallback"
                ref_used[plan.id] = ""
        else:
            composed[plan.id], origin[plan.id] = result.value, "authored"
            first = refs[plan.id][0]
            ref_used[plan.id] = first.id if first else ""
        m = await measure(plan)
        if not broken(m):
            first_clean.add(plan.id)

        # Rung 1: targeted repair from the measured defects.
        for _ in range(REPAIR_ROUNDS):
            if not broken(m) or origin[plan.id] not in ("authored", "repaired") or not affordable():
                break
            async with gate:
                fixed = await author.repair(
                    seam,
                    theme,
                    plan,
                    composed[plan.id],
                    m.defects(),
                    model=model,
                    shapes=shapes,
                )
            attempts[plan.id] += 1
            if isinstance(fixed, Err):
                break
            composed[plan.id], origin[plan.id] = fixed.value, "repaired"
            m = await measure(plan)

        # Rung 2: one fresh composition from the alternate reference, and one
        # repair. A filled or code-built slide is a fallback, so a failed first
        # answer gets this too.
        fell_back = origin[plan.id] in ("fallback", "reference")
        if (broken(m) or fell_back) and result is not None and affordable():
            alternate = refs[plan.id][1] or refs[plan.id][0]
            choices = alternate.variants if alternate else ()
            other = [v for v in choices if v != variation[plan.id]]
            fresh = await compose_from(index, plan, alternate, rng.choice(other) if other else "")
            attempts[plan.id] += 1
            if not isinstance(fresh, Err):
                kept, composed[plan.id] = composed[plan.id], fresh.value
                again = await measure(plan)
                if broken(again) and affordable():
                    async with gate:
                        fixed = await author.repair(
                            seam,
                            theme,
                            plan,
                            composed[plan.id],
                            again.defects(),
                            model=model,
                            shapes=shapes,
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
                    ref_used[plan.id] = alternate.id if alternate else ""

        # Rung 3: the reference filled by code, then the alternate's.
        if broken(m):
            refusals[plan.id] = (
                f"still defective after repair: {sorted({d.code for d in m.defects()})}"
            )
            for ref in (r for r in refs[plan.id] if r is not None):
                filled = ref_filled(plan, ref)
                if filled is None or filled == composed[plan.id]:
                    continue
                kept_c, kept_o = composed[plan.id], origin[plan.id]
                composed[plan.id], origin[plan.id] = filled, "reference"
                kept_r, ref_used[plan.id] = ref_used[plan.id], ref.id
                again = await measure(plan)
                if not broken(again):
                    m = again
                    break
                composed[plan.id], origin[plan.id] = kept_c, kept_o
                ref_used[plan.id] = kept_r
            else:
                m = await measure(plan)  # the kept slide's screenshot back on disk

        # Rung 4: the code-built layout, from the slide's target. No stored layout.
        if broken(m) and origin[plan.id] != "fallback":
            composed[plan.id], origin[plan.id] = code_built(plan), "fallback"
            ref_used[plan.id] = ""
            m = await measure(plan)

        # The novelty gate: quality first, then distance from everything made.
        if not broken(m):
            m = await novelty(index, plan, m)
        if logo is not None and not broken(m) and wants_logo(index):
            m = await with_logo(index, plan, m, logo)

        if drawing is not None and not broken(m):
            m = await with_picture(plan, m, await drawing)

        # Rung 5, the flag: whatever is still broken is shown, never hidden.
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
                reference=ref_used.get(plan.id, ""),
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
