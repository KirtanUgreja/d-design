"""Visuals: a picture of the product's world, drawn by our code as SVG in the
deck's tokens (owner, 2026-10-09: "don't limit it to simple shapes").

The storyline names a kind and up to four short lines; the model that writes
slides only places an empty ``<dd-visual>`` box, and this code draws into it
after sanitizing, as charts are drawn. Five kinds:

- **waveform**: a voice, a sound, a call;
- **phone** and **browser**: an app's screen, its lines as the screen's rows;
- **chat**: a conversation, its lines as alternating messages;
- **flow**: steps or a pipeline, its lines as connected nodes.

Colour comes only from theme roles (--c-accent, --c-ink, --c-surface, …), so
a brand colour or a recolour carries through. Flat fills and strokes only: no
gradient, blur, glow or icon (AGENTS.md, rule 7).
"""

from __future__ import annotations

import hashlib
import html
import random
import re

from engine.models import VisualSpec

FONT = 34
ACCENT = "var(--c-accent)"
ON_ACCENT = "var(--c-on-accent)"
INK = "var(--c-ink)"
QUIET = "var(--c-ink-2)"
SURFACE = "var(--c-surface)"
GROUND = "var(--c-ground)"
RULE = "var(--c-rule)"
LINE = "calc(var(--rule) * 2)"


def _rng(spec: VisualSpec) -> random.Random:
    seed = hashlib.sha256(f"{spec.kind}/{'|'.join(spec.lines)}".encode()).hexdigest()
    return random.Random(int(seed[:12], 16))  # noqa: S311 - a drawing, not a secret


def _text(
    x: float,
    y: float,
    words: str,
    *,
    fill: str = INK,
    size: float = FONT,
    anchor: str = "start",
    weight: str = "regular",
    face: str = "text",
) -> str:
    return (
        f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="{anchor}" style="font-family:var(--f-{face});'
        f'font-size:{size:.0f}px;font-weight:var(--w-{weight});fill:{fill}">{html.escape(words)}</text>'
    )


def _rect(x: float, y: float, w: float, h: float, fill: str, r: float = 0, stroke: str = "") -> str:
    edge = f";stroke:{stroke};stroke-width:{LINE}" if stroke else ""
    return (
        f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{r:.0f}" '
        f'style="fill:{fill}{edge}"/>'
    )


def _fit(words: str, width: float, size: float = FONT) -> str:
    """Cut a line to what fits ``width`` at ``size`` (about 0.52em a glyph)."""
    room = max(4, int(width / (size * 0.52)))
    return words if len(words) <= room else words[: room - 1].rstrip() + "…"


def _waveform(spec: VisualSpec) -> tuple[str, int, int]:
    """A voice: mirrored bars around a centre line, louder in the middle."""
    rng = _rng(spec)
    w, h, bars = 1200, 640, 46
    pitch = w / bars
    thick = pitch * 0.56
    out = []
    for i in range(bars):
        swell = 0.35 + 0.65 * (1 - abs(i - bars / 2) / (bars / 2)) ** 1.4
        amp = (h / 2 - 20) * swell * rng.uniform(0.35, 1.0)
        x = i * pitch + (pitch - thick) / 2
        tone = INK if rng.random() < 0.18 else ACCENT
        out.append(_rect(x, h / 2 - amp, thick, amp * 2, tone, thick / 2))
    out.append(f'<rect x="0" y="{h / 2 - 1:.0f}" width="{w}" height="2" style="fill:{RULE}"/>')
    return "".join(out), w, h


def _rows(lines: list[str], x: float, y: float, width: float, pitch: float) -> list[str]:
    """An app screen's list: a marker block and a label per line."""
    out = []
    for i, words in enumerate(lines):
        top = y + i * pitch
        out.append(_rect(x, top, width, pitch - 18, SURFACE, 14))
        mark = ACCENT if i == 0 else RULE
        out.append(_rect(x + 22, top + (pitch - 18) / 2 - 20, 40, 40, mark, 10))
        size = FONT * 1.25
        label = _fit(words, width - 120, size)
        out.append(_text(x + 86, top + (pitch - 18) / 2 + size * 0.35, label, size=size))
    return out


def _phone(spec: VisualSpec) -> tuple[str, int, int]:
    """An app on a phone: its title bar in the accent, its lines as rows."""
    w, h = 620, 1000
    lines = spec.lines or ["", "", ""]
    out = [
        _rect(6, 6, w - 12, h - 12, GROUND, 72, stroke=INK),
        _rect(w / 2 - 70, 34, 140, 26, INK, 13),  # the speaker
        _rect(44, 100, w - 88, 190, ACCENT, 22),
        _rect(80, 150, 220, 26, ON_ACCENT, 13),
        _rect(80, 200, 320, 18, ON_ACCENT, 9),
        *_rows(lines[:4], 44, 330, w - 88, 128),
        _rect(44, h - 150, w - 88, 92, INK, 46),
    ]
    return "".join(out), w, h


def _browser(spec: VisualSpec) -> tuple[str, int, int]:
    """A web app in a window: an address bar, a hero block, its lines as rows."""
    w, h = 1280, 820
    lines = spec.lines or ["", "", ""]
    dots = "".join(
        f'<circle cx="{48 + i * 40}" cy="46" r="11" style="fill:{RULE}"/>' for i in range(3)
    )
    out = [
        _rect(4, 4, w - 8, h - 8, GROUND, 24, stroke=INK),
        f'<rect x="4" y="90" width="{w - 8}" height="2" style="fill:{INK}"/>',
        dots,
        _rect(180, 26, w - 360, 40, SURFACE, 20),
        _rect(48, 130, 330, h - 178, ACCENT, 18),
        _rect(84, 180, 200, 30, ON_ACCENT, 15),
        _rect(84, 236, 240, 20, ON_ACCENT, 10),
        _rect(84, 274, 170, 20, ON_ACCENT, 10),
        *_rows(lines[:4], 418, 130, w - 466, 150),
    ]
    return "".join(out), w, h


def _chat(spec: VisualSpec) -> tuple[str, int, int]:
    """A conversation: the user's lines on the right in the accent, replies left."""
    w = 1200
    lines = (spec.lines or ["", ""])[:4]
    out, y = [], 0.0
    for i, words in enumerate(lines):
        mine = i % 2 == 0
        size = FONT * 1.35
        text = _fit(words, w * 0.66, size)
        bw = min(w * 0.8, len(text) * size * 0.52 + 110)
        bh = size * 2.4
        x = w - bw if mine else 0
        out.append(_rect(x, y, bw, bh, ACCENT if mine else SURFACE, bh / 2))
        tone = ON_ACCENT if mine else INK
        out.append(_text(x + 55, y + bh / 2 + size * 0.35, text, fill=tone, size=size))
        y += bh + 36
    return "".join(out), w, max(int(y - 36), 1)


def _flow(spec: VisualSpec) -> tuple[str, int, int]:
    """Steps: nodes in a row joined by arrows; the last node in the accent."""
    lines = (spec.lines or ["", "", ""])[:4]
    n = len(lines)
    w, h = 1400, 420
    gap = 90
    node = (w - gap * (n - 1)) / n
    out = []
    for i, words in enumerate(lines):
        x = i * (node + gap)
        last = i == n - 1
        out.append(
            _rect(x, 60, node, h - 120, ACCENT if last else GROUND, 22, stroke="" if last else INK)
        )
        out.append(
            _text(
                x + 32,
                60 + 64,
                f"{i + 1:02d}",
                fill=ON_ACCENT if last else QUIET,
                size=FONT * 0.8,
                face="label",
            )
        )
        label = _fit(words, node - 64, FONT * 1.5)
        out.append(
            _text(
                x + 32,
                h - 60 - 44,
                label,
                fill=ON_ACCENT if last else INK,
                size=FONT * 1.5,
                weight="bold",
            )
        )
        if not last:
            ax, ay = x + node + 14, h / 2
            out.append(
                f'<rect x="{ax:.0f}" y="{ay - 2:.0f}" width="{gap - 40}" height="4" '
                f'style="fill:{INK}"/>'
            )
            out.append(
                f'<polygon points="{ax + gap - 40:.0f},{ay - 14:.0f} {ax + gap - 22:.0f},'
                f'{ay:.0f} {ax + gap - 40:.0f},{ay + 14:.0f}" style="fill:{INK}"/>'
            )
    return "".join(out), w, h


_DRAW = {
    "waveform": _waveform,
    "phone": _phone,
    "browser": _browser,
    "chat": _chat,
    "flow": _flow,
}


def describe(spec: VisualSpec) -> str:
    """The visual as text, for screen readers."""
    what = {
        "waveform": "A voice waveform",
        "phone": "An app on a phone",
        "browser": "A web app in a browser",
        "chat": "A conversation",
        "flow": "Steps in order",
    }[spec.kind]
    return what + (": " + "; ".join(spec.lines) if spec.lines else "")


def svg(spec: VisualSpec) -> str:
    body, w, h = _DRAW[spec.kind](spec)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" '
        f'height="100%" preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="{html.escape(describe(spec))}">{body}</svg>'
    )


_PLACEHOLDER = re.compile(r"(<dd-visual\b[^>]*>)\s*(</dd-visual>)")


def fill(slide_html: str, spec: VisualSpec | None) -> str:
    """Draw the visual into the slide's first <dd-visual>. Called after sanitizing."""
    if spec is None:
        return slide_html
    return _PLACEHOLDER.sub(lambda m: m.group(1) + svg(spec) + m.group(2), slide_html, count=1)


def strip(slide_html: str) -> str:
    """No visual planned: an empty box the model left behind is removed."""
    return _PLACEHOLDER.sub("", slide_html)
