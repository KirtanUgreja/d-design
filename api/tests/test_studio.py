"""The studio's build, offline: the art director once, a designer and an
improver per slide, the safety net under them, and the worker's guarantees
(events, resume, abort, the budget)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from benchtools import files
from engine import Seam, Storyline
from engine.design.sampler import look_for
from engine.design.theme import THEMES
from engine.design.theme import build as build_theme
from engine.studio import build as studio
from engine.studio.build import Built
from engine.studio.slide import Kept
from tests.fakes import Studio, _no_sleep


def _story(n: int) -> Storyline:
    outline = files.load("pitch-devtools").outline
    assert outline is not None
    return outline.model_copy(update={"slides": outline.slides[:n]})


def _build(tmp_path: Path, transport: Studio, story: Storyline, **extra: object) -> Built:
    return asyncio.run(
        studio.build(
            Seam(api_key="k", transport=transport, sleep=_no_sleep),
            story,
            THEMES["ledger"],
            model="m",
            title="t",
            work_file=str(tmp_path / "qa.html"),
            shots_dir=str(tmp_path),
            budget_usd=1.0,
            **extra,  # type: ignore[arg-type]
        )
    )


def test_four_layers_direct_once_then_design_and_improve_each_slide(tmp_path: Path) -> None:
    transport = Studio()
    built = _build(tmp_path, transport, _story(4))
    assert transport.calls[0] == "direct" and transport.calls.count("direct") == 1
    assert transport.calls.count("compose") == 4
    assert transport.calls.count("review") == 1  # layer 5: the whole deck, once
    assert transport.calls.count("improve") == 4 + 1  # each slide, then the one sent back
    assert {s.origin for s in built.slides} == {"improved"} and built.improved == 4
    assert all(s.qa.status == "passed" for s in built.slides)
    assert "<section" in built.html and "<section" in built.send


def test_the_improver_sees_the_rendered_slide(tmp_path: Path) -> None:
    sent: list[object] = []
    transport = Studio()
    post = transport.post

    async def spy(url: str, *, json: object, headers: dict[str, str]):  # type: ignore[no-untyped-def]
        sent.append(json)
        return await post(url, json=json, headers=headers)

    transport.post = spy  # type: ignore[method-assign]
    _build(tmp_path, transport, _story(2), improving=True)
    improve = [
        b for b in sent if isinstance(b, dict) and isinstance(b["messages"][-1]["content"], list)
    ]
    assert len(improve) == 2
    parts = improve[0]["messages"][-1]["content"]
    assert parts[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_broken_designs_fall_to_the_code_layout_and_pass(tmp_path: Path) -> None:
    transport = Studio(broken=True)
    built = _build(tmp_path, transport, _story(3))
    assert transport.calls.count("repair") == 3 * studio.REPAIR_ROUNDS
    assert {s.origin for s in built.slides} == {"fallback"}
    assert all(s.qa.status == "passed" for s in built.slides), [
        (s.id, [d.code for d in s.qa.errors]) for s in built.slides
    ]


def test_the_budget_stops_every_call_once_it_is_spent(tmp_path: Path) -> None:
    transport = Studio()
    built = asyncio.run(
        studio.build(
            Seam(api_key="k", transport=transport, sleep=_no_sleep),
            _story(3),
            THEMES["ledger"],
            model="m",
            title="t",
            work_file=str(tmp_path / "qa.html"),
            shots_dir=str(tmp_path),
            budget_usd=0.0025,  # each call costs 0.001: three calls, then nothing
        )
    )
    assert len(transport.calls) == 3
    assert len(built.slides) == 3 and all(s.qa.status == "passed" for s in built.slides)


def test_events_announce_the_cover_first_each_slide_once_then_done(tmp_path: Path) -> None:
    events: list[dict[str, object]] = []
    story = _story(3)
    _build(tmp_path, Studio(), story, on_event=events.append)
    kinds = [e["type"] for e in events]
    assert kinds[0] == "stage" and kinds[-1] == "done"
    ready = [str(e["slide_id"]) for e in events if e["type"] == "slide_ready"]
    assert ready[0] == story.slides[0].id and sorted(ready) == sorted(s.id for s in story.slides)
    assert all((tmp_path / f"{sid}.png").exists() for sid in ready)


def test_a_restart_pays_for_no_slide_twice(tmp_path: Path) -> None:
    story = _story(3)
    kept: dict[str, Kept] = {}
    first = _build(tmp_path, Studio(), story, on_final=lambda sid, k: kept.__setitem__(sid, k))
    assert sorted(kept) == sorted(s.id for s in story.slides)
    again = Studio()
    second = _build(tmp_path, again, story, prebuilt=kept)
    assert again.calls == []  # not even the art director
    assert [s.html for s in second.slides] == [s.html for s in first.slides]


def test_an_abort_keeps_what_is_done_and_starts_nothing_new(tmp_path: Path) -> None:
    done: list[str] = []
    transport = Studio()
    story = _story(4)
    built = _build(
        tmp_path,
        transport,
        story,
        on_final=lambda sid, k: done.append(sid),
        stop=lambda: len(done) >= 1,  # the user aborts once the cover is in
    )
    assert [s.id for s in built.slides] == [story.slides[0].id]
    assert transport.calls.count("compose") == 1


def test_a_picture_lands_where_the_art_director_asked(tmp_path: Path) -> None:
    theme = build_theme(look_for("img-test", words="a pitch", language="editorial"))
    transport = Studio()
    built = asyncio.run(
        studio.build(
            Seam(api_key="k", transport=transport, sleep=_no_sleep),
            _story(3),
            theme,
            model="m",
            title="A pitch",
            work_file=str(tmp_path / "qa.html"),
            shots_dir=str(tmp_path),
            budget_usd=1.0,
            image_model="img",
        )
    )
    assert transport.calls.count("image") == 1  # the fake director asks for one, on slide 2
    second = built.slides[1]
    assert '<img src="data:image/webp;base64,' in second.html
    assert "Absolutely no text anywhere" in transport.prompts[0]


def test_the_rhythm_rules_hold_whatever_the_plan_says() -> None:
    from engine.studio.direct import SlideDirection, rhythm

    flat = [
        SlideDirection(id=f"s{n}", hero="headline", ground="accent", image=False, idea="x")
        for n in range(6)
    ]
    fixed = [s.ground for s in rhythm(flat)]
    assert not any(fixed[i] == fixed[i - 1] == fixed[i - 2] for i in range(2, len(fixed)))
    assert "ink" in fixed and ({"ground", "surface"} & set(fixed))


def test_the_review_scores_ride_on_an_event(tmp_path: Path) -> None:
    events: list[dict[str, object]] = []
    _build(tmp_path, Studio(), _story(4), on_event=events.append)
    [review] = [e for e in events if e["type"] == "review"]
    scores = review["scores"]
    assert isinstance(scores, dict)
    assert set(scores) == {"consistency", "hierarchy", "detail", "readability", "innovation"}
