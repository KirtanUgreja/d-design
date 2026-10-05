"""The offline test: the exported file, opened for real (phase 22 -> Verify).

Ported from v3's ``render/tests/offline.test.ts``. A CSP string in the markup
proves nothing: a font or image that was never inlined still leaves the line in
place while the page fetches from the network. This opens the export from
``file://`` with every slide shown and fails on any request that leaves it.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

from playwright.async_api import Route, async_playwright

from engine.compose.document import Frame
from engine.compose.exemplars import load_all
from engine.design.theme import THEMES
from engine.export.assemble import assemble


def _keep_only(url: str, left: list[str]) -> Callable[[Route], Awaitable[None]]:
    """Let the file itself and data: through; record and abort anything else."""

    async def route(r: Route) -> None:
        if r.request.url.split("#")[0] == url or r.request.url.startswith("data:"):
            await r.continue_()
        else:
            left.append(r.request.url)
            await r.abort()

    return route


def test_export_makes_zero_requests(tmp_path: Path) -> None:
    frames = [Frame(e.id, e.html, e.css) for e in load_all()]

    async def run() -> dict[str, list[str]]:
        leaks: dict[str, list[str]] = {}
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for theme in THEMES.values():
                path = tmp_path / f"{theme.id}.html"
                path.write_text(assemble(theme, frames, theme.id))
                url = "file://" + str(path)
                page = await browser.new_page(viewport={"width": 1920, "height": 1080})
                left: list[str] = []

                await page.route("**/*", _keep_only(url, left))
                await page.goto(url)
                # Print shows every slide at once, so every font and texture is used.
                await page.emulate_media(media="print")
                await page.evaluate("document.fonts.ready")
                await page.emulate_media(media="screen")
                for _ in frames:
                    await page.keyboard.press("ArrowRight")
                if left:
                    leaks[theme.id] = left
                await page.close()
            await browser.close()
        return leaks

    assert asyncio.run(run()) == {}
