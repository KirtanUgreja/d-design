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


def _wrap(words: str, width: float, size: float, max_lines: int = 2) -> list[str]:
    """Words broken into at most ``max_lines`` lines that fit ``width`` at
    ``size`` (about 0.52em a glyph); only the last line is cut, and only if it
    must be (2026-10-09: "Spotify libr…" in a circle that had room for two)."""
    room = max(4, int(width / (size * 0.52)))
    lines: list[str] = []
    for word in words.split():
        if lines and len(lines[-1]) + 1 + len(word) <= room:
            lines[-1] += " " + word
        else:
            lines.append(word)
    if len(lines) > max_lines:
        lines = [*lines[: max_lines - 1], _fit(" ".join(lines[max_lines - 1 :]), width, size)]
    return lines


def _block(
    x: float,
    cy: float,
    words: str,
    width: float,
    size: float,
    lines_max: int = 2,
    **style: object,
) -> str:
    """A label of up to ``lines_max`` lines, centred on ``cy``."""
    lines = _wrap(words, width, size, lines_max)
    lead = size * 1.15
    top = cy - lead * (len(lines) - 1) / 2 + size * 0.35
    return "".join(
        _text(x, top + n * lead, line, size=size, **style)  # type: ignore[arg-type]
        for n, line in enumerate(lines)
    )


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
        size = FONT * 1.1
        out.append(_block(x + 86, top + (pitch - 18) / 2, words, width - 120, size))
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
    """Steps, top to bottom, joined by arrows; the last in the accent. A
    column, so each step's words get the full width (side by side, four
    steps were cut to "Listen…", 2026-10-09)."""
    lines = (spec.lines or ["", "", ""])[:6]
    row, gap = (150, 56) if len(lines) <= 4 else (118, 40)
    w = 1000
    size = FONT * 1.4 if len(lines) <= 4 else FONT * 1.15
    out = []
    for i, words in enumerate(lines):
        y = i * (row + gap)
        last = i == len(lines) - 1
        tone = ON_ACCENT if last else INK
        out.append(_rect(0, y, w, row, ACCENT if last else GROUND, 22, stroke="" if last else INK))
        out.append(
            _text(
                48,
                y + row / 2 + size * 0.35,
                f"{i + 1:02d}",
                fill=ON_ACCENT if last else QUIET,
                size=size,
                face="label",
            )
        )
        # Two lines before a cut ("Art direction for the whole de…", 2026-10-10).
        out.append(_block(170, y + row / 2, words, w - 220, size, fill=tone, weight="bold"))
        if not last:
            ax, ay = 100, y + row + 8
            out.append(
                f'<rect x="{ax - 2}" y="{ay:.0f}" width="4" height="{gap - 26}" '
                f'style="fill:{INK}"/>'
            )
            out.append(
                f'<polygon points="{ax - 14},{ay + gap - 30:.0f} {ax + 14},'
                f'{ay + gap - 30:.0f} {ax},{ay + gap - 14:.0f}" style="fill:{INK}"/>'
            )
    h = len(lines) * row + (len(lines) - 1) * gap
    return "".join(out), w, h


def _stack(spec: VisualSpec) -> tuple[str, int, int]:
    """A tech stack as layers, top (what the user touches) to bottom (data):
    each line "Layer: tools", the layer in the label face, the tools large
    (a project deck's tech stack slide, owner, 2026-10-09)."""
    lines = (spec.lines or ["", "", ""])[:8]
    w, gap = 1300, 18
    row = 150 if len(lines) <= 4 else 118 if len(lines) <= 6 else 96
    out = []
    for i, line in enumerate(lines):
        layer, _, tools = line.partition(":")
        if not tools:
            layer, tools = "", line
        y = i * (row + gap)
        top = i == 0
        out.append(_rect(0, y, w, row, ACCENT if top else SURFACE, 18))
        tone = ON_ACCENT if top else INK
        if layer:
            out.append(
                _text(
                    40,
                    y + row / 2 + FONT * 0.3,
                    layer.strip().upper(),
                    fill=tone,
                    size=FONT * 0.9,
                    face="label",
                )
            )
        size = FONT * (1.35 if len(lines) <= 6 else 1.1)
        out.append(
            _block(
                380 if layer else 40,
                y + row / 2,
                tools.strip(),
                w - 420,
                size,
                fill=tone,
                weight="bold",
            )
        )
    return "".join(out), w, len(lines) * (row + gap) - gap


def _hub(spec: VisualSpec) -> tuple[str, int, int]:
    """The product at the centre, its parts around it, joined by curves: the
    first line is the hub, the rest (up to five) the spokes (Orbitoshift's
    flow diagram, the owner's reference, 2026-10-09)."""
    w, h, r, bw = 1500, 900, 175, 340
    cx, cy = w / 2, h / 2
    lines = spec.lines or ["", "", "", ""]
    centre, spokes = lines[0], lines[1:6]
    left = spokes[: (len(spokes) + 1) // 2]
    right = spokes[len(left) :]
    out = []
    for side, group in ((-1, left), (1, right)):
        for k, words in enumerate(group):
            y = h * (k + 1) / (len(group) + 1)
            x = bw / 2 + 20 if side < 0 else w - bw / 2 - 20
            start = x - side * bw / 2
            end_x, end_y = cx + side * r * 0.92, cy + (y - cy) * 0.4
            mid = (start + end_x) / 2
            out.append(
                f'<path d="M{start:.0f},{y:.0f} C{mid:.0f},{y:.0f} {mid:.0f},{end_y:.0f} '
                f'{end_x:.0f},{end_y:.0f}" style="fill:none;stroke:{ACCENT};stroke-width:10;'
                'stroke-linecap:round"/>'
            )
            out.append(_rect(x - bw / 2, y - 60, bw, 120, SURFACE, 20))
            size = FONT * 1.1
            out.append(_block(x, y, words, bw - 36, size, anchor="middle"))
    out.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r + 26}" style="fill:{SURFACE}"/>')
    out.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r}" style="fill:{ACCENT}"/>')
    size = FONT * 1.2
    # Wrapped, never cut ("Python worker…" in a circle with room, 2026-10-10).
    out.append(
        _block(
            cx,
            cy,
            centre,
            r * 1.6,
            size,
            lines_max=3,
            fill=ON_ACCENT,
            anchor="middle",
            weight="bold",
        )
    )
    return "".join(out), w, h


def _pipeline(spec: VisualSpec) -> tuple[str, int, int]:
    """Input, core and output as three circles on one line; the core in the
    accent (NovaThode's architecture diagram, the owner's reference, 2026-10-09)."""
    lines = (spec.lines or ["", "", ""])[:3]
    w, h, r = 1500, 520, 190
    xs = [r + 20 + i * (w - 2 * r - 40) / max(len(lines) - 1, 1) for i in range(len(lines))]
    out = [
        f'<rect x="{xs[0]:.0f}" y="{h / 2 - 2:.0f}" width="{xs[-1] - xs[0]:.0f}" height="4" '
        f'style="fill:{RULE}"/>'
    ]
    for i, (x, words) in enumerate(zip(xs, lines, strict=True)):
        core = len(lines) == 3 and i == 1
        fill = ACCENT if core else INK if i == 0 else SURFACE
        tone = ON_ACCENT if core else GROUND if i == 0 else INK
        out.append(f'<circle cx="{x:.0f}" cy="{h / 2:.0f}" r="{r}" style="fill:{fill}"/>')
        size = FONT * 1.3
        out.append(
            _block(x, h / 2, words, r * 1.5, size, 3, fill=tone, anchor="middle", weight="bold")
        )

    return "".join(out), w, h


_DRAW = {
    "waveform": _waveform,
    "phone": _phone,
    "browser": _browser,
    "chat": _chat,
    "flow": _flow,
    "hub": _hub,
    "stack": _stack,
    "pipeline": _pipeline,
}


def describe(spec: VisualSpec) -> str:
    """The visual as text, for screen readers."""
    what = {
        "waveform": "A voice waveform",
        "phone": "An app on a phone",
        "browser": "A web app in a browser",
        "chat": "A conversation",
        "flow": "Steps in order",
        "hub": "A hub and the parts around it",
        "stack": "A tech stack, layer by layer",
        "pipeline": "Input, core and output",
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
