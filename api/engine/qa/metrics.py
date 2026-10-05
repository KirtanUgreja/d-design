"""Thresholds over what measure.js and pixels.js report (docs/v4/design-engine.md
-> QA metrics). Errors trigger repair; warnings are reported and tracked, and
become errors only when the bench shows they track the owner's scores.
"""

from __future__ import annotations

from pydantic import BaseModel

W, H = 1920, 1080
AREA = W * H
GRID_X, GRID_Y = 48, 27  # 40px cells for the empty-rectangle search


class Box(BaseModel):
    field: str
    l: float  # noqa: E741 - left
    t: float
    r: float
    b: float
    color: list[int]
    size: float
    lines: int
    chars: int
    contrast: float


class Shape(BaseModel):
    """A colour field, texture, chart or image: geometry only, no content."""

    kind: str
    l: float  # noqa: E741 - left
    t: float
    r: float
    b: float


class Pixel(BaseModel):
    field: str
    wcag: float
    apca: float


class Found(BaseModel):
    code: str
    field: str | None = None
    measured: str
    threshold: str


def pixel_errors(pixels: list[Pixel], boxes: list[Box]) -> list[Found]:
    """E5 on the real background: WCAG below 4.5 (3 at 64px and up), APCA
    below 60 (45 at 64px and up), over the worst 10% of pixels."""
    size = {b.field: b.size for b in boxes}
    out: list[Found] = []
    for p in pixels:
        large = size.get(p.field, 0) >= 64
        need_w, need_a = (3.0, 45.0) if large else (4.5, 60.0)
        if p.wcag < need_w or p.apca < need_a:
            out.append(
                Found(
                    code="E5",
                    field=p.field,
                    measured=f"pixels: {p.wcag:.2f}:1, Lc {p.apca:.0f}",
                    threshold=f"{need_w}:1, Lc {need_a:.0f}",
                )
            )
    return out


Rect = tuple[float, float, float, float]  # left, top, right, bottom


def empty_rect(rects: list[Rect]) -> tuple[float, float, float]:
    """The largest empty rectangle: its share of the slide and its centre as
    fractions of the width and height (histogram method, 40px cells)."""
    filled = [[False] * GRID_X for _ in range(GRID_Y)]
    for left, top, right, bottom in rects:
        for y in range(max(0, int(top // 40)), min(GRID_Y, int(bottom // 40) + 1)):
            for x in range(max(0, int(left // 40)), min(GRID_X, int(right // 40) + 1)):
                filled[y][x] = True
    heights = [0] * GRID_X
    best, centre = 0, (0.5, 0.5)
    for row_index, row in enumerate(filled):
        heights = [0 if cell else h + 1 for h, cell in zip(heights, row, strict=True)]
        bars = [*heights, 0]
        stack: list[int] = []
        for i, h in enumerate(bars):
            while stack and bars[stack[-1]] >= h:
                top = stack.pop()
                start = 0 if not stack else stack[-1] + 1
                area = bars[top] * (i - start)
                if area > best:
                    best = area
                    centre = ((start + i) / 2 / GRID_X, (row_index + 1 - bars[top] / 2) / GRID_Y)
            stack.append(i)
    return best / (GRID_X * GRID_Y), centre[0], centre[1]


def _empty_share(boxes: list[Box]) -> float:
    return empty_rect([(b.l, b.t, b.r, b.b) for b in boxes])[0]


def slide_warnings(boxes: list[Box]) -> list[Found]:
    if not boxes:
        return []
    out: list[Found] = []
    area = sum((b.r - b.l) * (b.b - b.t) for b in boxes)
    coverage = area / AREA
    if coverage < 0.08 or coverage > 0.65:
        out.append(Found(code="W1", measured=f"{coverage:.0%} covered", threshold="8-65%"))
    empty = _empty_share(boxes)
    if empty > 0.5:
        out.append(Found(code="W2", measured=f"{empty:.0%} empty rectangle", threshold="50%"))
    cx = sum((b.l + b.r) / 2 * (b.r - b.l) * (b.b - b.t) for b in boxes) / max(area, 1)
    cy = sum((b.t + b.b) / 2 * (b.r - b.l) * (b.b - b.t) for b in boxes) / max(area, 1)
    offset = (((cx - W / 2) / (W / 2)) ** 2 + ((cy - H / 2) / (H / 2)) ** 2) ** 0.5 / 2**0.5
    if offset > 0.30:
        out.append(Found(code="W3", measured=f"centroid offset {offset:.2f}", threshold="0.30"))
    for b in boxes:
        per_line = b.chars / max(b.lines, 1)
        if b.size < 64 and b.lines > 1 and per_line > 75:
            out.append(
                Found(
                    code="W4",
                    field=b.field,
                    measured=f"{per_line:.0f} chars a line",
                    threshold="75",
                )
            )
        if b.size < 64 and b.contrast < 7:
            out.append(
                Found(
                    code="W6",
                    field=b.field,
                    measured=f"{b.contrast:.1f}:1",
                    threshold="7:1 for projectors",
                )
            )
    return out


def deck_warnings(fingerprints: list[str], centred: list[bool]) -> dict[int, list[Found]]:
    """W5 rhythm, across the deck: adjacent slides sharing a structure, and
    more than two centred compositions."""
    out: dict[int, list[Found]] = {}
    for i in range(1, len(fingerprints)):
        if fingerprints[i] and fingerprints[i] == fingerprints[i - 1]:
            out.setdefault(i, []).append(
                Found(
                    code="W5", measured="same structure as the previous slide", threshold="differs"
                )
            )
    centred_at = [i for i, c in enumerate(centred) if c]
    for i in centred_at[2:]:
        out.setdefault(i, []).append(
            Found(
                code="W5",
                measured=f"centred slide {centred_at.index(i) + 1}",
                threshold="at most 2 centred per deck",
            )
        )
    return out
