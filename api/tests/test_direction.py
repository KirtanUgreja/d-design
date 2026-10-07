"""Per-deck art direction and the shape vocabulary (owner, 2026-10-08: a deck
that differs only in font and palette is the same design)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from benchtools import files
from engine import Seam
from engine.compose import author
from engine.compose.document import Frame
from engine.design import direction
from engine.design.patterns import SHAPES
from engine.design.theme import THEMES
from engine.qa import browser
from engine.qa.sanitize import sanitize
from lib.result import Ok
from tests.test_ladder import _no_sleep


def _option(name: str, typical: float) -> dict[str, object]:
    return {
        "name": name,
        "idea": f"{name} idea",
        "type": "giant cropped numerals",
        "shapes": ["arc", "blob"],
        "shape_use": "one huge arc bleeding off a corner",
        "composition": ["mass low", "one shape per slide"],
        "never": ["thin rules", "small labels"],
        "texture": "never",
        "typicality": typical,
    }


class Directions:
    async def post(self, url: str, *, json: object, headers: dict[str, str]) -> httpx.Response:
        body = {"directions": [_option("Usual", 0.8), _option("Odd", 0.2), _option("Mid", 0.5)]}
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": _dump(body)}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.001},
            },
        )


def _dump(body: object) -> str:
    return json.dumps(body)


def test_the_least_typical_direction_is_kept() -> None:
    outline = files.load("pitch-devtools").outline
    assert outline is not None
    seam = Seam(api_key="k", transport=Directions(), sleep=_no_sleep)
    got = asyncio.run(direction.direct(seam, outline, THEMES["ledger"], title="t", model="m"))
    assert isinstance(got, Ok) and got.value.name == "Odd"


def test_the_prompt_carries_the_direction_and_no_house_style() -> None:
    d = direction.Direction.model_validate(_option("Odd", 0.2))
    text = author.prefix(THEMES["ledger"], direction.render(d))
    assert "ART DIRECTION FOR THIS DECK — Odd" in text and "arc, blob" in text
    assert "Use rules" not in text and "much bigger than everything else" not in text
    assert "senior editorial designer" not in text


def test_shapes_survive_the_sanitizer_and_unknown_kinds_fall_back() -> None:
    clean = sanitize(
        '<section class="s"><h1 data-field="headline">Hi</h1>'
        '<dd-shape class="a" kind="arc" tone="ink"></dd-shape>'
        '<dd-shape class="b" kind="dragon" tone="neon"></dd-shape></section>',
        frozenset({"headline"}),
    )
    assert isinstance(clean, Ok)
    assert 'kind="arc"' in clean.value and 'tone="ink"' in clean.value
    assert 'kind="disc"' in clean.value and 'tone="accent"' in clean.value


def test_a_large_shape_alone_is_not_an_empty_block(tmp_path: Path) -> None:
    html = (
        '<section class="s"><h1 class="h" data-field="headline">One big arc</h1>'
        + "".join(
            f'<dd-shape class="x{i}" kind="{k}"></dd-shape>' for i, k in enumerate(SHAPES[:3])
        )
        + "</section>"
    )
    css = (
        ".s{padding:var(--margin)}.h{font-family:var(--f-display);font-size:var(--t-h1)}"
        ".x0{position:absolute;right:-200px;bottom:-200px;width:900px;height:900px}"
        ".x1{position:absolute;left:200px;top:500px;width:400px;height:400px}"
        ".x2{position:absolute;left:800px;top:300px;width:500px;height:500px}"
    )
    result = asyncio.run(
        browser.measure(
            THEMES["ledger"],
            [Frame("sh", html, css)],
            {"sh": {"headline": "One big arc"}},
            str(tmp_path / "q.html"),
        )
    )
    assert [e.code for e in result["sh"].errors] == []
    assert [s.kind for s in result["sh"].shapes].count("shape") == 3
