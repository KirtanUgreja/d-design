"""The repair ladder, offline (docs/v4/design-engine.md -> Repair ladder):
at most two repair rounds, then the code-built layout from the slide's target,
then the novelty gate; every slide that leaves the pipeline is measured clean
or flagged."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from benchtools import files
from engine import Seam, pipeline
from engine.compose import author
from engine.compose.archive import Archive
from engine.compose.exemplars import load_all
from engine.design.theme import THEMES


@dataclass
class AlwaysTheSame:
    """Answers every compose with the same clean column: every slide comes
    out with one composition, so the novelty gate must notice."""

    calls: list[str] = field(default_factory=list)

    async def post(self, url: str, *, json: object, headers: dict[str, str]) -> httpx.Response:
        assert isinstance(json, dict)
        user = str(json["messages"][-1]["content"])
        self.calls.append("steered" if "too close" in user else "compose")
        names = [
            line.split(":")[0].strip("- ").strip()
            for line in user.splitlines()
            if line.startswith("- ") and ':"' in line.replace(': "', ':"')
        ]
        body = "".join(f'<p class="x" data-field="{n}">{_text(user, n)}</p>' for n in names)
        answer = (
            "```ideas\none\n```\n"
            f'```html\n<section class="s"><div class="c">{body}</div></section>\n```\n'
            "```css\n.c{position:absolute;left:160px;top:160px;width:1200px;display:grid;"
            "gap:var(--s-3)}.x{font-size:var(--t-h2);color:var(--c-ink)}\n```"
        )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": answer}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.001},
            },
        )


@dataclass
class AlwaysBroken:
    """Answers every compose and repair with a slide that lints clean but
    puts its text off the canvas, so QA fails it every time."""

    calls: list[str] = field(default_factory=list)

    async def post(self, url: str, *, json: object, headers: dict[str, str]) -> httpx.Response:
        assert isinstance(json, dict)
        user = str(json["messages"][-1]["content"])
        names = [
            line.split(":")[0].strip("- ").strip()
            for line in user.splitlines()
            if line.startswith("- ") and ':"' in line.replace(': "', ':"')
        ]
        self.calls.append("repair" if "measured" in user else "compose")
        body = "".join(f'<p class="x" data-field="{n}">{_text(user, n)}</p>' for n in names)
        answer = (
            f'```html\n<section class="s">{body}</section>\n```\n'
            "```css\n.x{position:absolute;left:1800px;top:500px;width:900px;"
            "font-size:var(--t-body)}\n```"
        )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": answer}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.001},
            },
        )


def _text(user: str, name: str) -> str:
    for line in user.splitlines():
        if line.startswith(f"- {name}: "):
            return str(json.loads(line.split(": ", 1)[1]))
    return ""


async def _no_sleep(_: float) -> None:
    return None


def test_repairs_a_fresh_attempt_then_the_code_built_layout(tmp_path: Path) -> None:
    outline = files.load("pitch-devtools").outline
    assert outline is not None
    story = outline.model_copy(update={"slides": outline.slides[:4]})
    transport = AlwaysBroken()
    seam = Seam(api_key="k", transport=transport, sleep=_no_sleep)
    built = asyncio.run(
        pipeline.build(
            seam,
            story,
            THEMES["ledger"],
            model="m",
            title="t",
            work_file=str(tmp_path / "qa.html"),
            shots_dir=str(tmp_path),
            budget_usd=1.0,
        )
    )
    assert transport.calls.count("compose") == 4 * 2  # the first, then one fresh attempt
    assert transport.calls.count("repair") == 4 * (pipeline.REPAIR_ROUNDS + 1)
    assert {s.origin for s in built.slides} == {"fallback"}
    assert all(s.qa.status == "passed" for s in built.slides), [
        (s.id, s.origin, [d.code for d in s.qa.errors]) for s in built.slides
    ]
    assert all(s.attempts == 1 + pipeline.REPAIR_ROUNDS + 2 for s in built.slides)


def test_the_budget_stops_every_call_once_it_is_spent(tmp_path: Path) -> None:
    outline = files.load("pitch-devtools").outline
    assert outline is not None
    story = outline.model_copy(update={"slides": outline.slides[:3]})
    transport = AlwaysBroken()
    seam = Seam(api_key="k", transport=transport, sleep=_no_sleep)
    built = asyncio.run(
        pipeline.build(
            seam,
            story,
            THEMES["ledger"],
            model="m",
            title="t",
            work_file=str(tmp_path / "qa.html"),
            shots_dir=str(tmp_path),
            budget_usd=0.0025,
        )
    )
    # Fails closed: no call starts once the cap is reached (each costs 0.001),
    # and every slide is still delivered, by code where the model was cut off.
    assert len(transport.calls) == 3
    assert all(s.qa.status == "passed" for s in built.slides)


def test_events_announce_each_slide_once_then_done(tmp_path: Path) -> None:
    outline = files.load("pitch-devtools").outline
    assert outline is not None
    story = outline.model_copy(update={"slides": outline.slides[:3]})
    events: list[dict[str, object]] = []
    asyncio.run(
        pipeline.build(
            Seam(api_key="k", transport=AlwaysBroken(), sleep=_no_sleep),
            story,
            THEMES["ledger"],
            model="m",
            title="t",
            work_file=str(tmp_path / "qa.html"),
            shots_dir=str(tmp_path),
            budget_usd=1.0,
            on_event=events.append,
        )
    )
    kinds = [e["type"] for e in events]
    assert kinds[0] == "stage" and kinds[-1] == "done"
    ready = [str(e["slide_id"]) for e in events if e["type"] == "slide_ready"]
    assert sorted(ready) == sorted(s.id for s in story.slides)
    times = [float(str(e["t"])) for e in events]
    assert times == sorted(times)
    assert all((tmp_path / f"{sid}.png").exists() for sid in ready)


def test_near_repeats_get_one_steered_retry_then_a_warning(tmp_path: Path) -> None:
    outline = files.load("pitch-devtools").outline
    assert outline is not None
    story = outline.model_copy(update={"slides": outline.slides[1:6]})
    transport = AlwaysTheSame()
    archive = Archive()
    built = asyncio.run(
        pipeline.build(
            Seam(api_key="k", transport=transport, sleep=_no_sleep),
            story,
            THEMES["ledger"],
            model="m",
            title="t",
            work_file=str(tmp_path / "qa.html"),
            shots_dir=str(tmp_path),
            budget_usd=1.0,
            archive=archive,
        )
    )
    # every slide is clean, so the gate measured each; the same column repeats
    assert all(s.qa.status == "passed" for s in built.slides)
    assert built.novelty_retries >= 1
    assert transport.calls.count("steered") == built.novelty_retries
    assert built.novelty_retries <= len(story.slides)  # one retry at most, never a loop
    assert built.near_repeats >= 1
    assert len(archive.entries) == len(story.slides)  # accepted compositions join the archive


def test_no_compose_prompt_carries_an_exemplar() -> None:
    text = author.prefix(THEMES["ledger"])
    assert "EXEMPLAR" not in text.upper()
    for e in load_all():
        assert e.html[:80] not in text


def test_the_cover_is_announced_first(tmp_path: Path) -> None:
    outline = files.load("pitch-devtools").outline
    assert outline is not None
    story = outline.model_copy(update={"slides": outline.slides[:4]})
    events: list[dict[str, object]] = []
    asyncio.run(
        pipeline.build(
            Seam(api_key="k", transport=AlwaysTheSame(), sleep=_no_sleep),
            story,
            THEMES["ledger"],
            model="m",
            title="t",
            work_file=str(tmp_path / "qa.html"),
            shots_dir=str(tmp_path),
            budget_usd=1.0,
            on_event=events.append,
        )
    )
    ready = [e["slide_id"] for e in events if e["type"] == "slide_ready"]
    assert ready[0] == story.slides[0].id
