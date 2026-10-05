"""The artefact: one .html file, zero network requests
(docs/v4/spec.md -> Export; docs/v4/plan/26-player-export.md).

Two flavours. "present" carries the speaker notes as an inert JSON block for
the presenter view; "send" carries none, and the PDF is printed from it, so
a file meant to be emailed never leaks the notes.

AI disclosure: two machine-readable marks — metadata in the head (meta tags
and IPTC digitalSourceType in JSON-LD) and the SHA-256 of every export, which
the caller logs — and a visible line in the player chrome, never on a slide.
Signing the metadata needs keys and accounts: phase 29.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Literal

from engine.compose.document import Frame, font_face_css, host
from engine.design.theme import Theme

Flavour = Literal["present", "send"]

_HERE = Path(__file__).resolve().parent
PLAYER_JS = (_HERE / "player.js").read_text()
PLAYER_CSS = (_HERE / "player.css").read_text()
SOURCE_TYPE = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
DISCLOSURE = "Made with AI · d-design"

# Copied into the presenter popup by the player; inert in the deck itself.
PRESENTER_CSS = (
    "html,body{margin:0;height:100%;background:#111;color:#eee;font:16px/1.4 system-ui,"
    "sans-serif}body{display:grid;grid-template-columns:62% 1fr;grid-template-rows:auto 1fr "
    "auto;gap:16px;padding:16px;box-sizing:border-box}#p-cur{grid-row:1/3}"
    ".p-frame{position:relative;aspect-ratio:16/9;overflow:hidden;background:#000}"
    ".dd-mini{position:absolute;left:0;top:0;width:1920px;height:1080px;transform-origin:0 0}"
    "#p-notes{grid-column:2;overflow:auto;font-size:22px;line-height:1.45;white-space:pre-wrap}"
    "#p-bar{grid-column:1/3;display:flex;gap:32px;font-size:28px;font-variant-numeric:"
    "tabular-nums}#p-timer{font-weight:600}"
)


def _json_block(value: object) -> str:
    # "<" escaped so no deck text can close the script element.
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")


def assemble(
    theme: Theme,
    frames: list[Frame],
    title: str,
    *,
    flavour: Flavour = "send",
    notes: dict[str, str] | None = None,
) -> str:
    digest = base64.b64encode(hashlib.sha256(PLAYER_JS.encode()).digest()).decode()
    csp = (
        f"default-src 'none'; script-src 'sha256-{digest}'; style-src 'unsafe-inline'; "
        "img-src data:; font-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'"
    )
    meta = {
        "@context": "https://schema.org",
        "@type": "PresentationDigitalDocument",
        "name": title,
        "creator": {"@type": "SoftwareApplication", "name": "d-design"},
        "digitalSourceType": SOURCE_TYPE,
    }
    notes_block = (
        f'<script type="application/json" id="dd-notes">{_json_block(notes or {})}</script>'
        if flavour == "present"
        else ""
    )
    motion = theme.look.get("motion", "subtle")
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="generator" content="d-design"><meta name="ai-generated" content="true">'
        f'<meta name="digital-source-type" content="{SOURCE_TYPE}">'
        f'<script type="application/ld+json">{_json_block(meta)}</script>'
        f"<title>{_escape(title)}</title>"
        f'<style id="dd-theme">{font_face_css(theme)}{theme.css()}</style>'
        f"<style>{PLAYER_CSS}</style>"
        f'<style id="dd-presenter-css" media="not all">{PRESENTER_CSS}</style>'
        f'</head><body data-motion="{_escape(motion)}"><main id="dd-stage">'
        f"{''.join(host(f) for f in frames)}</main>"
        f'<footer id="dd-chrome"><span id="dd-count"></span><span>{DISCLOSURE}</span></footer>'
        f"{notes_block}<script>{PLAYER_JS}</script></body></html>"
    )


def fingerprint(html: str) -> str:
    """The export's SHA-256, logged by the caller: the second machine-readable mark."""
    return hashlib.sha256(html.encode()).hexdigest()
