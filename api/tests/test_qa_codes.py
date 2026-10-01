"""One failing fixture per QA error code (phase 22 -> Verify).

Each fixture is the clean slide below with one thing broken, and must raise its
code. The clean slide must raise nothing, so a check that fires on everything
cannot pass. E10 (images) arrives with images in phase 25.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from engine.compose import document
from engine.compose.document import Frame
from engine.design.theme import THEMES
from engine.qa import browser

THEME = next(iter(THEMES.values()))
HEADLINE = "Revenue grew almost fourfold in twelve months"
BODY = "Annual recurring revenue reached two million."
FIELDS = {"headline": HEADLINE, "body": BODY}
HTML = (
    f'<section class="s"><h1 class="h" data-field="headline">{HEADLINE}</h1>'
    f'<p class="b" data-field="body">{BODY}</p></section>'
)
CSS = (
    ".s{padding:var(--margin);display:grid;align-content:start;gap:var(--s-4)}"
    ".h{font-family:var(--f-display);font-weight:var(--w-display);font-size:var(--t-h1)}"
    ".b{font-size:var(--t-body)}"
)

# code -> (extra css, fields)
BROKEN: dict[str, tuple[str, dict[str, str]]] = {
    "E1": (".b{position:absolute;left:1700px;top:600px;width:900px}", FIELDS),
    "E2": (".b{position:absolute;left:24px;top:600px}", FIELDS),
    "E3": (".h,.b{position:absolute;left:200px;top:300px}", FIELDS),
    "E4": (".b{font-size:var(--t-label)}", FIELDS),
    "E5": (".b{color:var(--c-ground)}", FIELDS),
    "E6": ("", {**FIELDS, "body": "The planned words, which the slide changed."}),
    "E7": (".b{font-size:35px}", FIELDS),
    "E9": (".h{width:260px}", FIELDS),
}


def _codes(result: dict[str, browser.Measured], slide_id: str) -> set[str]:
    m = result[slide_id]
    assert m.measured, slide_id
    return {e.code for e in m.errors}


def test_clean_slide_and_one_fixture_per_code(tmp_path: Path) -> None:
    frames = [Frame("clean", HTML, CSS)] + [
        Frame(code, HTML, CSS + css) for code, (css, _) in BROKEN.items()
    ]
    fields = {"clean": FIELDS} | {code: f for code, (_, f) in BROKEN.items()}
    result = asyncio.run(browser.measure(THEME, frames, fields, str(tmp_path / "qa.html")))
    assert _codes(result, "clean") == set()
    got = {code: _codes(result, code) for code in BROKEN}
    assert {code: sorted(c) for code, c in got.items() if code not in c} == {}


def test_e8_a_face_that_failed_to_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A theme face whose file is broken. The model cannot cause this (at-rules
    # are linted out); a bad vendored font can, and it must not pass silently.
    face = THEME.faces[0]
    weight = next(w for w in (500, 300, 800, 200, 100) if w not in face.weights)
    broken = (
        f"<style>@font-face{{font-family:'{face.family}';font-weight:{weight};"
        "src:url(data:font/woff2;base64,AAAA) format('woff2')}</style></head>"
    )

    def qa_document(theme: object, frames: list[Frame]) -> str:
        return document.qa_document(THEME, frames).replace("</head>", broken, 1)

    monkeypatch.setattr(browser, "qa_document", qa_document)
    css = CSS + f".b{{font-family:'{face.family}';font-weight:{weight}}}"
    result = asyncio.run(
        browser.measure(THEME, [Frame("e8", HTML, css)], {"e8": FIELDS}, str(tmp_path / "q.html"))
    )
    assert "E8" in _codes(result, "e8")
