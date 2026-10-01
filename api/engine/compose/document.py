"""Assemble slides into one HTML document.

Each slide lives in its own Declarative Shadow DOM root, so its CSS cannot
reach the player or another slide, and nothing here rewrites a selector. Theme
tokens are inherited custom properties and fonts are document-level
``@font-face`` rules, so both reach inside. The same document shape is used for
QA, the editor and the export — what is measured is what ships.
"""

from __future__ import annotations

import base64
import hashlib
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


def _host(frame: Frame) -> str:
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
        f"</head><body>{''.join(_host(f) for f in frames)}</body></html>"
    )


_PLAYER_CSS = (
    "html,body{margin:0;height:100%;overflow:hidden;background:var(--c-ground)}"
    ".dd-slide{width:1920px;height:1080px;position:absolute;left:50%;top:50%;"
    "transform-origin:0 0;display:none}.dd-slide.on{display:block}"
    "@media print{@page{size:1920px 1080px;margin:0}html,body{overflow:visible;height:auto}"
    ".dd-slide{display:block;position:static;transform:none!important;break-after:page}}"
)
# ponytail: arrows, space, home/end, F. The full player — overview, presenter
# view, builds, deep links — is phase 26.
_PLAYER_JS = (
    "(()=>{const s=[...document.querySelectorAll('.dd-slide')];"
    "let i=Math.max(0,Math.min(s.length-1,(parseInt(location.hash.slice(1))||1)-1));"
    "const fit=()=>{const k=Math.min(innerWidth/1920,innerHeight/1080);"
    "for(const e of s)e.style.transform='scale('+k+') translate(-50%,-50%)'};"
    "const go=n=>{i=Math.max(0,Math.min(s.length-1,n));"
    "s.forEach((e,j)=>e.classList.toggle('on',j===i));history.replaceState(null,'','#'+(i+1))};"
    "addEventListener('resize',fit);addEventListener('keydown',e=>{"
    "if(['ArrowRight','PageDown',' '].includes(e.key))go(i+1);"
    "else if(['ArrowLeft','PageUp'].includes(e.key))go(i-1);"
    "else if(e.key==='Home')go(0);else if(e.key==='End')go(s.length-1);"
    "else if(e.key==='f'||e.key==='F')document.documentElement.requestFullscreen()});"
    "addEventListener('click',e=>go(i+(e.clientX<innerWidth/3?-1:1)));fit();go(i)})();"
)


def export_document(theme: Theme, frames: list[Frame], title: str) -> str:
    """The artefact: one file, zero network requests. Only our player script
    runs, allowed by its hash."""
    digest = base64.b64encode(hashlib.sha256(_PLAYER_JS.encode()).digest()).decode()
    csp = (
        f"default-src 'none'; script-src 'sha256-{digest}'; style-src 'unsafe-inline'; "
        "img-src data:; font-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'"
    )
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;")
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="generator" content="d-design"><meta name="ai-generated" content="true">'
        f"<title>{safe_title}</title>"
        f"<style>{font_face_css(theme)}{theme.css()}{_PLAYER_CSS}</style></head><body>"
        f"{''.join(_host(f) for f in frames)}<script>{_PLAYER_JS}</script></body></html>"
    )
