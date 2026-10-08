"""The design score and --candidates (phase 39 -> 7): a broken slide never
wins, shared axes beat scattered edges, and N candidates cost N calls."""

from __future__ import annotations

import asyncio
from pathlib import Path

from engine import Seam, pipeline
from engine.qa.metrics import Box
from engine.qa.score import score
from tests.test_ladder import AlwaysTheSame, _no_sleep
from tests.test_references import SWISS, _story


def _box(l: float, t: float, r: float, b: float, size: float = 34) -> Box:  # noqa: E741
    return Box(
        field="x", l=l, t=t, r=r, b=b, color=[0, 0, 0], size=size, lines=1, chars=10, contrast=10
    )


def test_errors_always_lose() -> None:
    assert score([_box(120, 120, 900, 300)], [], errors=1).total < score([], []).total


def test_shared_axes_beat_scattered_edges() -> None:
    aligned = [_box(120, 120 + i * 200, 900, 260 + i * 200) for i in range(4)]
    scattered = [_box(120 + i * 230, 120 + i * 200, 900, 260 + i * 200) for i in range(4)]
    assert score(aligned, []).alignment > score(scattered, []).alignment


def test_one_hero_scores_over_equal_sizes() -> None:
    hero = [_box(120, 120, 1500, 500, size=208), _box(120, 700, 900, 760)]
    flat = [_box(120, 120, 1500, 500, size=34), _box(120, 700, 900, 760)]
    assert score(hero, []).hero > score(flat, []).hero


def test_candidates_compose_n_and_keep_one(tmp_path: Path) -> None:
    transport = AlwaysTheSame()
    built = asyncio.run(
        pipeline.build(
            Seam(api_key="k", transport=transport, sleep=_no_sleep),
            _story(1),
            SWISS,
            model="m",
            title="t",
            work_file=str(tmp_path / "qa.html"),
            shots_dir=str(tmp_path),
            budget_usd=1.0,
            candidates=3,
        )
    )
    assert transport.calls.count("compose") == 3
    assert len(built.slides) == 1 and built.slides[0].qa.status == "passed"
