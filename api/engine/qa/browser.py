"""Render slides in Chromium, measure them, screenshot them.

Layer 3 of the security model lives here: every request the page makes is
aborted except the document itself and ``data:``, and the document's CSP
allows no script. Our measure script is injected from outside the page.
"""

from __future__ import annotations

import base64
from pathlib import Path

from playwright.async_api import Route, async_playwright
from pydantic import BaseModel, Field, TypeAdapter

from engine.compose.document import Frame, qa_document
from engine.design.theme import Theme
from engine.models import Defect
from engine.qa import metrics

_MEASURE = (Path(__file__).parent / "measure.js").read_text()
_PIXELS = (Path(__file__).parent / "pixels.js").read_text()
# Every field's text made transparent, so a screenshot shows only what is behind it.
_HIDE_TEXT = """() => { for (const host of document.querySelectorAll('.dd-slide')) {
  const root = host.shadowRoot; if (!root) continue;
  for (const el of root.querySelectorAll('[data-field], [data-field] *'))
    el.style.setProperty('color', 'transparent', 'important');
} }"""


class _Found(BaseModel):
    code: str
    field: str | None = None
    measured: str
    threshold: str


class Measured(BaseModel):
    measured: bool
    errors: list[_Found] = Field(default_factory=list)
    warnings: list[_Found] = Field(default_factory=list)
    fingerprint: str = ""
    centred: bool = False
    boxes: list[metrics.Box] = Field(default_factory=list)

    def defects(self) -> list[Defect]:
        return [_defect(e) for e in self.errors]

    def warned(self) -> list[Defect]:
        return [_defect(e) for e in self.warnings]


def _defect(e: _Found) -> Defect:
    return Defect(code=e.code, field=e.field, measured=e.measured, threshold=e.threshold)


_RESULT = TypeAdapter(dict[str, Measured])
_PIXELS_RESULT = TypeAdapter(list[metrics.Pixel])


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
    *,
    pixels: bool = True,
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
            "display": theme.display.family,
            "leading": theme.leading,
        },
    }
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.route("**/*", _abort)
        await page.goto("file://" + work_file)
        await page.evaluate("document.fonts.ready")
        raw = await page.evaluate(_MEASURE, arg)
        hosts = page.locator(".dd-slide")
        if shots_dir is not None:
            for index in range(await hosts.count()):
                host = hosts.nth(index)
                slide_id = await host.get_attribute("data-slide")
                await host.screenshot(path=f"{shots_dir}/{slide_id}.png")
        result = _RESULT.validate_python(raw)
        if pixels:
            await page.evaluate(_HIDE_TEXT)
            for index in range(await hosts.count()):
                host = hosts.nth(index)
                slide_id = str(await host.get_attribute("data-slide"))
                m = result.get(slide_id)
                if m is None or not m.measured or not m.boxes:
                    continue
                png = base64.b64encode(await host.screenshot()).decode()
                found = _PIXELS_RESULT.validate_python(
                    await page.evaluate(
                        _PIXELS, {"png": png, "boxes": [b.model_dump() for b in m.boxes]}
                    )
                )
                already = {e.field for e in m.errors if e.code == "E5"}
                m.errors += [
                    _Found(**e.model_dump())
                    for e in metrics.pixel_errors(found, m.boxes)
                    if e.field not in already
                ]
        await browser.close()
    for m in result.values():
        m.warnings += [_Found(**w.model_dump()) for w in metrics.slide_warnings(m.boxes)]
    for frame in frames:
        result.setdefault(frame.slide_id, Measured(measured=False))
    return result
