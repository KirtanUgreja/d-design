"""The user's logo (docs/v4/plan/38-brand-kit.md). Every upload is hostile
until proven otherwise (docs/security/content-and-web.md -> Uploads):

- size checked before anything reads it, the format from its magic bytes,
  never its name or Content-Type;
- raster images (PNG, JPEG, WebP): dimensions checked before decode, then
  decoded and re-encoded by Pillow to a trimmed PNG, which strips metadata and
  kills polyglots;
- SVG: drawn to pixels by Chromium inside an <img> (no script runs there) on
  a page whose every request is aborted, then the same raster path. No user
  SVG ever reaches a slide, so no SVG sanitizer has to be perfect.

The logo is the one thing on a slide nobody generates: code places it in a
corner the composition left empty and picks the variant that reads on the
ground behind it. The model never sees it. ponytail: this runs in the engine
process; phase 29 moves ingest into the isolated upload worker.
"""

from __future__ import annotations

import base64
import io
from collections import Counter
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError
from playwright.async_api import Route, async_playwright

from engine.design.color import from_hex
from lib.result import Result, err, ok

MAX_BYTES = 2_000_000
MAX_SIDE = 4096  # either side, checked before decode
OUT_MAX = 1600  # the stored PNG's longest side
LOGO_CONTRAST = 3.0  # a graphic against its ground (WCAG non-text)

Image.MAX_IMAGE_PIXELS = MAX_SIDE * MAX_SIDE  # Pillow refuses a bomb before allocating


@dataclass(frozen=True)
class Logo:
    png: bytes
    width: int
    height: int
    luminance: float  # mean relative luminance of its opaque pixels
    colour: str | None  # its dominant chromatic colour: a brand-colour proposal, never applied

    def data_url(self) -> str:
        return "data:image/png;base64," + base64.b64encode(self.png).decode()


def _sniff(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if data.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    head = data[:1024].lstrip().lower()
    if head.startswith((b"<?xml", b"<svg", b"<!--")) and b"<svg" in data[:4096].lower():
        return "SVG"
    return None


def _lum(r: int, g: int, b: int) -> float:
    def lin(v: int) -> float:
        x = v / 255
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _stats(img: Image.Image) -> tuple[float, str | None]:
    """Mean luminance of the opaque pixels, and the most common chromatic colour."""
    small = img.copy()
    small.thumbnail((96, 96))
    raw = small.tobytes()  # RGBA, four bytes a pixel
    opaque = [(raw[i], raw[i + 1], raw[i + 2]) for i in range(0, len(raw), 4) if raw[i + 3] > 128]
    if not opaque:
        return 0.0, None
    luminance = sum(_lum(*p) for p in opaque) / len(opaque)
    buckets: Counter[tuple[int, int, int]] = Counter()
    for r, g, b in opaque:
        hex_ = f"#{r:02x}{g:02x}{b:02x}"
        if from_hex(hex_).c > 0.06:  # a colour, not a grey
            buckets[(r // 16 * 16 + 8, g // 16 * 16 + 8, b // 16 * 16 + 8)] += 1
    if not buckets or buckets.most_common(1)[0][1] < len(opaque) * 0.08:
        return luminance, None
    r, g, b = buckets.most_common(1)[0][0]
    return luminance, f"#{min(r, 255):02x}{min(g, 255):02x}{min(b, 255):02x}"


def _raster(data: bytes, expected: str) -> Result[Logo, str]:
    try:
        img = Image.open(io.BytesIO(data))
        if img.format != expected:
            return err(f"the file says {expected} but decodes as {img.format}")
        width, height = img.size
        if width > MAX_SIDE or height > MAX_SIDE or width < 16 or height < 16:
            return err(f"{width}x{height}px: a logo is 16 to {MAX_SIDE}px on each side")
        img.load()
        rgba = img.convert("RGBA")
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        return err("not a readable image")
    box = rgba.getchannel("A").getbbox()
    if box is None:
        return err("the image is fully transparent")
    rgba = rgba.crop(box)
    rgba.thumbnail((OUT_MAX, OUT_MAX))
    out = io.BytesIO()
    rgba.save(out, format="PNG", optimize=True)  # a fresh file: no metadata, no trailing bytes
    luminance, colour = _stats(rgba)
    return ok(Logo(out.getvalue(), rgba.width, rgba.height, luminance, colour))


_DRAW_SVG = """async ([src, most]) => {
  const img = new Image(); img.src = src;
  try { await img.decode(); } catch { return null; }
  const w = img.naturalWidth || 300, h = img.naturalHeight || 150;
  const k = Math.min(4, most / Math.max(w, h));
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(w * k)); c.height = Math.max(1, Math.round(h * k));
  c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
  return c.toDataURL('image/png');
}"""


async def _abort(route: Route) -> None:
    await route.abort()


async def _svg(data: bytes) -> Result[Logo, str]:
    src = "data:image/svg+xml;base64," + base64.b64encode(data).decode()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.route("**/*", _abort)  # nothing the SVG references is ever fetched
        await page.set_content("<!doctype html><title>logo</title>")
        drawn = await page.evaluate(_DRAW_SVG, [src, OUT_MAX])
        await browser.close()
    if not isinstance(drawn, str) or not drawn.startswith("data:image/png;base64,"):
        return err("the SVG did not draw")
    return _raster(base64.b64decode(drawn.split(",", 1)[1]), "PNG")


async def ingest(data: bytes) -> Result[Logo, str]:
    """Hostile bytes in, a clean trimmed PNG out — or the reason it was refused."""
    if len(data) > MAX_BYTES:
        return err(f"{len(data) // 1000} KB: a logo file is at most {MAX_BYTES // 1_000_000} MB")
    kind = _sniff(data)
    if kind is None:
        return err("not a PNG, JPEG, WebP or SVG file")
    if kind == "SVG":
        return await _svg(data)
    return _raster(data, kind)


def variant(logo: Logo, ground_hex: str) -> str:
    """ "original" when the logo reads on the ground as it is; else "mono":
    its shape filled with the deck's ink, which the theme guarantees reads."""
    g = _lum(*(int(ground_hex.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)))
    hi, lo = max(logo.luminance, g), min(logo.luminance, g)
    return "original" if (hi + 0.05) / (lo + 0.05) >= LOGO_CONTRAST else "mono"


Rect = tuple[float, float, float, float]
SAFE = 64  # the safe area QA enforces for text (E2), kept for the logo too
CLEAR = 32  # empty space kept around the logo


def place(occupied: list[Rect], logo: Logo, *, height: float, prefer_top: bool) -> Rect | None:
    """The first empty safe-area corner the logo fits in, in order of
    preference, or None when the composition left none (then it is not placed)."""
    w = min(360.0, height * logo.width / logo.height)
    h = w * logo.height / logo.width
    left, right = SAFE + 8, 1920 - SAFE - 8 - w
    top, bottom = SAFE - 16, 1080 - SAFE + 16 - h
    corners = [(left, top), (right, top), (left, bottom), (right, bottom)]
    if not prefer_top:
        corners = [(right, bottom), (left, bottom), (right, top), (left, top)]
    for x, y in corners:
        r = (x - CLEAR, y - CLEAR, x + w + CLEAR, y + h + CLEAR)
        if not any(r[0] < o[2] and o[0] < r[2] and r[1] < o[3] and o[1] < r[3] for o in occupied):
            return (x, y, x + w, y + h)
    return None


def element(at: Rect, tone: str) -> str:
    """The positioned element; the image itself is the theme's --logo token,
    defined once per deck, never repeated per slide."""
    x, y, r, b = at
    return (
        f'<dd-logo tone="{tone}" style="left:{x:.0f}px;top:{y:.0f}px;'
        f'width:{r - x:.0f}px;height:{b - y:.0f}px"></dd-logo>'
    )


def insert(slide_html: str, at: Rect, tone: str) -> str:
    """Into the slide's root, after everything the composition drew."""
    cut = slide_html.rfind("</section>")
    if cut < 0:
        return slide_html
    return slide_html[:cut] + element(at, tone) + slide_html[cut:]
