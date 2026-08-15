"""Slide-builder tests.

The core claim: each slide is generated individually, one call per slide, so
the deck cannot collapse onto a repeated frame. Phase 10: each call carries the
mapped layout structure and the family grammar, so the builder refines within
the grammar rather than picking a frame. Tests cover the one-call-per-slide
invariant, per-slide distinctness of the prompts, the backstop, image
generation as a seam action, and id preservation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pytest

from ai.complete import ModelError, Phase, Seam, T
from ai.images import ImageError, ImageSeam
from lib.result import Err, Ok, Result, err
from pipeline.slide_builder.slide_builder import run_build
from schema.deck import (
    Deck,
    ImageBlock,
    LayoutRegion,
    LayoutStructure,
    Slide,
    TextBlock,
)
from schema.no_style import has_presentational_value

Role = Literal["headline", "body", "media", "stats", "quote", "chart", "aside"]


def _layout(*roles: Role) -> LayoutStructure:
    """A full-span layout legal in the literary grammar (editorial-serif)."""
    return LayoutStructure(regions=[LayoutRegion(role=role, span="full") for role in roles])


def _deck() -> Deck:
    return Deck(
        family_id="editorial-serif",
        slides=[
            Slide(
                id="s1",
                title="The problem",
                layout=_layout("headline", "body"),
                blocks=[
                    TextBlock(kind="text", style="headline", content="Headline 1"),
                    TextBlock(kind="text", style="body", content="Body 1"),
                ],
            ),
            Slide(
                id="s2",
                title="The product",
                layout=_layout("headline", "body"),
                blocks=[
                    TextBlock(kind="text", style="headline", content="Headline 2"),
                    TextBlock(kind="text", style="body", content="Body 2"),
                ],
            ),
            Slide(
                id="s3",
                title="The ask",
                layout=_layout("headline", "media"),
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
        image: str | None = None,
    ) -> Result[T, ModelError]:
        del phase, schema, model, route, image
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
            layout = _layout("headline", "media")
        else:
            blocks.append(TextBlock(kind="text", style="body", content="Generated body"))
            layout = _layout("headline", "body")
        slide = Slide(
            id="generated",
            title="Generated slide",
            layout=layout,
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


def test_prompt_carries_layout_and_continuity() -> None:
    seam = FakeSeam()
    image_seam = FakeImageSeam()
    run_build(_deck(), seam, image_seam, model="m")
    second = seam.calls[1]["user"]
    assert "headline" in second  # the layout roles are in the prompt
    assert "The problem" in second  # previous slide's title for continuity
    assert "legal region roles" in second  # the grammar is in the prompt


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
            image: str | None = None,
        ) -> Result[T, ModelError]:
            del phase, schema, system, user, model, route, image
            slide = Slide(
                id="generated",
                title="Slide in #333",
                layout=_layout("headline", "body"),
                blocks=[
                    TextBlock(kind="text", style="headline", content="H"),
                    TextBlock(kind="text", style="body", content="B"),
                ],
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
            image: str | None = None,
        ) -> Result[T, ModelError]:
            del phase, schema, system, model, route, image
            self.calls.append({"system": "", "user": user})
            if len(self.calls) == 2:
                return err(ModelError("refused", "model refused"))
            slide = Slide(
                id="generated",
                title="Generated",
                layout=_layout("headline", "body"),
                blocks=[
                    TextBlock(kind="text", style="headline", content="Generated"),
                    TextBlock(kind="text", style="body", content="Generated body"),
                ],
            )
            return Ok(slide)  # type: ignore[arg-type]

    seam = FailOnSecond()
    result = run_build(_deck(), seam, FakeImageSeam(), model="m")
    assert isinstance(result, Err)
    assert result.error.kind == "refused"
    assert len(seam.calls) == 2  # the third slide was never attempted
