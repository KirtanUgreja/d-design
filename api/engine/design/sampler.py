"""The sampler: three looks per deck, as far apart as possible
(docs/v4/design-engine.md -> "Sampler and theme"). Pure code, no model call.

- Seeded by the deck id, so the same deck always gets the same looks.
- Constraints first: brand colours limit the palettes; compatibility rules
  drop bad combinations; deck type sets priors but never decides alone.
- The first look is random; each next one maximises its distance to those
  already picked. No two looks share a pairing or a grid.
"""

from __future__ import annotations

import dataclasses
import hashlib
import random
from collections.abc import Mapping
from dataclasses import dataclass

from engine.design import languages, palettes, patterns
from engine.design.axes import (
    DENSITIES,
    EDGES,
    GRIDS,
    IMAGE_TREATMENTS,
    MOTIONS,
    PAIRINGS,
    Grid,
    Motif,
    Pairing,
)
from engine.design.color import from_hex
from engine.design.languages import Language
from engine.design.palettes import Roles, brand, resolve
from engine.design.theme import display_width, face

CANDIDATES = 160
EXTREME_MAX_WIDTH = 0.52  # em; condensed faces and the tighter grotesks
INSTANCE_WIDER = 1.05  # a variable instance's widest, against its pairing's weight

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
    motif_tile: str = ""  # the deck's generated texture mask (patterns.motif)
    shapes: tuple[tuple[str, str], ...] = ()  # kind -> mask url, drawn per deck
    # The display face's own instance, when it is variable: axis -> value.
    instance: tuple[tuple[str, float], ...] = ()
    language: str = ""  # the visual language's id (design/languages.py); "" = none
    finish: str = "none"  # none · fine · film: the grain over every slide
    glow: bool = False  # may a slide carry one soft glow (dd-glow)

    def axis(self, tag: str, default: float) -> float:
        return next((v for t, v in self.instance if t == tag), default)

    @property
    def dark(self) -> bool:
        return self.roles["ground"].l < 0.5

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
            "language": self.language,
        }


def seed_of(deck_id: str) -> int:
    """A stable seed; Python's hash() changes per process."""
    return int.from_bytes(hashlib.sha256(deck_id.encode()).digest()[:8], "big")


def _pick(rng: random.Random, values: list[str], prior: dict[str, float] | None) -> str:
    weights = [prior.get(v, 1.0) for v in values] if prior else None
    return rng.choices(values, weights=weights)[0]


def _instance(rng: random.Random, pairing: Pairing) -> tuple[tuple[str, float], ...]:
    """A variable display face's instance for this deck: weight near the
    pairing's (display faces stay heavy), width, and Fraunces' softness and
    wonk. Optical size follows the type size by itself."""
    display = face(pairing.display)
    out: list[tuple[str, float]] = []
    if wght := display.axis("wght"):
        w0 = pairing.display_weight
        w = rng.uniform(max(wght[0], w0 - 100), min(wght[1], w0 + 100))
        # Some faces widen fast with weight (Syne): never more than 5% wider
        # than the weight the pairing was tested at.
        limit = display_width(pairing.display, w0) * INSTANCE_WIDER
        while w > w0 and display_width(pairing.display, w) > limit:
            w -= 10
        out.append(("wght", round(w)))
    if wdth := display.axis("wdth"):
        weight = next((v for t, v in out if t == "wght"), pairing.display_weight)
        stretch = rng.uniform(max(wdth[0], 72), min(wdth[1], 112))
        limit = display_width(pairing.display, pairing.display_weight) * INSTANCE_WIDER
        while stretch > 100 and display_width(pairing.display, weight, stretch) > limit:
            stretch -= 1
        out.append(("wdth", round(stretch, 1)))
    if display.axis("SOFT"):
        out.append(("SOFT", round(rng.uniform(0, 100))))
    if display.axis("WONK"):
        out.append(("WONK", float(rng.random() < 0.5)))
    return tuple(out)


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
# tone -> display ratio range; the tone's lean on colour is palettes.TILTS.
TONE: dict[str, tuple[float, float]] = {
    "plain": (1.25, 1.36),
    "confident": (1.3, 1.45),
    "warm": (1.28, 1.42),
    "bold": (1.38, 1.5),
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
    language: Language | None = None,
) -> Look:
    """One look, generated: the choices that must be discrete (a font family, a
    grid) are drawn, and everything that can be continuous is, colour included.
    A visual language narrows every discrete choice to what its system allows."""
    prior = PRIORS.get(deck_type, {})
    ratio_range = language.ratio if language else TONE.get(tone, TONE["confident"])
    pairings = language.allowed_pairings if language else PAIRINGS
    grid_ids = list(language.grids) if language else [g.id for g in GRIDS]
    densities = list(language.density) if language else list(DENSITIES)
    for _ in range(500):  # ponytail: rejection sampling; every language has a fit
        pairing = rng.choice(pairings)
        grid_id = _pick(rng, grid_ids, prior.get("grid"))
        grid = next(g for g in GRIDS if g.id == grid_id)
        display_ratio = rng.uniform(*ratio_range)
        scale = _scale_name(display_ratio)
        density = _pick(rng, densities, prior.get("density"))
        if _compatible(pairing, scale, density, grid):
            break
    hue = from_hex(brand_hex).h if brand_hex else _hue(rng, words)
    # A brand keeps its own hue as the accent, so the two-colour split is off.
    roles = palettes.generate(
        hue,
        rng,
        tone,
        split=not brand_hex,
        dark_chance=language.dark if language else None,
        split_chance=language.split if language else None,
    )
    if brand_hex:
        roles = brand(brand_hex, roles)
    roles = resolve(roles)
    edge = rng.choice(list(language.edges) if language else list(EDGES))
    motif_tile, motif_note = patterns.motif(rng)
    motif = Motif("generated", ("motif", "solid"), motif_note)
    if language and language.texture == "never":
        motif = Motif("plain", ("solid",), "no texture: flat colour fields only")
    shapes = patterns.shapes(rng)  # drawn always, so the rng stream stays the same
    wide = pairing.kind in ("wide", "mono")
    finish, glow = _surface(deck_id, n, language)
    return Look(
        id=f"{deck_id}-{n}",
        pairing=pairing,
        palette=palettes.describe(roles),
        hue=hue,
        roles=roles,
        grid=grid,
        motif=motif,
        scale=scale,
        edge=edge,
        density=density,
        motion=rng.choice(MOTIONS),
        image=rng.choice(language.image.styles if language else IMAGE_TREATMENTS),
        heading_ratio=round(rng.uniform(1.18, 1.32), 3),
        display_ratio=round(display_ratio, 3),
        margin=round(rng.uniform(96, 144)),
        gutter=round(rng.uniform(20, 48)),
        rule=round(rng.uniform(2, 6)),
        radius=round(rng.uniform(4, 14)) if edge == "soft" else 0,
        track=round(rng.uniform(-0.01, 0.01) if wide else rng.uniform(-0.035, 0.01), 3),
        texture=patterns.Params.draw(rng),
        mark=patterns.mark(words or deck_id, rng),
        motif_tile=motif_tile,
        instance=_instance(rng, pairing),
        shapes=tuple(shapes.items()) if language is None or language.shapes else (),
        language=language.id if language else "",
        finish=finish,
        glow=glow,
    )


def _surface(deck_id: str, n: int, language: Language | None) -> tuple[str, bool]:
    """The deck's finish and glow, from what its language allows. Its own
    random stream, so adding it moved no existing look."""
    rng = random.Random(seed_of(f"{deck_id}/{n}/surface"))  # noqa: S311 - a look
    finishes = language.finishes if language else ("none",)
    return rng.choice(finishes), bool(language and language.glow and rng.random() < 0.7)


def distance(a: Look, b: Look) -> float:
    return (
        3.0 * (a.pairing.kind != b.pairing.kind)
        + 1.0 * (a.pairing.id != b.pairing.id)
        + 2.0 * palettes.gap(a.roles, b.roles)
        + 2.0 * (a.dark != b.dark)
        + 2.0 * (a.grid.id != b.grid.id)
        + 1.5 * (a.motif.note.split()[0] != b.motif.note.split()[0])
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
    usage: Mapping[str, int] | None = None,
    exclude: frozenset[str] = frozenset(),
    language: str = "",
) -> Look:
    """The one look a deck gets — generated, never picked from a menu. The
    visual language is drawn first (balanced by ``usage``, the count of decks
    per language so far), then the tokens it allows. The deck's words steer
    it; ``nonce`` gives a new one when the user asks for another style, and
    ``exclude`` keeps it off the languages already shown; ``language`` forces
    the language the deck already has."""
    rng = random.Random(seed_of(f"{deck_id}/{words}/{nonce}"))  # noqa: S311 - a look, not a secret
    drawn = languages.choose(rng, tone=tone, deck_type=deck_type, usage=usage, exclude=exclude)
    # A deck keeps the language it drew first (``language``), so its look is
    # the same on every later call however usage has moved since.
    chosen = languages.get(language) if language else drawn
    return draw(rng, deck_id, nonce, deck_type, brand_hex, tone=tone, words=words, language=chosen)


def recolour(
    look: Look, nonce: int, *, tone: str = "confident", brand_hex: str | None = None
) -> Look:
    """The same look in another palette: type, grid, scale, texture and mark
    all kept, so every composed slide keeps its layout (docs/v4/plan/28-editor.md
    -> Look). Deterministic for a nonce; contrast still fitted by resolve()."""
    rng = random.Random(seed_of(f"{look.id}/recolour/{nonce}"))  # noqa: S311 - a look
    if brand_hex:  # a brand keeps its accent; new colours means a new ground and ink
        roles = resolve(brand(brand_hex, palettes.generate(from_hex(brand_hex).h, rng, tone)))
        return dataclasses.replace(look, roles=roles, palette=palettes.describe(roles))
    roles = resolve(palettes.generate(look.hue if nonce == 0 else rng.uniform(0, 360), rng, tone))
    return dataclasses.replace(look, roles=roles, palette=palettes.describe(roles))
