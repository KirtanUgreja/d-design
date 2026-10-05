"""Every accepted slide's composition, from every deck: the memory that
refuses repeats (docs/v4/plan/36-independent-design.md -> Make, 2).

Holds descriptors and occupancy hashes only — never text, never screenshots —
so it is not customer data. A MAP-Elites grid over four descriptors measures
coverage and tells the target sampler where nothing has been made yet.

Pure: the caller loads and saves the lines. ponytail: a linear scan; at
~100k slides move to a KD-tree or an ANN index behind ``nearest``.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Iterable

from pydantic import BaseModel, Field

from engine.qa.descriptors import NAMES, Descriptors, distance

GRID_AXES = ("mass_x", "mass_y", "empty", "hero")
BINS = 5
CELLS = math.prod([BINS] * len(GRID_AXES))
_AXIS = tuple(NAMES.index(a) for a in GRID_AXES)


def cell_of(values: tuple[float, ...]) -> tuple[int, ...]:
    return tuple(min(BINS - 1, int(values[i] * BINS)) for i in _AXIS)


class _Line(BaseModel):
    v: list[float] = Field(min_length=len(NAMES), max_length=len(NAMES))
    h: str = Field(pattern="^[0-9a-f]{1,144}$")


class Archive:
    def __init__(self, entries: Iterable[Descriptors] = ()) -> None:
        self.entries: list[Descriptors] = []
        self.cells: Counter[tuple[int, ...]] = Counter()
        for e in entries:
            self.add(e)

    def add(self, d: Descriptors) -> None:
        self.entries.append(d)
        self.cells[cell_of(d.values)] += 1

    def nearest(self, d: Descriptors) -> float:
        """Distance to the closest archived slide; 1.0 when the archive is empty."""
        return min((distance(d, e) for e in self.entries), default=1.0)

    def coverage(self) -> float:
        return len(self.cells) / CELLS

    def density(self, values: tuple[float, ...]) -> int:
        return self.cells[cell_of(values)]

    def lines(self) -> list[str]:
        return [json.dumps({"v": list(e.values), "h": format(e.hash, "x")}) for e in self.entries]

    @staticmethod
    def from_lines(lines: Iterable[str]) -> Archive:
        out = Archive()
        for line in lines:
            if line.strip():
                raw = _Line.model_validate_json(line)
                out.add(Descriptors(tuple(raw.v), int(raw.h, 16)))
        return out
