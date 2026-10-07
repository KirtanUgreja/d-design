"""The planner's rhythm rules (docs/v4/design-engine.md -> Compositions)."""

from __future__ import annotations

from itertools import pairwise

from benchtools import files
from engine.compose import planner
from engine.models import PlanField, SlidePlan


def _plan(n: int, intent: str, *names: str, words: int = 3) -> SlidePlan:
    text = " ".join(["word"] * words)
    fields = [PlanField(name="headline", text=text, budget_words=12)]
    fields += [PlanField(name=name, text=text, budget_words=10) for name in names]
    return SlidePlan(id=f"s{n}", beat="b", intent=intent, fields=fields)


def test_fixed_ends_and_intents_need_their_data() -> None:
    plans = [
        _plan(1, "statement"),
        _plan(2, "chart"),  # no chart spec
        _plan(3, "number"),  # no stat field
        _plan(4, "section"),  # a short deck
        _plan(5, "points"),  # no points
        _plan(6, "chart", "point-1"),
        _plan(7, "statement"),
    ]
    got = [p.intent for p in planner.assign(plans)]
    assert got == ["cover", "statement", "statement", "statement", "statement", "points", "ask"]


def test_image_led_is_capped_at_forty_percent() -> None:
    plans = [_plan(n, "image-led") for n in range(10)]
    got = [p.intent for p in planner.assign(plans)]
    assert got.count("image-led") <= 4


def test_no_stored_layout_is_chosen() -> None:
    """Phase 36: the planner names no layout; the target decides geometry."""
    assert not hasattr(planner, "ARCHETYPES")
    for brief_id in files.brief_ids():
        outline = files.load(brief_id).outline
        assert outline is not None
        assert all(p.archetype == "" for p in planner.assign(outline.slides)), brief_id


def test_ornaments_are_rationed() -> None:
    for brief_id in files.brief_ids():
        outline = files.load(brief_id).outline
        assert outline is not None
        plans = planner.assign(outline.slides)
        kinds = [p.ornament for p in plans]
        assert "mark" not in kinds, brief_id  # the emblem is gone (owner, 2026-10-08)
        textures = kinds.count("texture")
        assert textures <= 0.4 * len(kinds) + 1, (brief_id, kinds)
        assert not any(a == b == "texture" for a, b in pairwise(kinds)), (brief_id, kinds)
