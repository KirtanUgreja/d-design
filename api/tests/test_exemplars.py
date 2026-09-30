"""Every exemplar passes the sanitizer, the lint and the browser checks under
every theme. This is the free end-to-end test of the whole QA path: no model."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import NoReturn

from engine.compose.document import Frame
from engine.compose.exemplars import ARCHETYPES, load_all
from engine.design.theme import THEMES
from engine.qa import browser
from engine.qa.lint import lint
from engine.qa.sanitize import sanitize
from lib.result import Ok


def test_library_covers_every_archetype_twice() -> None:
    by = [e.archetype for e in load_all()]
    assert all(by.count(a) >= 2 for a in ARCHETYPES)


def test_exemplars_pass_sanitize_and_lint() -> None:
    for e in load_all():
        clean = sanitize(e.html, frozenset(e.fields))
        assert isinstance(clean, Ok), (e.id, clean)
        assert lint(e.css) == [], (e.id, lint(e.css))


def test_exemplars_pass_browser_qa_under_every_theme(tmp_path: Path) -> None:
    exemplars = load_all()
    frames = [Frame(e.id, e.html, e.css) for e in exemplars]
    fields = {e.id: e.fields for e in exemplars}
    for theme in THEMES.values():
        shots = tmp_path / theme.id
        shots.mkdir()
        result = asyncio.run(
            browser.measure(theme, frames, fields, str(tmp_path / "qa.html"), str(shots))
        )
        bad = {
            k: [(d.code, d.field, d.measured) for d in v.errors]
            for k, v in result.items()
            if v.errors or not v.measured
        }
        assert bad == {}, (theme.id, bad)


def test_fallback_passes_qa_for_every_bench_slide(tmp_path: Path) -> None:
    # The last rung before a flag must never itself be broken.
    from benchtools import files
    from engine.compose import author

    plans = [p for b in files.brief_ids() for p in (files.load(b).outline or _none()).slides]
    assert len(plans) > 100
    frames, fields = [], {}
    for n, plan in enumerate(plans):
        composed = author.fallback(plan)
        sid = f"f{n}"
        frames.append(Frame(sid, composed.html, composed.css))
        fields[sid] = {f.name: f.text for f in plan.fields}
        assert lint(composed.css) == []
    for theme in THEMES.values():
        result = asyncio.run(browser.measure(theme, frames, fields, str(tmp_path / "f.html")))
        bad = {
            k: [(d.code, d.field, d.measured) for d in v.errors]
            for k, v in result.items()
            if v.errors or not v.measured
        }
        assert bad == {}, (theme.id, bad)


def _none() -> NoReturn:
    raise AssertionError("a bench brief has no frozen outline")
