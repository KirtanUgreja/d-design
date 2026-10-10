"""Sampled themes (phase 23 -> Verify): contrast holds over 1,000 seeds, a
seed always gives the same theme, and the code-built layout (every slide's
floor) survives sampled looks."""

from __future__ import annotations

import asyncio
import random
from pathlib import Path

from engine.design import dataviz
from engine.design.color import from_hex, passes
from engine.design.palettes import BODY, LARGE, TEXT
from engine.design.sampler import draw, sample
from engine.design.theme import build
from engine.qa import browser
from engine.qa.lint import lint
from tests.fakes import sample_frames


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
        ]
        failures += [(seed, a, b) for a, b, need in pairs if not passes(c[a], c[b], need)]
        # Chart colours meet the dataviz method's checks instead (phase 37).
        marks = [c[k] for k in sorted(c) if k.startswith("series-")]
        check = dataviz.validate(marks, c["ground"], c["ground"].l < 0.5)
        if len(marks) < 4 or not check.ok:
            failures.append((seed, "series", "; ".join(check.problems) or f"{len(marks)} slots"))
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


def test_the_code_built_layout_passes_qa_under_sampled_themes(tmp_path: Path) -> None:
    frames, fields = sample_frames()
    assert all(lint(f.css) == [] for f in frames)
    rng = random.Random(23)
    bad: dict[str, list[tuple[str, str | None, str]]] = {}
    for n in range(20):
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


def test_every_deck_gets_its_own_look() -> None:
    from engine.design.sampler import look_for

    seen = set()
    for n in range(300):
        look = look_for(f"deck-{n}", words=f"a brief about thing {n}")
        theme = build(look)
        seen.add(
            (
                theme.look["pairing"],
                tuple(theme.colors.values()),
                tuple(theme.scale.values()),
                theme.margin,
                theme.tiles["halftone"],
                theme.mark,
            )
        )
    assert len(seen) == 300
    first = build(look_for("deck-1", words="Tesla pitch"))
    again = build(look_for("deck-1", words="Tesla pitch"))
    other = build(look_for("deck-1", words="Tesla pitch", nonce=1))
    assert first.colors == again.colors and first.mark == again.mark
    assert (first.colors, first.mark) != (other.colors, other.mark)
