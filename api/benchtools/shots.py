"""Screenshot every slide of an HTML deck at 1920x1080.

All network is aborted: a baseline deck is model-written HTML, and the bench
must not fetch what it asks for.
"""

from __future__ import annotations

from playwright.async_api import Route, async_playwright

SLIDE = "section.slide"


async def _abort(route: Route) -> None:
    if route.request.url.startswith(("file:", "data:")):
        await route.continue_()
    else:
        await route.abort()


async def shoot(url: str, out_dir: str) -> int:
    """Write ``01.png``, ``02.png``... into ``out_dir``. Returns the slide count."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(
            viewport={"width": 1920, "height": 1080}, java_script_enabled=False
        )
        await page.route("**/*", _abort)
        await page.goto(url)
        slides = page.locator(SLIDE)
        count = await slides.count()
        for index in range(count):
            await slides.nth(index).screenshot(path=f"{out_dir}/{index + 1:02d}.png")
        await browser.close()
    return count
