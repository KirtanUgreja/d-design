"""Slide imagery (docs/v4/plan/39-design-reset.md -> Make, 5).

A reference places an empty ``<dd-image aspect="…">``; the deck's image model
draws a picture for it in the deck's one image style; this code decodes,
crops, resizes and re-encodes it, then puts it into the slot after the slide
is sanitized, as charts are. The model that writes slides never sees an image
or its bytes. A failed image leaves the slot as a quiet surface field.
"""

from __future__ import annotations

import base64
import io
import re

from PIL import Image

from engine.models import SlidePlan
from lib.result import Result, err, ok

MAX_SIDE = 1600
QUALITY = 82
MAX_PIXELS = 40_000_000  # checked before decoding: a decompression bomb is refused
FORMATS = frozenset({"PNG", "JPEG", "WEBP"})
ASPECTS: dict[str, float] = {"3:2": 1.5, "2:3": 2 / 3, "1:1": 1.0, "16:9": 16 / 9, "4:5": 0.8}
NO_TEXT = (
    "No text, no letters, no numbers, no logos, no watermarks, no user interface, no charts, "
    "no diagrams."
)

_SLOT = re.compile(r'<dd-image\b[^>]*\baspect="([^"]+)"[^>]*>\s*</dd-image>')
_EMPTY = re.compile(r"(<dd-image\b[^>]*>)\s*(</dd-image>)")
_FILLED = re.compile(r"(<dd-image\b[^>]*>)<img [^>]*>(</dd-image>)")


def aspect_of(html: str) -> str:
    """The aspect the slide's image slot asks for; 3:2 if it names none."""
    m = _SLOT.search(html)
    return m.group(1) if m and m.group(1) in ASPECTS else "3:2"


def prompt(plan: SlidePlan, style: str, accent: str, *, deck: str = "") -> str:
    """What to picture: the slide's subject, the deck's one image style and
    its accent as a mood. Words come from the user's approved fields only."""
    by = {f.name: f.text for f in plan.fields}
    subject = by.get("headline", "")
    detail = "; ".join(v for k, v in sorted(by.items()) if k.startswith("point-"))
    return (
        f"A photograph or illustration for a presentation slide. Style: {style}.\n"
        f"Subject: {subject}"
        + (f" ({detail})" if detail else "")
        + "\n"
        + (f"The presentation is about: {deck}\n" if deck else "")
        + f"Colour mood: restrained, with touches near {accent}. One clear subject, generous "
        "negative space, editorial quality, nothing generic or stock-like.\n" + NO_TEXT
    )


def treat(raw: bytes, aspect: str) -> Result[bytes, str]:
    """Decode with the pixel cap set, crop to the slot's aspect from the
    centre, fit within 1600px, and write webp with no metadata."""
    target = ASPECTS.get(aspect, 1.5)
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            if probe.format not in FORMATS:
                return err(f"not an image we accept: {probe.format}")
            if probe.width * probe.height > MAX_PIXELS:
                return err("the image is too large")
            image = probe.convert("RGB")
    except (OSError, ValueError, Image.DecompressionBombError) as e:
        return err(f"unreadable image: {type(e).__name__}")
    w, h = image.size
    if w / h > target:  # too wide: trim the sides
        cw = round(h * target)
        image = image.crop(((w - cw) // 2, 0, (w - cw) // 2 + cw, h))
    else:  # too tall: trim top and bottom
        ch = round(w / target)
        image = image.crop((0, (h - ch) // 2, w, (h - ch) // 2 + ch))
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    image.save(out, "WEBP", quality=QUALITY)  # a fresh encode carries no EXIF or XMP
    return ok(out.getvalue())


def data_url(webp: bytes) -> str:
    return "data:image/webp;base64," + base64.b64encode(webp).decode()


def fill(html: str, url: str) -> str:
    """Put the picture into the slide's first empty image slot. Called after
    sanitizing; ``url`` is always our own webp data URL."""
    if not url.startswith("data:image/webp;base64,"):
        return html
    return _EMPTY.sub(lambda m: f'{m.group(1)}<img src="{url}" alt="">{m.group(2)}', html, count=1)


def strip(html: str) -> str:
    """The slide without its picture's bytes: what a prompt may carry."""
    return _FILLED.sub(r"\1\2", html)
