"""Charts: a ChartSpec drawn as hand-written SVG (docs/v4/design-engine.md ->
Components). No chart library.

The model only places an empty <dd-chart>; this code draws into it after the
slide is sanitized, so the data on a chart is exactly the approved facts.
Colours are the theme's chart tokens (--c-series-1..5), each distinct and
contrast-checked against the ground; a highlighted mark takes the first and
the rest step back. Values and labels sit on or beside the marks.
"""

from __future__ import annotations

import html
import math
import re

from engine.models import ChartSpec

W, H = 1200, 640
FONT = 26  # user units; a chart drawn about 1000px wide shows it near 22px
# A theme without chart tokens (phase 22's three) falls back to its roles.
_FALLBACK = ("var(--c-accent)", "var(--c-ink)", "var(--c-ink-2)", "var(--c-rule)", "var(--c-ink)")


def _series(n: int) -> str:
    i = n % 5
    return f"var(--c-series-{i + 1}, {_FALLBACK[i]})"


def _decimals(values: list[float]) -> int:
    """One precision per chart, so "$1.0" sits beside "$0.6", not "$1"."""
    return 0 if all(v == int(v) or abs(v) >= 100 for v in values) else 1


def label(v: float, unit: str, places: int = 1) -> str:
    """A value as the chart prints it: "$2.3M", "68%", "1,200 units"."""
    return _num(v, unit, places)


def _num(v: float, unit: str, places: int) -> str:
    text = f"{v:,.{places}f}"
    prefix = unit[:1] if unit[:1] in ("$", "€", "£") else ""
    rest = unit[len(prefix) :]
    if rest in ("%", "x") or (prefix and rest):
        return f"{prefix}{text}{rest}"
    return f"{prefix}{text} {rest}".strip()


def _t(
    x: float,
    y: float,
    text: str,
    *,
    anchor: str = "start",
    weight: str = "regular",
    fill: str = "var(--c-ink)",
    size: int = FONT,
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" style="font-family:var(--f-text);'
        f'font-size:{size}px;font-weight:var(--w-{weight});fill:{fill}">{html.escape(text)}</text>'
    )


def _color(label: str, highlight: str | None) -> str:
    """One series is one colour; a highlight takes it and the rest step back."""
    if highlight is None or label == highlight:
        return _series(0)
    return "var(--c-ink-2)"


def _bar(spec: ChartSpec) -> str:
    points = spec.series[0].points
    places = _decimals([p.value for p in points])
    top = max((p.value for p in points), default=1) or 1
    label_w, gap = 300, 18
    row = (H - gap * (len(points) - 1)) / max(len(points), 1)
    out = []
    for i, p in enumerate(points):
        y = i * (row + gap)
        w = (W - label_w - 160) * max(p.value, 0) / top
        out.append(_t(0, y + row / 2 + FONT * 0.35, p.label))
        out.append(
            f'<rect x="{label_w}" y="{y:.1f}" width="{w:.1f}" height="{row:.1f}" '
            f'style="fill:{_color(p.label, spec.highlight)}"/>'
        )
        out.append(
            _t(
                label_w + w + 14,
                y + row / 2 + FONT * 0.35,
                _num(p.value, spec.unit, places),
                weight="bold",
            )
        )
    return "".join(out)


def _column(spec: ChartSpec) -> str:
    points = spec.series[0].points
    places = _decimals([p.value for p in points])
    top = max((p.value for p in points), default=1) or 1
    base, head, gap = H - FONT * 2, FONT * 2, 28
    col = (W - gap * (len(points) - 1)) / max(len(points), 1)
    out = []
    for i, p in enumerate(points):
        x = i * (col + gap)
        h = (base - head) * max(p.value, 0) / top
        out.append(
            f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{col:.1f}" height="{h:.1f}" '
            f'style="fill:{_color(p.label, spec.highlight)}"/>'
        )
        out.append(
            _t(
                x + col / 2,
                base - h - 14,
                _num(p.value, spec.unit, places),
                anchor="middle",
                weight="bold",
            )
        )
        out.append(_t(x + col / 2, base + FONT * 1.3, p.label, anchor="middle"))
    out.append(f'<rect x="0" y="{base:.1f}" width="{W}" height="3" style="fill:var(--c-rule)"/>')
    return "".join(out)


def _line(spec: ChartSpec) -> str:
    labels = [p.label for p in spec.series[0].points]
    values = [p.value for s in spec.series for p in s.points]
    places = _decimals(values)
    lo, hi = min([*values, 0]), max(values) if values else 1
    span = (hi - lo) or 1
    left, base, head = 40, H - FONT * 2, FONT * 2
    step = (W - left * 2) / max(len(labels) - 1, 1)

    def xy(i: int, v: float) -> tuple[float, float]:
        return left + i * step, base - (base - head) * (v - lo) / span

    out = [f'<rect x="0" y="{base:.1f}" width="{W}" height="3" style="fill:var(--c-rule)"/>']
    for i, label in enumerate(labels):
        out.append(_t(xy(i, lo)[0], base + FONT * 1.3, label, anchor="middle"))
    for n, s in enumerate(spec.series):
        color = _series(n)
        pts = [xy(i, p.value) for i, p in enumerate(s.points)]
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        out.append(f'<polyline points="{path}" style="fill:none;stroke:{color};stroke-width:6"/>')
        for x, y in pts:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" style="fill:{color}"/>')
        last_x, last_y = pts[-1]
        out.append(
            _t(
                last_x,
                last_y - 22,
                _num(s.points[-1].value, spec.unit, places),
                anchor="end",
                weight="bold",
            )
        )
    return "".join(out)


def _donut(spec: ChartSpec) -> str:
    points = spec.series[0].points
    places = _decimals([p.value for p in points])
    total = sum(max(p.value, 0) for p in points) or 1
    cx, cy, r, inner = H / 2, H / 2, H / 2 - 8, H / 2 - 120
    angle = -math.pi / 2
    out = []
    for i, p in enumerate(points):
        sweep = 2 * math.pi * max(p.value, 0) / total
        a0, a1 = angle, angle + sweep
        large = 1 if sweep > math.pi else 0
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1 - 1e-6), cy + r * math.sin(a1 - 1e-6)
        x2, y2 = cx + inner * math.cos(a1 - 1e-6), cy + inner * math.sin(a1 - 1e-6)
        x3, y3 = cx + inner * math.cos(a0), cy + inner * math.sin(a0)
        out.append(
            f'<path d="M{x0:.1f},{y0:.1f} A{r:.1f},{r:.1f} 0 {large} 1 {x1:.1f},{y1:.1f} '
            f'L{x2:.1f},{y2:.1f} A{inner:.1f},{inner:.1f} 0 {large} 0 {x3:.1f},{y3:.1f}Z" '
            f'style="fill:{_series(i)}"/>'
        )
        angle = a1
        # The legend: a swatch, the label and the value, never text on a segment.
        ly = 60 + i * (FONT * 2.2)
        out.append(
            f'<rect x="{H + 40}" y="{ly - FONT * 0.8:.1f}" width="{FONT}" height="{FONT}" '
            f'style="fill:{_series(i)}"/>'
        )
        out.append(_t(H + 40 + FONT * 1.6, ly, f"{p.label}  {_num(p.value, spec.unit, places)}"))
    return "".join(out)


_DRAW = {"bar": _bar, "column": _column, "line": _line, "donut": _donut}


def svg(spec: ChartSpec) -> str:
    """The chart, sized to its box by viewBox. Its title is the slide's job."""
    body = _DRAW[spec.type](spec)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" '
        f'height="100%" preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="{html.escape(spec.title)}" style="overflow:visible">{body}</svg>'
    )


_PLACEHOLDER = re.compile(r"(<dd-chart\b[^>]*>)\s*(</dd-chart>)")


def fill(slide_html: str, spec: ChartSpec | None) -> str:
    """Draw the chart into the slide's first <dd-chart>. Called after sanitizing."""
    if spec is None:
        return slide_html
    return _PLACEHOLDER.sub(lambda m: m.group(1) + svg(spec) + m.group(2), slide_html, count=1)
