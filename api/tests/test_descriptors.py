"""Phase 36: composition descriptors, the archive and composition targets."""

from __future__ import annotations

import random

from engine.compose import targets
from engine.compose.archive import Archive
from engine.qa.descriptors import Descriptors, describe, distance
from engine.qa.metrics import Box, Shape


def box(field: str, l: float, t: float, r: float, b: float, size: float = 32) -> Box:  # noqa: E741
    return Box(
        field=field, l=l, t=t, r=r, b=b, color=[0, 0, 0], size=size, lines=1, chars=10, contrast=12
    )


# A big headline top-left, body under it: mass upper left, empty on the right.
LEFT = [box("headline", 120, 120, 900, 420, 160), box("body", 120, 480, 820, 600)]
# The mirror: the same blocks on the right, a colour field bleeding off the left.
RIGHT = [box("headline", 1020, 560, 1800, 860, 160), box("body", 1100, 900, 1800, 1000)]
FIELD = [Shape(kind="field", l=0, t=0, r=760, b=1080)]


def test_descriptors_read_known_geometry() -> None:
    d = describe(LEFT, []).named()
    assert d["mass_x"] < 0.35 and d["mass_y"] < 0.4
    assert d["empty"] > 0.4 and d["empty_x"] > 0.5
    assert d["hero"] > 0.5  # 160px over 32px
    assert d["field"] == 0 and d["edge"] == 0
    r = describe(RIGHT, FIELD).named()
    assert r["field"] > 0.3 and r["edge"] > 0.2


def test_hash_ignores_colour_and_text() -> None:
    recoloured = [b.model_copy(update={"color": [200, 10, 10], "chars": 99}) for b in LEFT]
    assert describe(LEFT, []).hash == describe(recoloured, []).hash
    assert distance(describe(LEFT, []), describe(recoloured, [])) == 0


def test_different_compositions_are_far_apart() -> None:
    assert distance(describe(LEFT, []), describe(RIGHT, FIELD)) > 0.3


def test_archive_round_trips_and_finds_repeats() -> None:
    a = Archive([describe(LEFT, [])])
    b = Archive.from_lines(a.lines())
    assert b.entries == a.entries
    assert b.nearest(describe(LEFT, [])) == 0
    assert b.nearest(describe(RIGHT, FIELD)) > 0.3
    assert 0 < b.coverage() < 0.01


def test_targets_fit_the_slides_job() -> None:
    rng = random.Random(1)
    for _ in range(50):
        t = targets.draw(rng, Archive(), "number", 2)
        assert t.point["hero"] >= 0.6
        t = targets.draw(rng, Archive(), "points", 6)
        assert t.point["blocks"] >= 0.5 - 1e-9


def test_targets_explore_where_nothing_was_made() -> None:
    rng = random.Random(2)
    crowded = Archive()
    first = targets.draw(rng, crowded, "statement", 2)
    for _ in range(200):
        crowded.add(Descriptors(first.values(), 0))
    again = targets.draw(rng, crowded, "statement", 2)
    assert crowded.density(again.values()) == 0


def test_targets_move_away_from_the_previous_slide() -> None:
    rng = random.Random(3)
    previous = targets.draw(rng, Archive(), "statement", 2)
    gaps = []
    for _ in range(30):
        t = targets.draw(rng, Archive(), "statement", 2, previous)
        gaps.append(
            abs(t.point["mass_x"] - previous.point["mass_x"])
            + abs(t.point["empty"] - previous.point["empty"])
        )
    assert sum(gaps) / len(gaps) > 0.25


def test_brief_is_geometry() -> None:
    t = targets.draw(random.Random(4), Archive(), "cover", 3)
    text = targets.brief(t)
    assert "Visual mass" in text and "empty" in text and "x the smallest" in text
