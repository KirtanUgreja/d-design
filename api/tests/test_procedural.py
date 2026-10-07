"""Phase 36: the code-built layout passes QA for every bench slide under
generated identities, from targets, with no stored layout."""

from __future__ import annotations

import asyncio
import random
from pathlib import Path

from benchtools import files
from engine.compose import planner, procedural, targets
from engine.compose.archive import Archive
from engine.compose.document import Frame
from engine.design.sampler import draw
from engine.design.theme import build
from engine.qa import browser

LOOKS = 8  # 30 looks x 109 slides passed by hand on 2026-10-07


def test_procedural_slides_pass_qa(tmp_path: Path) -> None:
    plans = []
    for brief_id in files.brief_ids():
        outline = files.load(brief_id).outline
        assert outline is not None
        plans += [(brief_id, p) for p in planner.assign(outline.slides)]
    rng = random.Random(36)
    broken: list[tuple[str, list[str]]] = []
    for n in range(LOOKS):
        theme = build(draw(rng, f"proc{n}", 0, "auto", None))
        frames, fields = [], {}
        # per deck: one identity, so a CSS difference is a layout difference
        layouts: dict[str, set[str]] = {}
        drawn: dict[str, int] = {}
        previous = None
        for brief_id, plan in plans:
            previous = targets.draw(rng, Archive(), plan.intent, len(plan.fields), previous)
            composed = procedural.build(plan, previous, theme)
            slide_id = f"{brief_id}-{plan.id}"
            frames.append(Frame(slide_id, composed.html, composed.css))
            fields[slide_id] = {f.name: f.text for f in plan.fields}
            if plan.chart is None:  # chart slides share one code layout until phase 37
                layouts.setdefault(brief_id, set()).add(composed.css)
                drawn[brief_id] = drawn.get(brief_id, 0) + 1
        result = asyncio.run(
            browser.measure(theme, frames, fields, str(tmp_path / "qa.html"), pixels=False)
        )
        broken += [(k, [e.code for e in m.errors]) for k, m in result.items() if m.errors]
        repeats = {b: drawn[b] - len(css) for b, css in layouts.items() if len(css) < drawn[b]}
        # Clamped targets can still meet (two full-width statements): at most
        # one repeat in a deck. The fallback is rare (3 of 327 slides on the
        # 2026-10-08 bench), and the novelty gate never sees fallbacks.
        assert all(r <= 1 for r in repeats.values()), (n, repeats)
    assert broken == []


def test_neighbouring_fallbacks_never_share_a_method() -> None:
    rng = random.Random(5)
    for _ in range(200):
        t = targets.draw(rng, Archive(), "statement", 2)
        avoid = {procedural.method(t)}
        assert procedural.method(procedural.vary(t, avoid)) not in avoid
