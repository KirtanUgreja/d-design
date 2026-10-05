"""Where each slide's composition should land: a point in the continuous
descriptor space, drawn where the archive has made least (docs/v4/plan/
36-independent-design.md -> Make, 3). Replaces the ten archetype names.

Code decides where to explore; the model designs there. The target reaches
the prompt as concrete geometry, never as "be different".
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from engine.compose.archive import Archive
from engine.qa.descriptors import NAMES

CANDIDATES = 64
# What a slide's job needs from its composition: (low, high) per descriptor.
# These are content constraints, not layouts — every value between is open.
_FREE = {"blocks": (0.0, 0.35)}
_NEEDS: dict[str, dict[str, tuple[float, float]]] = {
    "cover": _FREE | {"hero": (0.45, 1.0)},
    "ask": _FREE | {"hero": (0.35, 1.0)},
    "statement": _FREE | {"hero": (0.3, 0.9)},
    "question": _FREE | {"hero": (0.4, 1.0)},
    "section": _FREE | {"hero": (0.5, 1.0)},
    "quote": {"hero": (0.25, 0.7), "blocks": (0.0, 0.35)},
    "number": {"hero": (0.6, 1.0), "blocks": (0.1, 0.5)},
    "chart": {"field": (0.25, 0.6), "hero": (0.2, 0.6), "blocks": (0.2, 0.6)},
    "image-led": {"field": (0.35, 0.8)},
}
_DENSE = {"hero": (0.15, 0.6), "blocks": (0.35, 1.0), "empty": (0.05, 0.35)}
_DEFAULT = {"hero": (0.15, 0.75)}
_OPEN = {
    "mass_x": (0.2, 0.8),
    "mass_y": (0.25, 0.75),
    "empty": (0.1, 0.55),
    "hero": (0.1, 1.0),
    "blocks": (0.1, 0.8),
    "axis": (0.1, 0.9),
    "edge": (0.0, 0.5),
    "field": (0.0, 0.45),
}
DENSE_INTENTS = frozenset({"points", "number-set", "comparison", "steps", "timeline", "team"})


@dataclass(frozen=True)
class Target:
    point: dict[str, float]  # the descriptors this composition aims at

    def values(self) -> tuple[float, ...]:
        """A full descriptor tuple: unset descriptors follow from the set ones
        (the empty field sits opposite the mass)."""
        p = self.point
        derived = {"spread": 0.5, "empty_x": 1 - p["mass_x"], "empty_y": 1 - p["mass_y"]}
        derived["hero_area"] = p["hero"] * 0.6
        return tuple(p.get(n, derived.get(n, 0.5)) for n in NAMES)


def ranges(intent: str, fields: int) -> dict[str, tuple[float, float]]:
    needs = _DENSE if intent in DENSE_INTENTS else _NEEDS.get(intent, _DEFAULT)
    out = _OPEN | needs
    lo, hi = out["blocks"]
    # a slide holds at least one block per field
    out["blocks"] = (max(lo, min(fields / 12, 0.9)), max(hi, min(fields / 12, 0.9) + 0.1))
    return out


def draw(
    rng: random.Random,
    archive: Archive,
    intent: str,
    fields: int,
    previous: Target | None = None,
) -> Target:
    """The least-explored candidate that fits the slide's job and moves away
    from the previous slide."""
    bounds = ranges(intent, fields)
    keys = ("mass_x", "mass_y", "empty", "hero", "field")

    def score(t: Target) -> float:
        crowd = math.log1p(archive.density(t.values()))
        near = 0.0
        if previous is not None:
            gap = math.dist([t.point[k] for k in keys], [previous.point[k] for k in keys])
            near = max(0.0, 0.45 - gap) * 4
        return crowd + near + rng.random() * 0.05

    candidates = [
        Target({k: round(rng.uniform(lo, hi), 3) for k, (lo, hi) in bounds.items()})
        for _ in range(CANDIDATES)
    ]
    return min(candidates, key=score)


def _third(v: float, words: tuple[str, str, str]) -> str:
    return words[min(2, int(v * 3))]


def brief(t: Target) -> str:
    """The target as geometry a designer can act on."""
    p = t.point
    side = _third(p["mass_x"], ("left", "centre", "right"))
    height = _third(p["mass_y"], ("upper", "middle", "lower"))
    away = {"left": "right", "right": "left", "centre": "one side"}[side]
    ratio = 16 ** p["hero"]
    blocks = max(1, round(p["blocks"] * 12))
    lines = [
        f"- Visual mass in the {height} {side} of the canvas.",
        f"- About {p['empty']:.0%} of the canvas empty, as one open field toward the {away}.",
        f"- The largest type about {ratio:.0f}x the smallest.",
        f"- About {blocks} distinct block{'s' if blocks > 1 else ''}.",
    ]
    if p["axis"] < 0.38:
        lines.append("- Content set in a tall, narrow column.")
    elif p["axis"] > 0.62:
        lines.append("- Content spread as a wide, shallow band.")
    if p["field"] > 0.25:
        lines.append(f"- Colour fields (or the chart) cover about {p['field']:.0%} of the canvas.")
    elif p["field"] < 0.06:
        lines.append("- No colour fields: type on the ground.")
    if p["edge"] > 0.25:
        lines.append("- A field or the type is cropped by, or bleeds off, a canvas edge.")
    elif p["edge"] < 0.05:
        lines.append("- Nothing touches the canvas edge.")
    return "\n".join(lines)


def honoured(t: Target, measured: tuple[float, ...], tolerance: float = 0.2) -> float:
    """Share of the target's descriptors the measured slide landed within tolerance of."""
    named = dict(zip(NAMES, measured, strict=True))
    hits = [abs(named[k] - v) <= tolerance for k, v in t.point.items()]
    return sum(hits) / len(hits)
