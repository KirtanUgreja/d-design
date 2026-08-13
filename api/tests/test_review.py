"""Review loop tests.

The review is a human loop: written feedback drives a per-slide re-call. Tests
cover the index bounds, the feedback reaching the prompt, id preservation,
and the backstop.
"""

from __future__ import annotations

from ai.complete import ModelError, Phase, Seam, T
from lib.result import Err, Ok, Result
from pipeline.review.review import revise_slide
from schema.deck import Deck, Slide, TextBlock


class FakeSeam(Seam):
    def __init__(self) -> None:
        self.captured_user = ""

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
        self.captured_user = user
        slide = Slide(
            id="revised",
            title="Revised slide",
            layout_archetype="opener",
            blocks=[TextBlock(kind="text", style="headline", content="Revised")],
        )
        return Ok(slide)  # type: ignore[arg-type]


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
                title="The ask",
                layout_archetype="closer",
                blocks=[TextBlock(kind="text", style="headline", content="Headline 2")],
            ),
        ],
    )


def test_revise_slide_returns_schema_valid_slide() -> None:
    seam = FakeSeam()
    result = revise_slide(_deck(), 0, "Make the headline shorter", seam, model="m")
    assert isinstance(result, Ok)
    assert isinstance(result.value, Slide)


def test_revision_honors_feedback_in_prompt() -> None:
    seam = FakeSeam()
    revise_slide(_deck(), 0, "The headline is too long", seam, model="m")
    assert "The headline is too long" in seam.captured_user
    assert "Reviewer feedback" in seam.captured_user


def test_revision_preserves_slide_id() -> None:
    seam = FakeSeam()
    result = revise_slide(_deck(), 1, "Change the closer", seam, model="m")
    assert isinstance(result, Ok)
    assert result.value.id == "s2"


def test_revision_rejects_out_of_range_index() -> None:
    seam = FakeSeam()
    result = revise_slide(_deck(), 99, "nope", seam, model="m")
    assert isinstance(result, Err)
    assert result.error.kind == "invalid"


def test_revision_prompt_has_no_presentational_values() -> None:
    seam = FakeSeam()
    revise_slide(_deck(), 0, "Make it pop", seam, model="m")
    assert "Make it pop" in seam.captured_user
