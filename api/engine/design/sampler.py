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

from engine.design import patterns
from engine.design.axes import (
    DENSITIES,
    EDGES,
    GRIDS,
    IMAGE_TREATMENTS,
    MOTIFS,
    MOTIONS,
    PAIRINGS,
    Grid,
    Motif,
    Pairing,
)
from engine.design.color import Oklch, from_hex
from engine.design.palettes import DARK, STRATEGIES, Roles, brand, resolve
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
    # Continuous, per look: no two decks share these (design-engine.md -> "Generated").
    heading_ratio: float = 1.25
    display_ratio: float = 1.38
    margin: int = 112
    gutter: int = 32
    rule: int = 3
    radius: int = 0
    track: float = 0.0
    texture: patterns.Params = patterns.DEFAULT
    mark: str = ""

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
            "ratios": f"{self.heading_ratio:.2f}/{self.display_ratio:.2f}",
            "margin": str(self.margin),
            "texture": f"dots {self.texture.dot_pitch}px, hatch {self.texture.hatch_angle}deg",
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


# Topic words that steer the hue, and how often they are followed; the rest of
# the time the hue is free, so a climate deck is not always green.
# ponytail: a keyword list. Upgrade: a mood read from the storyline.
TOPIC_HUES: tuple[tuple[tuple[str, ...], tuple[float, float]], ...] = (
    (("climate", "carbon", "energy", "solar", "heat", "green", "sustain", "electric"), (110, 190)),
    (("health", "clinic", "medical", "care", "patient", "bio", "physio"), (150, 215)),
    (("finance", "bank", "fund", "invest", "payment", "ledger", "revenue", "close"), (215, 265)),
    (("food", "meal", "coffee", "bakery", "kitchen", "potluck", "oven", "cook"), (18, 70)),
    (("freight", "logistics", "shipping", "industrial", "hardware", "factory"), (195, 240)),
    (("car", "vehicle", "auto", "mobility", "battery", "tesla"), (0, 30)),
)
TOPIC_FOLLOWED = 0.7
TONE: dict[str, tuple[tuple[float, float], tuple[str, ...]]] = {
    # tone -> (display ratio range, palettes it leans to)
    "plain": ((1.25, 1.36), ("paper", "signal", "tonal")),
    "confident": ((1.3, 1.45), ("paper", "night", "blocks", "signal", "duotone")),
    "warm": ((1.28, 1.42), ("paper", "duotone", "tonal", "blocks")),
    "bold": ((1.38, 1.5), ("night", "blocks", "deep", "signal")),
}


def _hue(rng: random.Random, words: str) -> float:
    lowered = words.lower()
    for keys, (lo, hi) in TOPIC_HUES:
        if any(k in lowered for k in keys) and rng.random() < TOPIC_FOLLOWED:
            return rng.uniform(lo, hi) % 360
    return rng.uniform(0, 360)


def _scale_name(display_ratio: float) -> str:
    return "modest" if display_ratio < 1.33 else "dramatic" if display_ratio < 1.42 else "extreme"


def draw(
    rng: random.Random,
    deck_id: str,
    n: int,
    deck_type: str,
    brand_hex: str | None,
    *,
    tone: str = "confident",
    words: str = "",
) -> Look:
    """One look, generated: the choices that must be discrete (a font family, a
    palette strategy) are drawn, and everything that can be continuous is."""
    prior = PRIORS.get(deck_type, {})
    ratio_range, leaning = TONE.get(tone, TONE["confident"])
    while True:
        pairing = rng.choice(PAIRINGS)
        grid_id = _pick(rng, [g.id for g in GRIDS], prior.get("grid"))
        grid = next(g for g in GRIDS if g.id == grid_id)
        display_ratio = rng.uniform(*ratio_range)
        scale = _scale_name(display_ratio)
        density = _pick(rng, list(DENSITIES), prior.get("density"))
        if _compatible(pairing, scale, density, grid):
            break
    palettes = list(BRAND_PALETTES) if brand_hex else list(STRATEGIES)
    weights = [3.0 if p in leaning else 1.0 for p in palettes]
    palette = rng.choices(palettes, weights=weights)[0]
    hue = from_hex(brand_hex).h if brand_hex else _hue(rng, words)
    roles = STRATEGIES[palette](hue, rng)
    if brand_hex:
        roles = brand(brand_hex, roles)
    edge = rng.choice(list(EDGES))
    wide = pairing.kind in ("wide", "mono")
    return Look(
        id=f"{deck_id}-{n}",
        pairing=pairing,
        palette=palette,
        hue=hue,
        roles=resolve(roles),
        grid=grid,
        motif=rng.choice(MOTIFS),
        scale=scale,
        edge=edge,
        density=density,
        motion=rng.choice(MOTIONS),
        image=rng.choice(IMAGE_TREATMENTS),
        heading_ratio=round(rng.uniform(1.18, 1.32), 3),
        display_ratio=round(display_ratio, 3),
        margin=round(rng.uniform(96, 144)),
        gutter=round(rng.uniform(20, 48)),
        rule=round(rng.uniform(2, 6)),
        radius=round(rng.uniform(4, 14)) if edge == "soft" else 0,
        track=round(rng.uniform(-0.01, 0.01) if wide else rng.uniform(-0.035, 0.01), 3),
        texture=patterns.Params.draw(rng),
        mark=patterns.mark(words or deck_id, rng),
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


def look_for(
    deck_id: str,
    *,
    deck_type: str = "auto",
    tone: str = "confident",
    words: str = "",
    brand_hex: str | None = None,
    nonce: int = 0,
) -> Look:
    """The one look a deck gets — generated, never picked from a menu. The deck's
    words steer it; ``nonce`` gives a new one when the user asks for another."""
    rng = random.Random(seed_of(f"{deck_id}/{words}/{nonce}"))  # noqa: S311 - a look, not a secret
    return draw(rng, deck_id, nonce, deck_type, brand_hex, tone=tone, words=words)
