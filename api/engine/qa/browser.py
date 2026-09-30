"""Render slides in Chromium, measure them, screenshot them.

Layer 3 of the security model lives here: every request the page makes is
aborted except the document itself and ``data:``, and the document's CSP
allows no script. Our measure script is injected from outside the page.
"""

from __future__ import annotations

from pathlib import Path

from playwright.async_api import Route, async_playwright
from pydantic import BaseModel, Field, TypeAdapter

from engine.compose.document import Frame, qa_document
from engine.design.theme import Theme
from engine.models import Defect

_MEASURE = (Path(__file__).parent / "measure.js").read_text()


class _Found(BaseModel):
    code: str
    field: str | None = None
    measured: str
    threshold: str


class Measured(BaseModel):
    measured: bool
    errors: list[_Found] = Field(default_factory=list)
    fingerprint: str = ""
    centred: bool = False

    def defects(self) -> list[Defect]:
        return [
            Defect(code=e.code, field=e.field, measured=e.measured, threshold=e.threshold)
            for e in self.errors
        ]


_RESULT = TypeAdapter(dict[str, Measured])


def _rgb(hex_color: str) -> str:
    value = hex_color.lstrip("#")
    r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgb({r}, {g}, {b})"


async def _abort(route: Route) -> None:
    if route.request.url.startswith(("file:", "data:")):
        await route.continue_()
    else:
        await route.abort()


async def measure(
    theme: Theme,
    frames: list[Frame],
    fields: dict[str, dict[str, str]],
    work_file: str,
    shots_dir: str | None = None,
) -> dict[str, Measured]:
    """Measure every frame. With ``shots_dir``, also write ``<slide_id>.png``.

    A slide missing from the result, or one the script could not read, comes
    back ``measured=False``: a failure to measure is an error, never a pass.
    """
    with open(work_file, "w") as out:  # noqa: ASYNC230 - one small local write
        out.write(qa_document(theme, frames))
    arg = {
        "slides": fields,
        "theme": {
            "colors": [_rgb(c) for c in theme.colors.values()],
            "families": [face.family for face in theme.faces],
            "sizes": list(theme.scale.values()),
        },
    }
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.route("**/*", _abort)
        await page.goto("file://" + work_file)
        await page.evaluate("document.fonts.ready")
        raw = await page.evaluate(_MEASURE, arg)
        if shots_dir is not None:
            hosts = page.locator(".dd-slide")
            for index in range(await hosts.count()):
                host = hosts.nth(index)
                slide_id = await host.get_attribute("data-slide")
                await host.screenshot(path=f"{shots_dir}/{slide_id}.png")
        await browser.close()
    result = _RESULT.validate_python(raw)
    for frame in frames:
        result.setdefault(frame.slide_id, Measured(measured=False))
    return result
