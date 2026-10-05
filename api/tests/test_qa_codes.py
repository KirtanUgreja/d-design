"""One failing fixture per QA error code (phase 22 -> Verify).

Each fixture is the clean slide below with one thing broken, and must raise its
code. The clean slide must raise nothing, so a check that fires on everything
cannot pass. E10 (images) arrives with images in phase 25.

E3 and E11 each have a second fixture: lines set tighter than the display face
survives, and an empty solid field. The clean slide keeps a thin rule, a
pattern field and a colour field under text, which must all still pass.
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
    f'<p class="b" data-field="body">{BODY}</p>'
    '<dd-texture class="rule" kind="solid" tone="accent"></dd-texture>'
    '<dd-texture class="dots" kind="halftone" tone="accent"></dd-texture></section>'
)
CSS = (
    ".s{padding:var(--margin);display:grid;align-content:start;gap:var(--s-4)}"
    ".h{font-family:var(--f-display);font-weight:var(--w-display);font-size:var(--t-h1)}"
    ".b{font-size:var(--t-body);background-color:var(--c-surface)}"
    ".rule{position:absolute;left:0;bottom:0;width:1920px;height:24px}"
    ".dots{position:absolute;right:0;top:0;width:400px;height:1080px}"
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
    "E3-leading": (".h{width:900px;line-height:0.8}", FIELDS),
    "E11": (".rule{height:400px;width:600px}", FIELDS),
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
    assert {k: sorted(c) for k, c in got.items() if k.split("-")[0] not in c} == {}


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


def test_e5_on_pixels_sees_text_over_a_texture(tmp_path: Path) -> None:
    # The computed-colour check sees the plain ground behind the body and
    # passes it; the screenshot sees the ink-coloured dots under the words.
    html = HTML.replace(
        "</section>", '<dd-texture class="dots" kind="halftone" tone="ink"></dd-texture></section>'
    )
    css = CSS + (
        ".b{position:relative;z-index:2}"
        ".dots{position:absolute;left:0;top:0;width:1920px;height:1080px;z-index:1}"
    )
    frames = [Frame("tex", html, css)]
    result = asyncio.run(browser.measure(THEME, frames, {"tex": FIELDS}, str(tmp_path / "q.html")))
    e5 = [d for d in result["tex"].errors if d.code == "E5"]
    assert e5 and all("pixels" in str(d.measured) for d in e5)
    off = asyncio.run(
        browser.measure(THEME, frames, {"tex": FIELDS}, str(tmp_path / "r.html"), pixels=False)
    )
    assert not [d for d in off["tex"].errors if d.code == "E5"]
