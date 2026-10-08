"""References in the compose path (phase 39 -> Verify): the prompt carries
the slide's reference and none of the retired house style, and the ladder
falls back to the reference filled by code before the code layout."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from benchtools import files
from engine import Seam, Storyline, pipeline
from engine.compose import author, references
from engine.design.sampler import look_for
from engine.design.theme import build
from tests.test_ladder import AlwaysBroken, _no_sleep

SWISS = build(look_for("refs-test", words="a board update", language="swiss"))


@dataclass
class Recorder:
    """Records every prompt and answers with an unusable reply."""

    prompts: list[str] = field(default_factory=list)

    async def post(self, url: str, *, json: object, headers: dict[str, str]) -> httpx.Response:
        assert isinstance(json, dict)
        self.prompts.append("\n".join(str(m["content"]) for m in json["messages"]))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "no blocks"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.001},
            },
        )


def _story(n: int) -> Storyline:
    outline = files.load("pitch-devtools").outline
    assert outline is not None
    return outline.model_copy(update={"slides": outline.slides[:n]})


def test_every_compose_prompt_carries_its_reference_and_no_house_style(tmp_path: Path) -> None:
    recorder = Recorder()
    asyncio.run(
        pipeline.build(
            Seam(api_key="k", transport=recorder, sleep=_no_sleep),
            _story(2),
            SWISS,
            model="m",
            title="t",
            work_file=str(tmp_path / "qa.html"),
            shots_dir=str(tmp_path),
            budget_usd=1.0,
        )
    )
    assert recorder.prompts
    cover = next(r for r in references.load_all() if r.id == "swiss/cover-1")
    assert any(cover.html in p for p in recorder.prompts)
    for prompt in recorder.prompts:
        assert "REFERENCE" in prompt
        assert "Visual language: Swiss grid" in prompt
        for retired in ("COMPOSITION TARGET", "```ideas", "ART DIRECTION", "least typical"):
            assert retired not in prompt
        assert "dd-shape kind" not in prompt  # Swiss does not use shapes


def test_a_language_with_shapes_is_told_how_to_use_them() -> None:
    assert "<dd-shape kind" in author.rules(shapes=True)
    assert "No dd-shape" in author.rules(shapes=False)


def test_an_unusable_answer_falls_back_to_the_reference_filled(tmp_path: Path) -> None:
    built = asyncio.run(
        pipeline.build(
            Seam(api_key="k", transport=Recorder(), sleep=_no_sleep),
            _story(1),
            SWISS,
            model="m",
            title="t",
            work_file=str(tmp_path / "qa.html"),
            shots_dir=str(tmp_path),
            budget_usd=1.0,
        )
    )
    cover = built.slides[0]
    assert cover.origin == "reference"
    assert cover.reference == "swiss/cover-1"
    assert cover.qa.status == "passed"


def test_a_slide_still_broken_after_repairs_takes_the_reference_before_code(
    tmp_path: Path,
) -> None:
    transport = AlwaysBroken()
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
        )
    )
    assert transport.calls.count("repair") == pipeline.REPAIR_ROUNDS + 1
    assert built.slides[0].origin == "reference"
    assert built.slides[0].qa.status == "passed"


def test_fill_without_an_image_removes_the_slot() -> None:
    ref = references.Reference(
        id="x/cover-1",
        language="x",
        shape="cover",
        idea="",
        fields=frozenset({"headline"}),
        image="half",
        variants=(),
        html='<section class="s"><dd-image aspect="3:2" class="i"></dd-image>'
        '<h1 data-field="headline"></h1></section>',
        css="",
    )
    assert "<dd-image" in references.fill(ref, {"headline": "Hi"})
    assert "<dd-image" not in references.fill(ref, {"headline": "Hi"}, image=False)
    assert "Hi" in references.fill(ref, {"headline": "Hi"}, image=False)
