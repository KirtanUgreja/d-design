"""Sampled themes (phase 23 -> Verify): contrast holds over 1,000 seeds, a
seed always gives the same theme, and the exemplars survive sampled looks."""

from __future__ import annotations

import asyncio
import random
from pathlib import Path

from engine.compose.document import Frame
from engine.compose.exemplars import load_all
from engine.design.color import from_hex, passes
from engine.design.palettes import BODY, GRAPHIC, LARGE, TEXT
from engine.design.sampler import draw, sample
from engine.design.theme import build
from engine.qa import browser
from engine.qa.lint import lint


def test_a_thousand_seeds_never_fail_contrast() -> None:
    failures = []
    for seed in range(1000):
        rng = random.Random(seed)
        brand = "#ff5a1f" if seed % 7 == 0 else None
        theme = build(draw(rng, f"d{seed}", 0, "auto", brand))
        c = {k: from_hex(v) for k, v in theme.colors.items()}
        pairs = [
            ("ink", "ground", TEXT),
            ("ink", "surface", BODY),
            ("ink-2", "ground", BODY),
            ("ink-2", "surface", BODY),
            ("on-accent", "accent", BODY),
            ("accent", "ground", LARGE),
            ("ground", "ink", BODY),
        ] + [(f"series-{n}", "ground", GRAPHIC) for n in range(1, 6)]
        failures += [(seed, a, b) for a, b, need in pairs if not passes(c[a], c[b], need)]
    assert failures == []


def test_the_same_seed_gives_the_same_theme() -> None:
    a = [build(look) for look in sample("deck-1", deck_type="pitch")]
    b = [build(look) for look in sample("deck-1", deck_type="pitch")]
    assert [t.colors for t in a] == [t.colors for t in b]
    assert [t.look for t in a] == [t.look for t in b]
    shuffled = sample(
        "deck-1", deck_type="pitch", shuffle=1, exclude=frozenset(t.look["pairing"] for t in a)
    )
    assert not {t.look["pairing"] for t in a} & {x.pairing.id for x in shuffled}


def test_three_looks_share_no_pairing_or_grid() -> None:
    for n in range(20):
        looks = sample(f"deck-{n}")
        assert len({x.pairing.id for x in looks}) == 3
        assert len({x.grid.id for x in looks}) == 3


def test_exemplars_pass_qa_under_50_sampled_themes(tmp_path: Path) -> None:
    exemplars = load_all()
    frames = [Frame(e.id, e.html, e.css) for e in exemplars]
    fields = {e.id: e.fields for e in exemplars}
    assert all(lint(e.css) == [] for e in exemplars)
    rng = random.Random(23)
    bad: dict[str, list[tuple[str, str | None, str]]] = {}
    for n in range(50):
        theme = build(draw(rng, f"x{n}", 0, "auto", None))
        result = asyncio.run(browser.measure(theme, frames, fields, str(tmp_path / "qa.html")))
        for slide, m in result.items():
            if m.errors or not m.measured:
                look = theme.look
                key = f"{slide} @ {look['pairing']}/{look['scale']}/{look['palette']}"
                bad[key] = [(d.code, d.field, str(d.measured)) for d in m.errors]
    assert bad == {}


def test_the_hand_themes_meet_the_sampled_contrast_targets() -> None:
    from engine.design.theme import THEMES

    for theme in THEMES.values():
        c = {k: from_hex(v) for k, v in theme.colors.items()}
        pairs = [
            ("ink", "ground", TEXT),
            ("ink", "surface", BODY),
            ("ink-2", "ground", BODY),
            ("ink-2", "surface", BODY),
            ("on-accent", "accent", BODY),
            ("accent", "ground", LARGE),
        ]
        assert [(a, b) for a, b, n in pairs if not passes(c[a], c[b], n)] == [], theme.id
