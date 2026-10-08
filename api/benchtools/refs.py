"""The reference QA harness and wall (docs/v4/plan/39-design-reset.md -> 2).

``check`` fills every reference of a language with long and with short words
and measures it in Chromium under sampled looks of that language: zero errors
is the bar. ``wall`` renders every reference under two looks with real words,
one screenshot each, on one page the owner curates. No model call; $0.
"""

from __future__ import annotations

import asyncio
import html
import random
from pathlib import Path

from engine.compose import references
from engine.compose.document import Frame
from engine.compose.references import FIELDS, Reference
from engine.design.languages import all_languages, get
from engine.design.sampler import draw, seed_of
from engine.design.theme import Theme, build
from engine.qa import browser
from engine.qa.lint import lint
from engine.qa.sanitize import sanitize
from lib.result import Err

# The longest and shortest words a field carries on the 12 bench outlines.
LONG: dict[str, str] = {
    "kicker": "Series A · Q3 2026 board update",
    "headline": "Teams that close their books in two days grow revenue faster than their peers",
    "point-1": "Reconciliation runs every night, so nothing waits for month end",
    "point-2": "Every number links back to the ledger line it came from",
    "point-3": "Controllers review exceptions instead of rebuilding spreadsheets",
    "stat": "8 months",  # real figures carry words (the 2026-10-08 bench)
    "stat-label": "annual recurring revenue, up from $1.1M eighteen months ago",
    "source": "Company finance data, September 2026",
}
# A slide with only its claim: every block whose fields are gone must close.
SPARSE: dict[str, str] = {"kicker": "Team", "headline": "Who builds it"}
SHORT: dict[str, str] = {
    "kicker": "Why now",
    "headline": "Close in two days",
    "point-1": "Nightly sync",
    "point-2": "Linked lines",
    "point-3": "Fewer errors",
    "stat": "3x",
    "stat-label": "faster close",
    "source": "Internal data",
}


def themes(language: str, n: int, *, salt: str = "refs") -> list[Theme]:
    """``n`` sampled looks of one language, the same every run."""
    lang = get(language)
    out = []
    for i in range(n):
        rng = random.Random(seed_of(f"{salt}/{language}/{i}"))  # noqa: S311 - a look
        out.append(build(draw(rng, f"{language}-{i}", i, "auto", None, language=lang)))
    return out


def _words(ref: Reference, which: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in which.items() if k in ref.fields}


def static_problems(ref: Reference) -> list[str]:
    """What is wrong without a browser: fields, sanitizer, lint."""
    problems = []
    missing = FIELDS[ref.shape] - ref.fields
    if missing:
        problems.append(f"missing fields for a {ref.shape}: {sorted(missing)}")
    if references.field_names(ref.html) != ref.fields:
        problems.append("the html's data-fields differ from the metadata's fields")
    if (ref.image == "none") == ("<dd-image" in ref.html):
        problems.append("the image slot and the metadata disagree")
    if ref.shape == "chart" and "<dd-chart" not in ref.html:
        problems.append("a chart reference needs an empty <dd-chart>")
    for label, words in (("long", LONG), ("short", SHORT), ("sparse", SPARSE)):
        clean = sanitize(references.fill(ref, _words(ref, words)), ref.fields)
        if isinstance(clean, Err):
            problems.append(f"sanitize ({label}): {clean.error}")
    problems += [f"lint: {p}" for p in lint(ref.css)]
    return problems


async def check(language: str, looks: int = 30, work: Path | None = None) -> dict[str, list[str]]:
    """Every problem per reference id, across ``looks`` looks; empty = pass."""
    refs = [r for r in references.load_all() if r.language == language]
    found: dict[str, list[str]] = {r.id: static_problems(r) for r in refs}
    frames, fields = [], {}
    for r in refs:
        for label, words in (("long", LONG), ("short", SHORT), ("sparse", SPARSE)):
            sid = f"{r.id.replace('/', '-')}-{label}"
            clean = sanitize(references.fill(r, _words(r, words)), r.fields)
            if isinstance(clean, Err):
                continue
            frames.append(Frame(sid, clean.value, r.css + references.fit_css(r, _words(r, words))))
            fields[sid] = _words(r, words)
    if not frames:
        return found
    work = work or Path("/tmp")  # noqa: S108 - a scratch page, rewritten each run
    for theme in themes(language, looks):
        result = await browser.measure(theme, frames, fields, str(work / f"refs-{language}.html"))
        for sid, measured in result.items():
            rid = sid.rsplit("-", 1)[0]
            ref_id = next(r.id for r in refs if r.id.replace("/", "-") == rid)
            if not measured.measured:
                found[ref_id].append(f"{sid}: not measured under {theme.id}")
            for d in measured.errors:
                found[ref_id].append(f"{sid} under {theme.id}: {d.code} {d.field} {d.measured}")
    return {k: sorted(set(v)) for k, v in found.items()}


async def wall(out: Path, languages: list[str] | None = None, looks: int = 2) -> Path:
    """Every reference, long words, under ``looks`` looks: PNGs and one page."""
    out.mkdir(parents=True, exist_ok=True)  # noqa: ASYNC240 - a local bench page
    rows = []
    for lang in [x.id for x in all_languages() if not languages or x.id in languages]:
        refs = [r for r in references.load_all() if r.language == lang]
        if not refs:
            continue
        frames = []
        fields = {}
        for r in refs:
            sid = r.id.replace("/", "-")
            clean = sanitize(references.fill(r, _words(r, LONG)), r.fields)
            if isinstance(clean, Err):
                continue
            frames.append(Frame(sid, clean.value, r.css + references.fit_css(r, _words(r, LONG))))
            fields[sid] = _words(r, LONG)
        for i, theme in enumerate(themes(lang, looks, salt="wall")):
            shots = out / lang / str(i)
            shots.mkdir(parents=True, exist_ok=True)
            await browser.measure(theme, frames, fields, str(out / "work.html"), str(shots))
        cells = "".join(
            f'<figure><img src="{lang}/{i}/{r.id.replace("/", "-")}.png" loading="lazy">'
            f"<figcaption>{html.escape(r.id)} · {html.escape(r.idea)}</figcaption></figure>"
            for r in refs
            for i in range(looks)
        )
        rows.append(f"<h2>{html.escape(get(lang).name)}</h2><div class=g>{cells}</div>")
    page = out / "index.html"
    page.write_text(
        "<!doctype html><meta charset=utf-8><title>References</title><style>"
        "body{font:14px system-ui;margin:24px;background:#eee}"
        ".g{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}"
        "img{width:100%;display:block;box-shadow:0 1px 3px #0003}"
        "figure{margin:0}figcaption{padding:4px 0}</style>" + "".join(rows)
    )
    return page


def run_check(language: str, looks: int) -> int:
    found = asyncio.run(check(language, looks))
    bad = {k: v for k, v in found.items() if v}
    for ref_id, problems in sorted(found.items()):
        print(f"{'FAIL' if problems else 'ok  '} {ref_id}")
        for p in problems[:12]:
            print(f"     {p}")
    print(f"{len(found) - len(bad)}/{len(found)} references pass under {looks} looks")
    return 1 if bad or not found else 0
