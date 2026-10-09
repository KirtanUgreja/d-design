"""Charts: a ChartSpec drawn as hand-written SVG (docs/v4/plan/37-beautiful-
data.md). No chart library.

The model only places an empty <dd-chart>; this code draws into it after the
slide is sanitized, so the data on a chart is exactly the approved facts. The
form follows the data's job (``form``); colour comes last and only from the
deck's validated series tokens (--c-series-N, design/dataviz.py), in a fixed
order, never cycled. One series wears slot 1; a highlight takes slot 1 and
everything else steps back to a quiet ink. Text wears text tokens, never a
series colour. Values sit on the data; a legend appears only for two or more
series. Marks take the deck's own rule weight and radius, and small choices
(bar thickness, label side) are drawn per chart from its own data, so two
decks' charts of the same numbers do not look alike.
"""

from __future__ import annotations

import hashlib
import html
import random
import re

from engine.models import ChartSpec

W, H = 1200, 640
FONT = 26  # user units; a chart drawn about 1000px wide shows it near 22px
QUIET = "var(--c-ink-2)"  # quiet text
# Context marks step back further than quiet text: labelled, so they need no 3:1.
CONTEXT = "var(--c-ink-2);fill-opacity:0.32"
RULE = "var(--c-rule)"
# A theme without chart tokens (phase 22's three) falls back to its roles.
_FALLBACK = ("var(--c-accent)", "var(--c-ink)", "var(--c-ink-2)", "var(--c-rule)", "var(--c-ink)")
_TIME = re.compile(
    r"^(?:(?:19|20)\d\d|Q[1-4]|H[12]|FY|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
    r"|Week|Month|Year)",
    re.IGNORECASE,
)


def series_colour(n: int) -> str:
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
    size: float = FONT,
    face: str = "text",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" style="font-family:var(--f-{face});'
        f'font-size:{size:.0f}px;font-weight:var(--w-{weight});fill:{fill}">{html.escape(text)}</text>'
    )


def _rect(x: float, y: float, w: float, h: float, fill: str, round_end: str = "") -> str:
    """A bar. Its data end takes the deck's radius; the baseline end stays square."""
    if w <= 0 or h <= 0:
        return ""
    if ";fill-opacity:" in fill:  # a tint over two shapes: tint the group once
        colour, alpha = fill.split(";fill-opacity:")
        return f'<g style="opacity:{alpha}">{_rect(x, y, w, h, colour, round_end)}</g>'
    box = f'x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"'
    if not round_end:
        return f'<rect {box} style="fill:{fill}"/>'
    # Both corners rounded, then the baseline half covered square: no path maths.
    rx = f"rx:min(var(--radius), {min(w, h) / 2:.1f}px)"
    if round_end == "right":
        cover = _rect(x, y, w / 2, h, fill)
    else:
        cover = _rect(x, y + h / 2, w, h / 2, fill)
    return f'<rect {box} style="fill:{fill};{rx}"/>' + cover


def _dot(x: float, y: float, r: float, fill: str) -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" style="fill:{fill}"/>'


def _baseline(y: float) -> str:
    return f'<rect x="0" y="{y:.1f}" width="{W}" height="3" style="fill:{RULE}"/>'


def _rng(spec: ChartSpec) -> random.Random:
    """Small per-chart choices, from the chart's own data: stable, never shared."""
    key = spec.title + "|" + "|".join(f"{p.label}={p.value}" for s in spec.series for p in s.points)
    return random.Random(hashlib.sha256(key.encode()).digest())  # noqa: S311 - a shape


def _fill(label_: str, spec: ChartSpec) -> str:
    """Emphasis: the highlighted item wears slot 1 and the rest step back."""
    if spec.highlight is None or label_ == spec.highlight:
        return series_colour(0)
    return CONTEXT


def annotation(spec: ChartSpec) -> str:
    """The one callout a trend earns, computed from its own values — never
    written by a model. "3.8x since 2022", "+42% since Q1"."""
    points = spec.series[0].points
    if len(points) < 3 or not _TIME.match(points[0].label):
        return ""
    first, last = points[0].value, points[-1].value
    if first <= 0 or last <= first:
        return ""
    ratio = last / first
    if ratio >= 1.5:
        return f"{ratio:.1f}x since {points[0].label}"
    return f"+{(ratio - 1) * 100:.0f}% since {points[0].label}"


def _legend(spec: ChartSpec, slots: tuple[int, ...] = (0, 1, 2, 3, 4)) -> str:
    """Only for two or more series: a swatch and a name each, in one row.
    ``slots`` maps each series to the colour slot the form drew it in."""
    if len(spec.series) < 2:
        return ""
    out, x = [], 0.0
    for n, s in enumerate(spec.series):
        out.append(_rect(x, -FONT * 1.9, FONT * 0.8, FONT * 0.8, series_colour(slots[n])))
        out.append(_t(x + FONT * 1.2, -FONT * 1.15, s.name))
        x += FONT * 1.6 + len(s.name) * FONT * 0.55 + FONT * 1.5
    return "".join(out)


def _bar(spec: ChartSpec) -> str:
    """Compare magnitudes, long names: horizontal, sorted, labelled on the bar."""
    rng = _rng(spec)
    points = sorted(spec.series[0].points, key=lambda p: -p.value)
    places = _decimals([p.value for p in points])
    top = max((p.value for p in points), default=1) or 1
    label_w = min(420, max(len(p.label) for p in points) * FONT * 0.55 + 24)
    pitch = H / max(len(points), 1)
    thick = pitch * rng.uniform(0.5, 0.78)
    out = [f'<rect x="{label_w - 3:.1f}" y="0" width="3" height="{H}" style="fill:{RULE}"/>']
    for i, p in enumerate(points):
        y = i * pitch + (pitch - thick) / 2
        w = (W - label_w - 170) * max(p.value, 0) / top
        mid = y + thick / 2 + FONT * 0.35
        out.append(_t(label_w - 20, mid, p.label, anchor="end"))
        out.append(_rect(label_w, y, w, thick, _fill(p.label, spec), "right"))
        out.append(_t(label_w + w + 14, mid, _num(p.value, spec.unit, places), weight="bold"))
    return "".join(out)


def _column(spec: ChartSpec) -> str:
    """Compare a few short-named items, or a handful of periods: vertical."""
    rng = _rng(spec)
    points = spec.series[0].points
    places = _decimals([p.value for p in points])
    top = max((p.value for p in points), default=1) or 1
    base, head = H - FONT * 2, FONT * 2.4
    pitch = W / max(len(points), 1)
    thick = pitch * rng.uniform(0.48, 0.72)
    out = []
    for i, p in enumerate(points):
        x = i * pitch + (pitch - thick) / 2
        h = (base - head) * max(p.value, 0) / top
        out.append(_rect(x, base - h, thick, h, _fill(p.label, spec), "top"))
        value = _num(p.value, spec.unit, places)
        out.append(_t(x + thick / 2, base - h - 14, value, anchor="middle", weight="bold"))
        out.append(_t(x + thick / 2, base + FONT * 1.3, p.label, anchor="middle"))
    out.append(_baseline(base))
    return "".join(out)


def _xy(spec: ChartSpec, area: bool) -> tuple[list[str], float, float, float, float]:
    labels = [p.label for p in spec.series[0].points]
    values = [p.value for s in spec.series for p in s.points]
    lo = 0.0 if area else min([*values, 0])
    hi = max(values) if values else 1
    return labels, lo, (hi - lo) or 1, H - FONT * 2, FONT * 2.4


def _positions(labels: list[str]) -> list[float]:
    """Where each label sits across the axis, 0..1. Plain years are spaced to
    scale, so 2025, 2026, 2031 does not draw five years as one; anything else
    is evenly spaced."""
    if len(labels) < 2:
        return [0.0] * len(labels)
    if all(re.fullmatch(r"(19|20)\d\d", x) for x in labels):
        years = [int(x) for x in labels]
        first, span = years[0], (years[-1] - years[0])
        if span > 0 and years == sorted(years):
            return [(y - first) / span for y in years]
    return [i / (len(labels) - 1) for i in range(len(labels))]


def _line(spec: ChartSpec, area: bool = False) -> str:
    """Change over time. The latest value is labelled at the end, and the one
    callout the data earns sits above it."""
    labels, lo, span, base, head = _xy(spec, area)
    places = _decimals([p.value for s in spec.series for p in s.points])
    left, right = 24, 200  # room on the right for end labels
    at = _positions(labels)

    def xy(i: int, v: float) -> tuple[float, float]:
        return left + (W - left - right) * at[i], base - (base - head) * (v - lo) / span

    out = [_baseline(base), _legend(spec)]
    for i, name in enumerate(labels):
        out.append(_t(xy(i, lo)[0], base + FONT * 1.3, name, anchor="middle"))
    for n, s in enumerate(spec.series):
        colour = series_colour(n)
        pts = [xy(i, p.value) for i, p in enumerate(s.points)]
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        if area and len(spec.series) == 1:
            poly = f"{pts[0][0]:.1f},{base:.1f} {path} {pts[-1][0]:.1f},{base:.1f}"
            out.append(f'<polygon points="{poly}" style="fill:{colour};fill-opacity:0.18"/>')
        out.append(
            f'<polyline points="{path}" style="fill:none;stroke:{colour};'
            'stroke-width:calc(var(--rule) * 1.6);stroke-linejoin:round;stroke-linecap:round"/>'
        )
        last_x, last_y = pts[-1]
        out.append(
            f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="10" '
            f'style="fill:{colour};stroke:var(--c-ground);stroke-width:3"/>'
        )
        value = _num(s.points[-1].value, spec.unit, places)
        out.append(_t(last_x + 22, last_y + FONT * 0.35, value, weight="bold"))
    note = annotation(spec)
    if note:
        x, y = xy(len(labels) - 1, spec.series[0].points[-1].value)
        out.append(_t(x, max(FONT, y - 40), note, anchor="end", fill=QUIET))
    return "".join(out)


def _area(spec: ChartSpec) -> str:
    return _line(spec, area=True)


def _stacked(spec: ChartSpec) -> str:
    """Part of a whole: one horizontal bar, segments in the series order with
    a ground-coloured gap between, each labelled above. Replaces the donut."""
    points = [p for p in spec.series[0].points if p.value > 0][:5]
    total = sum(p.value for p in points) or 1
    places = _decimals([p.value for p in points])
    y, thick, gap = H * 0.42, H * 0.22, 4
    out, x = [], 0.0
    for i, p in enumerate(points):
        w = W * p.value / total
        out.append(_rect(x + (gap / 2 if i else 0), y, max(w - gap, 1), thick, series_colour(i)))
        # Labels alternate above and below, so narrow parts never collide.
        above = i % 2 == 0
        ty = y - 24 if above else y + thick + FONT * 1.3
        out.append(_t(x, ty - (FONT * 1.1 if above else 0), p.label))
        value = _num(p.value, spec.unit, places)
        out.append(_t(x, ty + (0 if above else FONT * 1.1), value, weight="bold"))
        x += w
    return "".join(out)


def _pair(spec: ChartSpec) -> tuple[list[tuple[str, float, float]], int]:
    a, b = spec.series[0], spec.series[1]
    later = {p.label: p.value for p in b.points}
    rows = [(p.label, p.value, later[p.label]) for p in a.points if p.label in later]
    return rows, _decimals([v for _, x, y in rows for v in (x, y)])


def _dumbbell(spec: ChartSpec) -> str:
    """Before and after, per item: two dots joined, the change readable at a glance."""
    if len(spec.series) < 2:
        return _bar(spec)
    rows, places = _pair(spec)
    top = max(max(x, y) for _, x, y in rows) or 1
    label_w = min(420, max(len(r[0]) for r in rows) * FONT * 0.55 + 24)
    pitch = H / max(len(rows), 1)
    out = [_legend(spec, (1, 0))]  # the later value wears slot 1

    def at(v: float) -> float:
        return label_w + (W - label_w - 170) * max(v, 0) / top

    for i, (name, before, after) in enumerate(rows):
        y = i * pitch + pitch / 2
        out.append(_t(label_w - 20, y + FONT * 0.35, name, anchor="end"))
        x0, x1 = sorted((at(before), at(after)))
        out.append(_rect(x0, y - 2, x1 - x0, 4, QUIET))
        out.append(_dot(at(before), y, 11, series_colour(1)))
        out.append(_dot(at(after), y, 13, series_colour(0)))
        value = _num(after, spec.unit, places)
        out.append(_t(max(at(before), at(after)) + 26, y + FONT * 0.35, value, weight="bold"))
    return "".join(out)


def _slope(spec: ChartSpec) -> str:
    """Two moments, many items: who rose, who fell. Left and right are the two series."""
    if len(spec.series) < 2:
        return _column(spec)
    rows, places = _pair(spec)
    values = [v for _, x, y in rows for v in (x, y)]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    x0, x1, top, bottom = 360, W - 360, FONT * 2, H - FONT

    def y(v: float) -> float:
        return bottom - (bottom - top) * (v - lo) / span

    out = [
        _t(x0, FONT, spec.series[0].name, anchor="middle", fill=QUIET),
        _t(x1, FONT, spec.series[1].name, anchor="middle", fill=QUIET),
    ]
    for name, before, after in rows:
        colour = _fill(name, spec).replace("fill-opacity", "stroke-opacity")
        out.append(
            f'<line x1="{x0}" y1="{y(before):.1f}" x2="{x1}" y2="{y(after):.1f}" '
            f'style="stroke:{colour};stroke-width:calc(var(--rule) * 1.4)"/>'
        )
        left = f"{name}  {_num(before, spec.unit, places)}"
        out.append(_t(x0 - 18, y(before) + FONT * 0.35, left, anchor="end"))
        right = _num(after, spec.unit, places)
        out.append(_t(x1 + 18, y(after) + FONT * 0.35, right, weight="bold"))
    return "".join(out)


def _diverging(spec: ChartSpec) -> str:
    """Above or below a baseline: bars both ways from a zero rule, positives in
    slot 1, negatives in slot 2, every value labelled at its end."""
    points = spec.series[0].points
    places = _decimals([p.value for p in points])
    reach = max((abs(p.value) for p in points), default=1) or 1
    label_w = min(420, max(len(p.label) for p in points) * FONT * 0.55 + 24)
    zero = label_w + (W - label_w) / 2
    half = (W - label_w) / 2 - 140
    pitch = H / max(len(points), 1)
    thick = pitch * 0.6
    out = [f'<rect x="{zero - 1.5:.1f}" y="0" width="3" height="{H}" style="fill:{RULE}"/>']
    for i, p in enumerate(points):
        y = i * pitch + (pitch - thick) / 2
        w = half * abs(p.value) / reach
        mid = y + thick / 2 + FONT * 0.35
        out.append(_t(label_w - 20, mid, p.label, anchor="end"))
        value = _num(p.value, spec.unit, places)
        if p.value >= 0:
            out.append(_rect(zero, y, w, thick, series_colour(0)))
            out.append(_t(zero + w + 12, mid, value, weight="bold"))
        else:
            out.append(_rect(zero - w, y, w, thick, series_colour(1)))
            out.append(_t(zero - w - 12, mid, value, anchor="end", weight="bold"))
    return "".join(out)


def _waffle(spec: ChartSpec) -> str:
    """A share out of 100: a 10x10 grid with the share filled, and the figure
    set large beside it in the display face."""
    p = spec.series[0].points[0]
    share = max(0, min(100, round(p.value)))
    cell, gap = 52.0, 8.0
    out = []
    for i in range(100):
        row, col = divmod(i, 10)
        fill = series_colour(0) if i < share else QUIET
        x, y = col * (cell + gap), (9 - row) * (cell + gap) + 20
        tint = 1 if i < share else 0.25
        out.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" '
            f'style="fill:{fill};fill-opacity:{tint}"/>'
        )
    side = 10 * (cell + gap) + 60
    figure = _num(p.value, spec.unit or "%", 0)
    out.append(_t(side, H * 0.55, figure, size=FONT * 5, weight="display", face="display"))
    out.append(_t(side, H * 0.55 + FONT * 1.8, p.label, fill=QUIET))
    return "".join(out)


def change(a: float, b: float, unit: str) -> str:
    """The change between two values, computed, never written by a model:
    "-12 pts" for a share, "2.4x" for a big rise, "+38%" otherwise."""
    if unit == "%":
        return f"{b - a:+.0f} pts"
    if a > 0 and b / a >= 1.5:
        return f"{b / a:.1f}x"
    if a > 0:
        return f"{(b / a - 1) * 100:+.0f}%"
    return ""


def _figure(x: float, y: float, part: list[str], size: float, anchor: str, fill: str) -> str:
    """A display figure with its word unit, if any, a third of its size."""
    number, word = part
    unit = (
        f'<tspan style="font-family:var(--f-text);font-size:{size / 3:.0f}px;'
        f'font-weight:var(--w-regular)"> {html.escape(word)}</tspan>'
        if word
        else ""
    )
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" style="font-family:var(--f-display);'
        f'font-size:{size:.0f}px;font-weight:var(--w-display);fill:{fill}">'
        f"{html.escape(number)}{unit}</text>"
    )


def _pair_figures(spec: ChartSpec) -> str:
    """Two values: two figures in the display face and the change between
    them. Two bars would say less with more ink (the 2026-10-08 run)."""
    (first, second) = spec.series[0].points[:2]
    places = _decimals([first.value, second.value])
    texts = [_num(p.value, spec.unit, places) for p in (first, second)]
    # A word unit ("21.5 hours") is set at a third of the figure's size, so it
    # no longer shrinks the figure to fit (live deck, 2026-10-09).
    parts = [t.split(" ", 1) if " " in t else [t, ""] for t in texts]
    longest = max(len(n) + len(w) / 3 for n, w in parts)
    # Wide display faces run near 0.8em a figure: keep each inside 40% of the width.
    size = min(200.0, W * 0.4 / (0.8 * max(longest, 1)))
    base = 380.0
    under = base + size * 0.12 + FONT * 1.6
    mark = min(W * 0.4, size * 0.8 * longest)
    out = [
        _figure(0, base, parts[0], size, "start", QUIET),
        _t(0, under, first.label, fill=QUIET),
        _figure(W, base, parts[1], size, "end", "var(--c-ink)"),
        _t(W, under, second.label, anchor="end"),
        # The later value carries the series colour as a mark, never as text.
        _rect(W - mark, under + FONT, mark, 8, series_colour(0)),
        _t(W / 2, base - size * 0.3, "\u2192", anchor="middle", size=size * 0.45, fill=QUIET),
    ]
    delta = change(first.value, second.value, spec.unit)
    if delta:
        out.append(
            _t(
                W / 2,
                base - size * 0.3 - size * 0.45,
                delta,
                anchor="middle",
                weight="bold",
                size=FONT * 1.5,
            )
        )
    return "".join(out)


_DRAW = {
    "bar": _bar,
    "column": _column,
    "line": _line,
    "area": _area,
    "stacked": _stacked,
    "donut": _stacked,  # legacy specs: a part-of-a-whole reads better as a stack
    "dumbbell": _dumbbell,
    "slope": _slope,
    "diverging": _diverging,
    "waffle": _waffle,
    "pair": _pair_figures,
}


def form(spec: ChartSpec) -> str:
    """The form for the data's job (the dataviz method: form first, colour
    last). A spec's own type is a hint; the data decides when it is clear."""
    points = spec.series[0].points
    values = [p.value for p in points]
    timed = len(points) >= 3 and all(_TIME.match(p.label) for p in points)
    if any(v < 0 for v in values):
        return "diverging"
    if (
        len(spec.series) == 1
        and len(points) == 2
        and not (spec.unit == "%" and 97 <= sum(values) <= 103)
    ):
        return "pair"  # two values: two figures and the change, not two bars
    if len(spec.series) >= 2 and len(points) >= 2 and not timed:
        return "slope" if len(points) >= 5 else "dumbbell"
    if len(points) == 1 and spec.unit == "%" and 0 < values[0] <= 100:
        return "waffle"
    if spec.type in ("donut", "stacked") or (
        spec.unit == "%" and len(points) >= 2 and 97 <= sum(values) <= 103
    ):
        return "stacked"
    if timed:
        if len(spec.series) == 1 and len(points) <= 4:
            # A few periods: columns label every value. A thin line with only
            # its last value labelled left most of a slide empty (live, 2026-10-09).
            return "column"
        return "area" if len(spec.series) == 1 and len(points) >= 5 else "line"
    if max((len(p.label) for p in points), default=0) > 10 or len(points) > 6:
        return "bar"
    return spec.type if spec.type in ("bar", "column") else "column"


def describe(spec: ChartSpec) -> str:
    """The data as text, for screen readers and the speaker notes."""
    places = _decimals([p.value for s in spec.series for p in s.points])
    parts = []
    for s in spec.series:
        values = ", ".join(f"{p.label} {_num(p.value, spec.unit, places)}" for p in s.points)
        parts.append(f"{s.name}: {values}" if len(spec.series) > 1 else values)
    return f"{spec.title}. " + "; ".join(parts)


def svg(spec: ChartSpec) -> str:
    """The chart, sized to its box by viewBox. Its title is the slide's job."""
    body = _DRAW[form(spec)](spec)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {-FONT * 2} {W} {H + FONT * 2}" '
        f'width="100%" height="100%" preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="{html.escape(spec.title)}" style="overflow:visible">'
        f"<desc>{html.escape(describe(spec))}</desc>{body}</svg>"
    )


_PLACEHOLDER = re.compile(r"(<dd-chart\b[^>]*>)\s*(</dd-chart>)")


def fill(slide_html: str, spec: ChartSpec | None) -> str:
    """Draw the chart into the slide's first <dd-chart>. Called after sanitizing."""
    if spec is None:
        return slide_html
    return _PLACEHOLDER.sub(lambda m: m.group(1) + svg(spec) + m.group(2), slide_html, count=1)
