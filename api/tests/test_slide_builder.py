"""Slide-builder tests.

The core claim: each slide is generated individually, one call per slide, so
the deck cannot collapse onto a repeated frame. Tests cover the one-call-per-
slide invariant, per-slide distinctness of the prompts, the backstop, image
generation as a seam action, and id preservation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from ai.complete import ModelError, Phase, Seam, T
from ai.images import ImageError, ImageSeam
from lib.result import Err, Ok, Result, err
from pipeline.slide_builder.slide_builder import run_build
from schema.deck import Deck, ImageBlock, Slide, TextBlock
from schema.no_style import has_presentational_value


def _deck() -> Deck:
    return Deck(
        family_id="editorial-serif",
        slides=[
            Slide(
                id="s1",
                title="The problem",
                layout_archetype="opener",
                blocks=[TextBlock(kind="text", style="headline", content="Headline 1")],
            ),
            Slide(
                id="s2",
                title="The product",
                layout_archetype="split",
                blocks=[TextBlock(kind="text", style="headline", content="Headline 2")],
            ),
            Slide(
                id="s3",
                title="The ask",
                layout_archetype="closer",
                blocks=[
                    TextBlock(kind="text", style="headline", content="Headline 3"),
                    ImageBlock(
                        kind="image",
                        subject="A founder shaking hands",
                        role="hero",
                        alt="A founder shaking hands",
                    ),
                ],
            ),
        ],
    )


@dataclass
class FakeSeam(Seam):
    """A seam that returns a scripted slide per call and records the prompts."""

    calls: list[dict[str, str]] = field(default_factory=list)

    def complete(
        self,
        phase: Phase,
        schema: type[T],
        system: str,
        user: str,
        model: str,
        route: str = "openrouter/auto",
    ) -> Result[T, ModelError]:
        del phase, schema, model, route
        self.calls.append({"system": system, "user": user})
        # Echo the mapped spec's image blocks (if any) so the image path is
        # exercised; otherwise a plain generated slide. The heuristic is the
        # slide's subject, which only appears when the spec wanted an image.
        blocks: list[TextBlock | ImageBlock] = [
            TextBlock(kind="text", style="headline", content="Generated")
        ]
        if "A founder shaking hands" in user:
            blocks.append(
                ImageBlock(
                    kind="image",
                    subject="A founder shaking hands",
                    role="hero",
                    alt="A founder shaking hands",
                )
            )
        slide = Slide(
            id="generated",
            title="Generated slide",
            layout_archetype="opener",
            blocks=blocks,  # type: ignore[arg-type]  # list variance: TextBlock|ImageBlock vs SlideBlock
        )
        return Ok(slide)  # type: ignore[arg-type]  # schema=Slide for all calls


@dataclass
class FakeImageSeam(ImageSeam):
    """An image seam that returns a scripted data URI without network."""

    called: int = 0
    last_subject: str = ""
    last_rules: str = ""

    def generate(
        self, subject: str, visual_rules: str, model: str = "openai/dall-e-3"
    ) -> Result[str, ImageError]:
        del model
        self.called += 1
        self.last_subject = subject
        self.last_rules = visual_rules
        return Ok("data:image/png;base64,AAAA")


def test_one_call_per_slide() -> None:
    seam = FakeSeam()
    image_seam = FakeImageSeam()
    result = run_build(_deck(), seam, image_seam, model="m")
    assert isinstance(result, Ok)
    assert len(seam.calls) == 3  # three slides, three calls


def test_per_slide_prompts_are_distinct() -> None:
    seam = FakeSeam()
    image_seam = FakeImageSeam()
    run_build(_deck(), seam, image_seam, model="m")
    users = [c["user"] for c in seam.calls]
    assert len(set(users)) == 3  # each slide got its own prompt, none repeated


def test_prompt_carries_archetype_and_continuity() -> None:
    seam = FakeSeam()
    image_seam = FakeImageSeam()
    run_build(_deck(), seam, image_seam, model="m")
    second = seam.calls[1]["user"]
    assert "split" in second  # the archetype is in the prompt
    assert "The problem" in second  # previous slide's title for continuity


def test_prompt_has_no_presentational_values() -> None:
    seam = FakeSeam()
    image_seam = FakeImageSeam()
    run_build(_deck(), seam, image_seam, model="m")
    for c in seam.calls:
        assert not has_presentational_value(c["user"])


def test_image_blocks_trigger_image_seam() -> None:
    seam = FakeSeam()
    image_seam = FakeImageSeam()
    result = run_build(_deck(), seam, image_seam, model="m")
    assert isinstance(result, Ok)
    assert image_seam.called == 1
    assert image_seam.last_subject == "A founder shaking hands"
    # The visual rules are the family's axis tags (type/spacing/texture/...).
    assert "warm-ink" in image_seam.last_rules
    assert "paper" in image_seam.last_rules
    assert result.value.images["s3"].startswith("data:image/png;base64,")


def test_slide_ids_are_preserved() -> None:
    seam = FakeSeam()
    image_seam = FakeImageSeam()
    result = run_build(_deck(), seam, image_seam, model="m")
    assert isinstance(result, Ok)
    ids = [s.id for s in result.value.deck.slides]
    assert ids == ["s1", "s2", "s3"]


def test_backstop_rejects_presentational_value_in_slide() -> None:
    class BadSeam(FakeSeam):
        def complete(
            self,
            phase: Phase,
            schema: type[T],
            system: str,
            user: str,
            model: str,
            route: str = "openrouter/auto",
        ) -> Result[T, ModelError]:
            del phase, schema, system, user, model, route
            slide = Slide(
                id="generated",
                title="Slide in #333",
                layout_archetype="opener",
                blocks=[TextBlock(kind="text", style="headline", content="H")],
            )
            return Ok(slide)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="presentational"):
        run_build(_deck(), BadSeam(), FakeImageSeam(), model="m")


def test_build_failure_keeps_prior_slides() -> None:
    """A failing slide returns an error; it does not discard the deck (spec.md:
    "Failure at slide 6 of 8 keeps the five"). The orchestrator returns Err and
    the caller keeps what was built."""

    class FailOnSecond(FakeSeam):
        def complete(
            self,
            phase: Phase,
            schema: type[T],
            system: str,
            user: str,
            model: str,
            route: str = "openrouter/auto",
        ) -> Result[T, ModelError]:
            del phase, schema, system, model, route
            self.calls.append({"system": "", "user": user})
            if len(self.calls) == 2:
                return err(ModelError("refused", "model refused"))
            slide = Slide(
                id="generated",
                title="Generated",
                layout_archetype="opener",
                blocks=[TextBlock(kind="text", style="headline", content="Generated")],
            )
            return Ok(slide)  # type: ignore[arg-type]

    seam = FailOnSecond()
    result = run_build(_deck(), seam, FakeImageSeam(), model="m")
    assert isinstance(result, Err)
    assert result.error.kind == "refused"
    assert len(seam.calls) == 2  # the third slide was never attempted
