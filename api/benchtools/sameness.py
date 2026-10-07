"""The sameness bench (docs/v4/plan/36-independent-design.md -> Make, 8):
how much of the composition space is used, and how often a slide repeats
one already made. Reads descriptors only — never slide text.

``report`` works on any set of compositions: the archive, one run, or a
simulation. ``simulate`` builds decks with the code-built layout from the
real targets and archive, no model call, so the exploration machinery can be
measured for free; a paid run measures the model.
"""

from __future__ import annotations

import asyncio
import random
import statistics
from dataclasses import dataclass
from pathlib import Path

from benchtools import files
from engine.compose import planner, procedural, targets
from engine.compose.archive import Archive
from engine.compose.document import Frame
from engine.design.sampler import look_for
from engine.design.theme import build
from engine.pipeline import NOVELTY_EPSILON
from engine.qa import browser
from engine.qa.descriptors import Descriptors, describe, distance


@dataclass(frozen=True)
class Report:
    slides: int
    coverage: float  # share of the MAP-Elites grid cells used
    repeat_rate: float  # share of slides within epsilon of an earlier one
    nearest_median: float
    nearest_p10: float

    def line(self) -> str:
        return (
            f"{self.slides} slides · coverage {self.coverage:.1%} · repeats "
            f"{self.repeat_rate:.1%} (ε {NOVELTY_EPSILON}) · nearest median "
            f"{self.nearest_median:.3f}, p10 {self.nearest_p10:.3f}"
        )


def report(entries: list[Descriptors]) -> Report:
    """Each slide against every slide made before it, in order."""
    nearest = [
        min(distance(d, e) for e in entries[:i]) for i, d in enumerate(entries) if i > 0
    ] or [1.0]
    ordered = sorted(nearest)
    return Report(
        slides=len(entries),
        coverage=Archive(entries).coverage(),
        repeat_rate=sum(n < NOVELTY_EPSILON for n in nearest) / len(nearest),
        nearest_median=statistics.median(nearest),
        nearest_p10=ordered[len(ordered) // 10],
    )


async def simulate(decks: int, work: Path) -> list[Report]:
    """``decks`` code-built decks over the bench outlines, each with its own
    generated look, targets drawn from a growing archive. A report after each."""
    outlines = [(b, files.load(b).outline) for b in files.brief_ids()]
    archive = Archive()
    made: list[Descriptors] = []
    reports: list[Report] = []
    for n in range(decks):
        brief_id, outline = outlines[n % len(outlines)]
        if outline is None:
            continue
        theme = build(look_for(f"sim-{n}", words=f"{brief_id} {n}"))
        rng = random.Random(f"sim/{n}")  # noqa: S311 - layout, not security
        plans = planner.assign(outline.slides)
        frames, fields, previous = [], {}, None
        for plan in plans:
            previous = targets.draw(rng, archive, plan.intent, len(plan.fields), previous)
            composed = procedural.build(plan, previous, theme)
            frames.append(Frame(plan.id, composed.html, composed.css))
            fields[plan.id] = {f.name: f.text for f in plan.fields}
        measured = await browser.measure(
            theme, frames, fields, str(work / "sim.html"), pixels=False
        )
        for plan in plans:
            m = measured[plan.id]
            d = describe(m.boxes, m.shapes)
            made.append(d)
            archive.add(d)
        reports.append(report(made))
    return reports


def run(decks: int, work: Path) -> list[Report]:
    return asyncio.run(simulate(decks, work))
