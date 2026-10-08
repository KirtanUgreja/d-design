"""The reference library as a whole (phase 39 -> Verify): every language
covers every shape, every bench slide gets a reference of its shape in every
language, and that reference filled by code passes QA."""

from __future__ import annotations

import asyncio
from pathlib import Path

from benchtools import files, refs
from engine.compose import planner, references
from engine.compose.document import Frame
from engine.design.languages import all_languages
from engine.models import SlidePlan
from engine.qa import browser
from engine.qa.sanitize import sanitize
from lib.result import Ok


def _bench() -> list[SlidePlan]:
    out: list[SlidePlan] = []
    for brief_id in files.brief_ids():
        outline = files.load(brief_id).outline
        if outline is not None:
            out += planner.assign(outline.slides, 0)
    return out


def test_every_language_covers_every_shape() -> None:
    for lang in all_languages():
        shapes = {r.shape for r in references.load_all() if r.language == lang.id}
        assert shapes == set(references.SHAPES), (lang.id, set(references.SHAPES) - shapes)


def test_every_bench_slide_gets_a_reference_of_its_shape_in_every_language() -> None:
    plans = _bench()
    assert len(plans) > 100
    for lang in all_languages():
        for plan in plans:
            first, _ = references.pick(lang.id, plan)
            assert first is not None, (lang.id, plan.id)
            assert first.shape == references.shape_of(plan), (lang.id, plan.id)
            assert first.language == lang.id, (lang.id, plan.id, first.id)


def test_every_reference_passes_its_static_checks() -> None:
    bad = {r.id: refs.static_problems(r) for r in references.load_all()}
    assert {k: v for k, v in bad.items() if v} == {}


def test_reference_fill_passes_qa_for_every_bench_slide(tmp_path: Path) -> None:
    plans = _bench()
    failures: list[tuple[str, str, list[str]]] = []
    for lang in all_languages():
        theme = refs.themes(lang.id, 1, salt="bench")[0]
        frames, fields = [], {}
        for n, plan in enumerate(plans):
            ref, _ = references.pick(lang.id, plan)
            assert ref is not None
            words = {f.name: f.text for f in plan.fields}
            clean = sanitize(references.fill(ref, words, image=False), frozenset(words))
            assert isinstance(clean, Ok), (ref.id, clean)
            sid = f"b{n}"
            frames.append(Frame(sid, clean.value, ref.css + references.fit_css(ref, words)))
            fields[sid] = words
        got = asyncio.run(browser.measure(theme, frames, fields, str(tmp_path / f"{lang.id}.html")))
        for n, plan in enumerate(plans):
            m = got[f"b{n}"]
            if m.errors or not m.measured:
                ref, _ = references.pick(lang.id, plan)
                codes = [f"{d.code} {d.field} {d.measured}" for d in m.errors]
                failures.append((lang.id, ref.id if ref else "", codes))
    assert failures == [], failures[:20]
