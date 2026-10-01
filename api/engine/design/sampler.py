"""The sampler: three looks per deck, as far apart as possible
(docs/v4/design-engine.md -> "Sampler and theme"). Pure code, no model call.

- Seeded by the deck id, so the same deck always gets the same looks.
- Constraints first: brand colours limit the palettes; compatibility rules
  drop bad combinations; deck type sets priors but never decides alone.
- The first look is random; each next one maximises its distance to those
  already picked. No two looks share a pairing or a grid.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from engine.design.axes import (
    DENSITIES,
    EDGES,
    GRIDS,
    IMAGE_TREATMENTS,
    MOTIFS,
    MOTIONS,
    PAIRINGS,
    SCALES,
    Grid,
    Motif,
    Pairing,
)
from engine.design.color import Oklch, from_hex
from engine.design.palettes import DARK, HUES, STRATEGIES, Roles, brand, resolve
from engine.design.theme import display_width

CANDIDATES = 160
EXTREME_MAX_WIDTH = 0.52  # em; condensed faces and the tighter grotesks
BRAND_PALETTES = ("paper", "night", "blocks", "signal", "tonal")

# deck type -> axis -> {value: weight}. A prior tilts the draw, never fixes it.
PRIORS: dict[str, dict[str, dict[str, float]]] = {
    "investor_update": {
        "density": {"dense": 3, "balanced": 2, "airy": 0.5},
        "grid": {"swiss": 3, "modular": 3, "editorial": 1, "asymmetric": 1, "poster": 0.3},
    },
    "pitch": {"scale": {"dramatic": 3, "extreme": 2, "modest": 1}},
    "launch": {
        "scale": {"extreme": 3, "dramatic": 2, "modest": 0.5},
        "grid": {"poster": 3, "asymmetric": 2, "swiss": 1, "modular": 1, "editorial": 1},
    },
    "sales": {"density": {"balanced": 3, "airy": 1, "dense": 1}},
    "partnership": {
        "grid": {"editorial": 3, "asymmetric": 2, "swiss": 1, "modular": 1, "poster": 1}
    },
}


@dataclass(frozen=True)
class Look:
    id: str
    pairing: Pairing
    palette: str
    hue: float
    roles: Roles
    grid: Grid
    motif: Motif
    scale: str
    edge: str
    density: str
    motion: str
    image: str

    @property
    def dark(self) -> bool:
        return self.palette in DARK

    def record(self) -> dict[str, str]:
        return {
            "pairing": self.pairing.id,
            "palette": self.palette,
            "hue": f"{self.hue:.0f}",
            "grid": self.grid.id,
            "motif": self.motif.id,
            "scale": self.scale,
            "edge": self.edge,
            "density": self.density,
            "motion": self.motion,
            "image": self.image,
        }


def seed_of(deck_id: str) -> int:
    """A stable seed; Python's hash() changes per process."""
    return int.from_bytes(hashlib.sha256(deck_id.encode()).digest()[:8], "big")


def _pick(rng: random.Random, values: list[str], prior: dict[str, float] | None) -> str:
    weights = [prior.get(v, 1.0) for v in values] if prior else None
    return rng.choices(values, weights=weights)[0]


def _compatible(p: Pairing, scale: str, density: str, grid: Grid) -> bool:
    if p.kind == "didone" and density == "dense":
        return False  # hairline serifs need air
    if scale == "extreme" and display_width(p.display, p.display_weight) > EXTREME_MAX_WIDTH:
        return False  # extreme sizes need a narrow face, or a figure fills the slide
    return not (p.kind == "mono" and grid.id == "poster")


def draw(rng: random.Random, deck_id: str, n: int, deck_type: str, brand_hex: str | None) -> Look:
    prior = PRIORS.get(deck_type, {})
    while True:
        pairing = rng.choice(PAIRINGS)
        grid_id = _pick(rng, [g.id for g in GRIDS], prior.get("grid"))
        grid = next(g for g in GRIDS if g.id == grid_id)
        scale = _pick(rng, list(SCALES), prior.get("scale"))
        density = _pick(rng, list(DENSITIES), prior.get("density"))
        if _compatible(pairing, scale, density, grid):
            break
    palettes = list(BRAND_PALETTES) if brand_hex else list(STRATEGIES)
    palette = rng.choice(palettes)
    hue = from_hex(brand_hex).h if brand_hex else rng.choice(HUES)
    roles = STRATEGIES[palette](hue, rng)
    if brand_hex:
        roles = brand(brand_hex, roles)
    return Look(
        id=f"{deck_id}-{n}",
        pairing=pairing,
        palette=palette,
        hue=hue,
        roles=resolve(roles),
        grid=grid,
        motif=rng.choice(MOTIFS),
        scale=scale,
        edge=rng.choice(list(EDGES)),
        density=density,
        motion=rng.choice(MOTIONS),
        image=rng.choice(IMAGE_TREATMENTS),
    )


def _hue_gap(a: Oklch, b: Oklch) -> float:
    d = abs(a.h - b.h) % 360
    return min(d, 360 - d) / 180


def distance(a: Look, b: Look) -> float:
    return (
        3.0 * (a.pairing.kind != b.pairing.kind)
        + 1.0 * (a.pairing.id != b.pairing.id)
        + 2.0 * (a.palette != b.palette)
        + 2.0 * (a.dark != b.dark)
        + 2.0 * _hue_gap(a.roles["accent"], b.roles["accent"])
        + 2.0 * (a.grid.id != b.grid.id)
        + 1.5 * (a.motif.id != b.motif.id)
        + 1.0 * (a.scale != b.scale)
        + 0.5 * (a.edge != b.edge)
        + 0.5 * (a.density != b.density)
    )


def sample(
    deck_id: str,
    *,
    deck_type: str = "auto",
    brand_hex: str | None = None,
    shuffle: int = 0,
    exclude: frozenset[str] = frozenset(),
    count: int = 3,
) -> list[Look]:
    """``count`` looks for a deck. ``shuffle`` and ``exclude`` (pairing ids
    already shown) give the next set without repeating one."""
    rng = random.Random(seed_of(f"{deck_id}/{shuffle}"))  # noqa: S311 - a look, not a secret
    pool = [draw(rng, deck_id, n, deck_type, brand_hex) for n in range(CANDIDATES)]
    pool = [p for p in pool if p.pairing.id not in exclude] or pool
    picked = [pool[0]]
    while len(picked) < count:
        free = [
            p
            for p in pool
            if all(p.pairing.id != q.pairing.id and p.grid.id != q.grid.id for q in picked)
        ] or pool
        picked.append(max(free, key=lambda p: min(distance(p, q) for q in picked)))
    return [
        Look(**{**look.__dict__, "id": f"{deck_id}-s{shuffle}-{i}"})
        for i, look in enumerate(picked, start=1)
    ]
