"""Visual languages (phase 39 -> Verify): over 1,000 seeds every language is
drawn, contrast holds, and every draw stays inside its language's system."""

from __future__ import annotations

import random
from collections import Counter

from engine.design import dataviz
from engine.design.color import from_hex, passes
from engine.design.languages import all_languages, choose, get
from engine.design.palettes import BODY, LARGE, TEXT
from engine.design.sampler import look_for
from engine.design.theme import build

PAIRS = [
    ("ink", "ground", TEXT),
    ("ink", "surface", BODY),
    ("ink-2", "ground", BODY),
    ("ink-2", "surface", BODY),
    ("on-accent", "accent", BODY),
    ("accent", "ground", LARGE),
]


def test_eight_languages_load() -> None:
    ids = [lang.id for lang in all_languages()]
    assert ids == sorted(
        ["swiss", "editorial", "poster", "cinematic", "journal", "minimal", "bauhaus", "humanist"]
    )
    assert all(lang.allowed_pairings for lang in all_languages())


def test_a_thousand_seeds_stay_inside_their_language() -> None:
    drawn: Counter[str] = Counter()
    failures: list[tuple[int, str]] = []
    for seed in range(1000):
        brand = "#ff5a1f" if seed % 7 == 0 else None
        look = look_for(f"deck-{seed}", words=f"brief {seed}", brand_hex=brand)
        lang = get(look.language)
        drawn[lang.id] += 1
        theme = build(look)
        c = {k: from_hex(v) for k, v in theme.colors.items()}
        failures += [(seed, f"{a}/{b}") for a, b, need in PAIRS if not passes(c[a], c[b], need)]
        marks = [c[k] for k in sorted(c) if k.startswith("series-")]
        if not dataviz.validate(marks, c["ground"], c["ground"].l < 0.5).ok:
            failures.append((seed, "series"))
        if not lang.allows(look.pairing):
            failures.append((seed, f"pairing {look.pairing.id} outside {lang.id}"))
        if look.grid.id not in lang.grids or look.edge not in lang.edges:
            failures.append((seed, f"grid or edge outside {lang.id}"))
        if look.density not in lang.density:
            failures.append((seed, f"density outside {lang.id}"))
        if bool(look.shapes) != lang.shapes:
            failures.append((seed, f"shapes policy broken in {lang.id}"))
        if lang.texture == "never" and theme.textures != ("solid",):
            failures.append((seed, f"texture in {lang.id}"))
        if lang.dark in (0.0, 1.0) and look.dark != (lang.dark == 1.0):
            failures.append((seed, f"ground policy broken in {lang.id}"))
        if look.image not in lang.image.styles:
            failures.append((seed, "image style"))
        if lang.name not in theme.guidance:
            failures.append((seed, "the brief is not in the guidance"))
    assert failures == []
    assert set(drawn) == {lang.id for lang in all_languages()}
    assert min(drawn.values()) >= 50  # roughly balanced, with priors


def test_usage_balances_the_draw() -> None:
    rng = random.Random(1)
    heavy = {lang.id: 50 for lang in all_languages() if lang.id != "humanist"}
    picks = Counter(choose(rng, usage=heavy).id for _ in range(200))
    assert picks.most_common(1)[0][0] == "humanist"


def test_another_style_changes_the_language() -> None:
    first = look_for("deck-x", words="a pitch")
    other = look_for("deck-x", words="a pitch", nonce=1, exclude=frozenset({first.language}))
    assert other.language != first.language
    assert look_for("deck-x", words="a pitch").language == first.language
