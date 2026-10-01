"""The hostile-slide suite (phase 22 -> Verify).

Every payload is first proven to run on a bare page — no sanitizer, no lint, no
CSP — so a passing test cannot be a payload that was dead anyway. Then the same
payload goes through our path and must do nothing: no script, no request, no
navigation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import Browser, Page, Route, async_playwright
from playwright.async_api import Error as PlaywrightError

from engine.compose.document import Frame, export_document, qa_document
from engine.design.theme import THEMES
from engine.qa.lint import lint
from engine.qa.sanitize import sanitize
from lib.result import Ok

EVIL = "http://evil.test"
THEME = next(iter(THEMES.values()))
TEXT = '<p class="t" data-field="body">A slide.</p>'

HTML = {
    "script": "<script>window.__pwn=1</script>",
    "handler": '<img src="x" onerror="window.__pwn=1">',
    "svg-onload": '<svg onload="window.__pwn=1"></svg>',
    "style-attr-url": f'<div style="background-image:url({EVIL}/style-attr)">x</div>',
    "style-import": f"<style>@import url({EVIL}/import.css);</style>",
    "link-stylesheet": f'<link rel="stylesheet" href="{EVIL}/link.css">',
    "iframe": f'<iframe src="{EVIL}/frame"></iframe>',
    "object": f'<object data="{EVIL}/object"></object>',
    "img": f'<img src="{EVIL}/img">',
    "meta-refresh": f'<meta http-equiv="refresh" content="0;url={EVIL}/refresh">',
    "anchor-js": '<a class="cover" href="javascript:window.__pwn=1">go</a>',
    "anchor-out": f'<a class="cover" href="{EVIL}/link">go</a>',
}
# Anchors run only when clicked; this makes the whole slide the target.
_COVER = ".cover{position:fixed;inset:0;display:block}"

CSS = {
    "url": f".s{{background-image:url({EVIL}/css-url)}}",
    "import": f"@import url({EVIL}/css-import.css);",
    "font-face": f"@font-face{{font-family:x;src:url({EVIL}/font)}}.t{{font-family:x}}",
    "image-set": f".s{{background-image:image-set('{EVIL}/set' 1x)}}",
    # Closing the style element from inside CSS turns the rest into live HTML.
    "breakout-script": ".t{color:var(--c-ink)}</style><script>window.__pwn=1</script><style>",
    "breakout-img": f'.t{{color:var(--c-ink)}}</style><img src="{EVIL}/breakout"><style>',
    "breakout-refresh": (
        f'.t{{color:var(--c-ink)}}</style><meta http-equiv="refresh" '
        f'content="0;url={EVIL}/breakout-refresh"><style>'
    ),
    "breakout-anchor": (
        f'.t{{color:var(--c-ink)}}</style><a href="{EVIL}/breakout-link" '
        'style="position:fixed;inset:0;display:block;z-index:9">x</a><style>'
    ),
}


@dataclass
class Effect:
    requests: list[str] = field(default_factory=list)
    ran: bool = False

    @property
    def any(self) -> bool:
        return self.ran or bool(self.requests)


async def _observe(browser: Browser, load: str, *, file: bool) -> Effect:
    """Open a page, click it, and record what it did."""
    effect = Effect()
    page: Page = await browser.new_page(viewport={"width": 1920, "height": 1080})

    async def route(r: Route) -> None:
        url = r.request.url
        if url.startswith(("file:", "data:", "about:")):
            await r.continue_()
        else:
            effect.requests.append(url)
            await r.abort()

    await page.route("**/*", route)
    if file:
        await page.goto(load)
    else:
        await page.set_content(load)
    await page.wait_for_timeout(150)
    try:
        await page.mouse.click(960, 540)
        await page.wait_for_timeout(150)
        effect.ran = bool(await page.evaluate("() => window.__pwn === 1"))
    except PlaywrightError:  # a navigation away destroys the context
        effect.ran = effect.ran or bool(effect.requests)
    await page.close()
    return effect


def _bare(html: str, css: str) -> str:
    return (
        f"<!doctype html><html><head><style>{css}</style><style>{_COVER}</style></head>"
        f'<body><section class="s">{TEXT}{html}</section></body></html>'
    )


async def _ours(browser: Browser, tmp: Path, name: str, html: str, css: str) -> list[str]:
    """Render through both our documents; return what went wrong."""
    frame = Frame(name, html, css)
    problems: list[str] = []
    for kind, doc in (
        ("qa", qa_document(THEME, [frame])),
        ("export", export_document(THEME, [frame], name)),
    ):
        path = tmp / f"{name}-{kind}.html"
        path.write_text(doc)
        effect = await _observe(browser, "file://" + str(path), file=True)
        if effect.any:
            problems.append(f"{kind}: ran={effect.ran} requests={effect.requests}")
    return problems


def test_hostile_html_is_proven_live_then_dead(tmp_path: Path) -> None:
    async def run() -> dict[str, str]:
        failures: dict[str, str] = {}
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for name, payload in HTML.items():
                live = await _observe(browser, _bare(payload, ""), file=False)
                if not live.any:
                    failures[name] = "payload does nothing even unsandboxed"
                    continue
                slide = f'<section class="s">{TEXT}{payload}</section>'
                clean = sanitize(slide, frozenset({"body"}))
                if not isinstance(clean, Ok):
                    continue  # refused outright
                found = await _ours(browser, tmp_path, name, clean.value, "")
                if found:
                    failures[name] = "; ".join(found)
            await browser.close()
        return failures

    assert asyncio.run(run()) == {}


def test_hostile_css_is_proven_live_then_refused_and_inert(tmp_path: Path) -> None:
    async def run() -> dict[str, str]:
        failures: dict[str, str] = {}
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            for name, payload in CSS.items():
                live = await _observe(browser, _bare("", payload), file=False)
                if not live.any:
                    failures[name] = "payload does nothing even unsandboxed"
                    continue
                if not lint(payload):
                    failures[name] = "lint passed it"
                # Defence in depth: even CSS that skipped the lint stays inert.
                slide = f'<section class="s">{TEXT}</section>'
                found = await _ours(browser, tmp_path, name, slide, payload)
                if found:
                    failures[name] = "; ".join(found)
            await browser.close()
        return failures

    assert asyncio.run(run()) == {}
