"""Assemble slides into one HTML document.

Each slide lives in its own Declarative Shadow DOM root, so its CSS cannot
reach the player or another slide, and nothing here rewrites a selector. Theme
tokens are inherited custom properties and fonts are document-level
``@font-face`` rules, so both reach inside. The same document shape is used for
QA, the editor and the export — what is measured is what ships.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from engine.design.theme import Theme

FONTS = Path(__file__).resolve().parent.parent.parent / "library" / "fonts"
W, H = 1920, 1080


@dataclass(frozen=True)
class Frame:
    """One slide, already sanitized and linted."""

    slide_id: str
    html: str
    css: str


def _svg(body: str, size: int) -> str:
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' "
        f"viewBox='0 0 {size} {size}'>{body}</svg>"
    )
    return f'url("data:image/svg+xml,{quote(svg)}")'


# Texture without gradients: colourless SVG tiles used as masks, the colour
# underneath always a theme token (docs/v4/design-engine.md -> Registry).
_TILES = {
    "halftone": _svg("<circle cx='12' cy='12' r='6.5'/>", 24),
    "hatch": _svg(
        "<path d='M-4 4 L4 -4 M0 20 L20 0 M16 24 L24 16' stroke='#000' stroke-width='5'/>", 20
    ),
    "grid": _svg("<path d='M0 0H40V3H0ZM0 0V40H3V0Z'/>", 40),
    # Ported from v3's texture/patterns.ts without its light-source bloom.
    "dither": _svg(
        "".join(
            f"<rect x='{x * 4}' y='{y * 4}' width='4' height='4'/>"
            for y, row in enumerate(((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5)))
            for x, t in enumerate(row)
            if t < 6
        ),
        16,
    ),
    "crosshatch": _svg("<rect width='16' height='2.5'/><rect width='2.5' height='16'/>", 16),
    "weave": _svg("<rect width='5' height='8'/><rect x='8' y='8' width='5' height='8'/>", 16),
    "lines": _svg("<rect width='24' height='3'/>", 24),
    "grain": _svg(
        "<filter id='g'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' "
        "stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 "
        "-1.6 1.1'/></filter><rect width='64' height='64' filter='url(#g)'/>",
        64,
    ),
}

# Ours, not the model's: it may use :host, masks and url(). The model's CSS is
# appended after it inside the same shadow root.
_BASE = (
    ":host{display:block;width:1920px;height:1080px;overflow:hidden;position:relative;"
    "background:var(--c-ground);color:var(--c-ink);font-family:var(--f-text);"
    "font-size:var(--t-body);font-weight:var(--w-regular);line-height:1.25;"
    "-webkit-font-smoothing:antialiased;text-rendering:geometricPrecision}"
    "*{box-sizing:border-box;margin:0;padding:0}"
    ".s{width:1920px;height:1080px;position:relative;overflow:hidden}"
    "ul,ol{list-style:none}em{font-style:normal}strong{font-weight:inherit}"
    "h1,h2,h3{text-wrap:balance}p,li{text-wrap:pretty}"
    "dd-texture{display:block;background-color:var(--c-accent)}"
    "dd-texture[tone=ink]{background-color:var(--c-ink)}"
    "dd-texture[tone=surface]{background-color:var(--c-surface)}"
    + "".join(
        f"dd-texture[kind={kind}]{{-webkit-mask-image:{tile};mask-image:{tile};"
        "-webkit-mask-repeat:repeat;mask-repeat:repeat}"
        for kind, tile in _TILES.items()
    )
)


def font_face_css(theme: Theme) -> str:
    """Every face the theme uses, embedded as-is. No subsetting: that would be
    a modification under the OFL (docs/v4/spec.md -> Export)."""
    rules: list[str] = []
    for face in theme.faces:
        for weight in face.weights:
            data = base64.b64encode((FONTS / face.folder / f"{weight}.woff2").read_bytes())
            rules.append(
                f"@font-face{{font-family:'{face.family}';font-weight:{weight};"
                f"font-style:normal;font-display:block;"
                f"src:url(data:font/woff2;base64,{data.decode()}) format('woff2')}}"
            )
    return "".join(rules)


def host(frame: Frame) -> str:
    # The lint refuses "<"; this keeps a frame that skipped it inside its
    # <style> anyway. CSS reads "<\/" as "</", and no valid rule contains it.
    css = frame.css.replace("</", "<\\/")
    return (
        f'<div class="dd-slide" data-slide="{frame.slide_id}">'
        f'<template shadowrootmode="open"><style>{_BASE}{css}</style>{frame.html}'
        "</template></div>"
    )


def qa_document(theme: Theme, frames: list[Frame]) -> str:
    """Slides stacked at true size, no script of ours, none allowed at all."""
    csp = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:"
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">'
        f"<style>{font_face_css(theme)}{theme.css()}"
        "html,body{margin:0;background:#888}.dd-slide{width:1920px;height:1080px}</style>"
        f"</head><body>{''.join(host(f) for f in frames)}</body></html>"
    )
