"""The PDF: the send flavour, printed by Chromium at 1920x1080 per page. A
print of the same bytes, never a screenshot, so the PDF and the file cannot
drift; and from "send", so the PDF never carries the notes."""

from __future__ import annotations

from playwright.async_api import Route, async_playwright


async def _offline(route: Route) -> None:
    if route.request.url.startswith(("data:", "about:")):
        await route.continue_()
    else:
        await route.abort()


async def render(send_html: str) -> bytes:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.route("**/*", _offline)
        await page.set_content(send_html, wait_until="load")
        await page.evaluate("document.fonts.ready")
        # Step reveals are a presenting effect; a page shows every step.
        await page.evaluate("window.ddPlayer && window.ddPlayer.revealAll()")
        pdf = await page.pdf(
            width="1920px", height="1080px", print_background=True, prefer_css_page_size=True
        )
        await browser.close()
        return pdf
