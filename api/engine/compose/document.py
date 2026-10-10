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

from engine.design.patterns import SHAPES
from engine.design.theme import Theme
from engine.design.theme import face as registry_face

FONTS = Path(__file__).resolve().parent.parent.parent / "library" / "fonts"
W, H = 1920, 1080


@dataclass(frozen=True)
class Frame:
    """One slide, already sanitized and linted."""

    slide_id: str
    html: str
    css: str


# Texture without gradients: colourless SVG masks over a theme colour. The
# geometry is the look's own (design/patterns.py) and reaches each slide as the
# --tile-* and --mark tokens, so the slide's CSS never carries a url().
KINDS = ("halftone", "hatch", "crosshatch", "grid", "dither", "weave", "lines", "grain", "motif")


# Ours, not the model's: it may use :host, masks and url(). The model's CSS is
# appended after it inside the same shadow root.
_BASE = (
    ":host{display:block;width:1920px;height:1080px;overflow:hidden;position:relative;"
    "background:var(--c-ground);color:var(--c-ink);font-family:var(--f-text);"
    "font-size:var(--t-body);font-weight:var(--w-regular);line-height:1.25;"
    "-webkit-font-smoothing:antialiased;text-rendering:geometricPrecision;"
    # The deck's variable instance. Only a face with a wdth range, or with the
    # named axes, responds; every other face ignores them.
    "font-stretch:var(--stretch-display,100%);font-variation-settings:var(--fv-display,normal)}"
    "*{box-sizing:border-box;margin:0;padding:0}"
    ".s{width:1920px;height:1080px;position:relative;overflow:hidden}"
    "ul,ol{list-style:none}em{font-style:normal}strong{font-weight:inherit}"
    "h1,h2,h3{text-wrap:balance}p,li{text-wrap:pretty}"
    "dd-chart{display:block}"
    "dd-visual{display:block}"
    # Film grain over the whole slide (owner, 2026-10-09: the references he
    # wants are textured, never flat). Ours, offline, too faint to touch QA.
    ".s::after{content:'';position:absolute;inset:0;pointer-events:none;z-index:40;"
    "background-image:var(--grain,none);background-size:180px 180px}"
    # A soft glow the slide may place once, drawn by us: the one gradient a
    # slide carries (owner, 2026-10-09: "slight gradient, not AI slop").
    "dd-glow{display:block;pointer-events:none;background:var(--glow-accent,none)}"
    "dd-glow[tone=ink]{background:var(--glow-ink,none)}"
    "dd-glow[tone=surface]{background:var(--glow-surface,none)}"
    # Unstyled SVG would draw in browser black: the theme's ink instead, at no specificity.
    ":where(.s svg) :where(path,rect,circle,ellipse,line,polyline,polygon)"
    "{fill:var(--c-ink);stroke:none}"
    # An image slot (phase 39): a quiet surface field until our code puts the
    # deck's generated image in it, and the same field if that image fails.
    "dd-image{display:block;overflow:hidden;background-color:var(--c-surface)}"
    "dd-image>img{display:block;width:100%;height:100%;object-fit:cover}"
    # Shapes (design/patterns.py): colourless masks over a theme colour; the
    # slide's CSS sizes and places them. Diagonals and bands fill their box.
    "dd-shape{display:block;background-color:var(--c-accent);-webkit-mask-repeat:no-repeat;"
    "mask-repeat:no-repeat;-webkit-mask-position:center;mask-position:center;"
    "-webkit-mask-size:contain;mask-size:contain}"
    "dd-shape[tone=ink]{background-color:var(--c-ink)}"
    "dd-shape[tone=surface]{background-color:var(--c-surface)}"
    "dd-shape[tone=rule]{background-color:var(--c-rule)}"
    "dd-shape[kind=diagonal],dd-shape[kind=band]{-webkit-mask-size:100% 100%;mask-size:100% 100%}"
    + "".join(
        f"dd-shape[kind={k}]{{-webkit-mask-image:var(--shape-{k});mask-image:var(--shape-{k})}}"
        for k in SHAPES
    )
    # The user's logo, placed by our code (components/logo.py): never restyled,
    # only shown as it is or, where it would not read, as its shape in ink.
    + "dd-logo{position:absolute;display:block;background:var(--logo) center/contain no-repeat}"
    "dd-logo[tone=mono]{background:var(--c-ink);-webkit-mask:var(--logo) center/contain "
    "no-repeat;mask:var(--logo) center/contain no-repeat}"
    "dd-texture{display:block;background-color:var(--c-accent)}"
    "dd-texture[tone=ink]{background-color:var(--c-ink)}"
    "dd-texture[tone=surface]{background-color:var(--c-surface)}"
    + "".join(
        f"dd-texture[kind={kind}]{{-webkit-mask-image:var(--tile-{kind});"
        f"mask-image:var(--tile-{kind});-webkit-mask-repeat:repeat;mask-repeat:repeat}}"
        for kind in KINDS
    )
    + "dd-texture[kind=mark]{-webkit-mask-image:var(--mark);mask-image:var(--mark);"
    "-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;-webkit-mask-position:center;"
    "mask-position:center;-webkit-mask-size:contain;mask-size:contain}"
)


def font_face_css(theme: Theme) -> str:
    """Every face the theme uses, embedded as-is. No subsetting: that would be
    a modification under the OFL (docs/v4/spec.md -> Export)."""
    rules: list[str] = []
    for named in theme.faces:
        face = registry_face(named.family)  # the registry knows which files exist
        if face.axes:  # one variable file, declared over its ranges
            data = base64.b64encode((FONTS / face.folder / "variable.woff2").read_bytes())
            wght = face.axis("wght")
            wdth = face.axis("wdth")
            rules.append(
                f"@font-face{{font-family:'{face.family}';"
                + (f"font-weight:{wght[0]:g} {wght[1]:g};" if wght else "")
                + (f"font-stretch:{wdth[0]:g}% {wdth[1]:g}%;" if wdth else "")
                + "font-style:normal;font-display:block;"
                f"src:url(data:font/woff2;base64,{data.decode()}) format('woff2')}}"
            )
            continue
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
