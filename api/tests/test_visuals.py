"""Drawn visuals (components/visuals.py): tokens only, the planned words only,
and the storyline's limits on them (offline)."""

from __future__ import annotations

import re

import pytest

from engine.components import visuals
from engine.models import Brief, VisualSpec
from engine.studio.outline import Draft, DraftSlide, assemble, visual_lines

KINDS = ["waveform", "phone", "browser", "chat", "flow", "hub", "pipeline", "stack"]


@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_draws_in_theme_tokens_only(kind: str) -> None:
    spec = VisualSpec.model_validate({"kind": kind, "lines": ["Talk", "Listen", "Ship"]})
    out = visuals.svg(spec)
    assert out.startswith("<svg") and "var(--c-accent)" in out
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", out)  # no colour of its own
    assert not re.search(r"gradient|filter|blur|<image|href", out, re.I)


def test_fill_draws_into_the_box_and_strip_removes_an_unplanned_one() -> None:
    html = '<section class="s"><dd-visual class="v"></dd-visual></section>'
    drawn = visuals.fill(html, VisualSpec(kind="chat", lines=["I need a salon app"]))
    assert "I need a salon app" in drawn and drawn.count("<svg") == 1
    assert "<dd-visual" not in visuals.strip(html)


def test_a_visual_shows_short_lines_with_no_numbers() -> None:
    lines = visual_lines(
        ["Book a stylist in one tap today please now", "Save 40% on fees", " ", "Pay"]
    )
    assert lines == ["Book a stylist in one tap today please", "Pay"]  # eight words


def _slide(**kw: object) -> DraftSlide:
    base: dict[str, object] = {
        "beat": "solution",
        "intent": "statement",
        "kicker": "",
        "headline": "Swarvani builds the app you describe",
        "points": [],
        "stat": "",
        "stat_label": "",
        "fact_ids": [],
    }
    return DraftSlide.model_validate(base | kw)


def test_at_most_three_visuals_per_deck() -> None:
    draft = Draft(
        title="Tessel",
        governing_thought="g",
        key_points=["a"],
        slides=[_slide(visual="chat", visual_lines=["I need an app"]) for _ in range(5)],
    )
    story, _ = assemble(draft, Brief(id="b", prompt="launch Swarvani"), [])
    kinds = [s.visual.kind if s.visual else None for s in story.slides]
    assert kinds == ["chat", "chat", "chat", None, None]
