"""The player and the export on real engines (phase 26 -> Verify).

Chromium and WebKit run everywhere; Firefox runs where DD_ENGINES names it (CI).
On this project's macOS dev sandbox Firefox cannot start its helper process,
which is an environment limit, not a product finding.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest
from playwright.async_api import Browser, Page, Route, async_playwright

from engine.compose.document import Frame
from engine.design.theme import THEMES
from engine.export import pdf
from engine.export.assemble import Flavour, assemble
from tests.fakes import sample_frames

ENGINES = os.environ.get("DD_ENGINES", "chromium,webkit").split(",")
THEME = next(iter(THEMES.values()))
SECRET = "Only the presenter may read this note"


def _deck() -> tuple[list[Frame], dict[str, str]]:
    frames, _ = sample_frames(4)
    # Slide 2 reveals its fields in steps.
    second = frames[1]
    built = re.sub(r'data-field="', 'data-build="1" data-field="', second.html, count=2)
    built = re.sub(r'data-build="1" data-field="', 'data-build="2" data-field="', built, count=1)
    frames[1] = Frame(second.slide_id, built, second.css)
    notes = {f.slide_id: f"{SECRET} ({f.slide_id})" for f in frames}
    return frames, notes


def _offline(seen: list[str], allow: str) -> Callable[[Route], Awaitable[None]]:
    async def route(r: Route) -> None:
        url = r.request.url
        if url.split("#")[0] == allow or url.startswith(("data:", "about:")):
            await r.continue_()
        else:
            seen.append(url)
            await r.abort()

    return route


async def _open(browser: Browser, path: Path, seen: list[str]) -> Page:
    ctx = await browser.new_context(viewport={"width": 1280, "height": 720})
    url = "file://" + str(path)
    await ctx.route("**/*", _offline(seen, url))
    page = await ctx.new_page()
    await page.goto(url)
    await page.evaluate("document.fonts.ready")
    return page


async def _state(page: Page) -> tuple[int, str]:
    idx = await page.evaluate(
        "[...document.querySelectorAll('.dd-slide')].findIndex(s => s.classList.contains('on'))"
    )
    return idx, await page.evaluate("location.hash")


@pytest.mark.parametrize("engine", ENGINES)
def test_present_flavour_end_to_end(engine: str, tmp_path: Path) -> None:
    frames, notes = _deck()
    path = tmp_path / "deck.html"
    path.write_text(assemble(THEME, frames, "Deck", flavour="present", notes=notes))

    async def run() -> None:
        async with async_playwright() as pw:
            browser = await getattr(pw, engine).launch()
            seen: list[str] = []
            page = await _open(browser, path, seen)
            # Renders offline: every slide's shadow root is live and its fonts loaded.
            ok = await page.evaluate(
                "[...document.querySelectorAll('.dd-slide')].every(s => s.shadowRoot && "
                "s.shadowRoot.querySelector('.s'))"
            )
            assert ok
            assert await _state(page) == (0, "#1")
            await page.keyboard.press("ArrowRight")
            assert await _state(page) == (1, "#2")
            # Slide 2 has two build steps before the next slide.
            hidden = "s => [...s.shadowRoot.querySelectorAll('[data-build]')]"
            opacity = (
                "() => (" + hidden + ")(document.querySelectorAll('.dd-slide')[1])"
                ".map(e => e.style.opacity)"
            )
            assert await page.evaluate(opacity) == ["0", "0"]
            await page.keyboard.press("ArrowRight")
            assert (await _state(page))[0] == 1
            await page.keyboard.press("ArrowRight")
            assert await page.evaluate(opacity) == ["", ""]
            await page.keyboard.press("ArrowRight")
            assert (await _state(page))[0] == 2
            await page.keyboard.press("ArrowLeft")
            await page.keyboard.press("End")
            assert (await _state(page))[0] == len(frames) - 1
            await page.keyboard.press("Home")
            assert (await _state(page))[0] == 0
            await page.keyboard.type("3")
            await page.keyboard.press("Enter")
            assert await _state(page) == (2, "#3")
            await page.keyboard.press("o")
            assert await page.evaluate("document.body.classList.contains('dd-overview')")
            await page.locator(".dd-slide").nth(3).click()
            assert (await _state(page))[0] == 3
            await page.keyboard.press("b")
            assert await page.evaluate("document.body.classList.contains('dd-black')")
            await page.keyboard.press("Escape")
            # The presenter popup: notes, a mirrored slide, and keys that drive the deck.
            async with page.context.expect_page() as info:
                await page.keyboard.press("p")
            pop = await info.value
            await pop.wait_for_load_state()
            text = await pop.evaluate("document.getElementById('p-notes').textContent")
            assert text == notes[frames[3].slide_id]
            assert await pop.evaluate(
                "!!document.querySelector('#p-cur .dd-mini').shadowRoot.querySelector('.s')"
            )
            await pop.keyboard.press("Home")
            assert (await _state(page))[0] == 0
            assert (
                await pop.evaluate("document.getElementById('p-notes').textContent")
                == (notes[frames[0].slide_id])
            )
            await page.wait_for_timeout(300)
            assert seen == []  # zero requests, popup included
            await browser.close()

    asyncio.run(run())


@pytest.mark.parametrize("engine", ENGINES)
def test_deep_link_opens_that_slide(engine: str, tmp_path: Path) -> None:
    frames, _ = _deck()
    path = tmp_path / "deck.html"
    path.write_text(assemble(THEME, frames, "Deck"))

    async def run() -> None:
        async with async_playwright() as pw:
            browser = await getattr(pw, engine).launch()
            ctx = await browser.new_context()
            page = await ctx.new_page()
            await page.goto(f"file://{path}#3")
            assert (await _state(page))[0] == 2
            await browser.close()

    asyncio.run(run())


def test_send_flavour_and_pdf_carry_no_notes(tmp_path: Path) -> None:
    frames, notes = _deck()
    present = assemble(THEME, frames, "Deck", flavour="present", notes=notes)
    send = assemble(THEME, frames, "Deck", flavour="send")
    assert SECRET in present and 'id="dd-notes"' in present
    assert SECRET not in send and 'id="dd-notes"' not in send
    data = asyncio.run(pdf.render(send))
    pages = len(re.findall(rb"/Type\s*/Page[^s]", data))
    assert pages == len(frames)
    assert SECRET.encode() not in data


def test_notes_cannot_close_their_script_element() -> None:
    frames, _ = _deck()
    html = assemble(
        THEME, frames, "Deck", flavour="present", notes={frames[0].slide_id: "</script><b>x"}
    )
    block = html.split('id="dd-notes">', 1)[1].split("</script>", 1)[0]
    assert json.loads(block) == {frames[0].slide_id: "</script><b>x"}


def test_ai_markers_are_in_every_export() -> None:
    frames, _ = _deck()
    flavours: tuple[Flavour, ...] = ("present", "send")
    for flavour in flavours:
        html = assemble(THEME, frames, "Deck", flavour=flavour)
        assert '<meta name="ai-generated" content="true">' in html
        assert "trainedAlgorithmicMedia" in html
        assert "Made with AI" in html
