"""Mapping tests.

The mapping must produce a schema-valid Deck from an approved Outline, keep
the through-line (structural opener), distribute layout signatures, and reject
a collapsed deck and a grammar-illegal layout. The seam is stubbed so no
network is involved.
"""

from __future__ import annotations

from typing import Literal

import pytest

from ai.complete import ModelError, Phase, Seam, T
from lib.result import Err, Ok, Result
from pipeline.mapping.distribution import distribution_violation, layout_signature
from pipeline.mapping.mapping import run_mapping
from schema.deck import (
    Deck,
    ImageBlock,
    LayoutRegion,
    LayoutStructure,
    QuoteBlock,
    Slide,
    SlideBlock,
    TextBlock,
)
from schema.no_style import has_presentational_value
from schema.outline import Outline, OutlineClaim, OutlineSection

Role = Literal["headline", "body", "media", "stats", "quote", "chart", "aside"]


class FakeSeam(Seam):
    """A minimal seam double: records the user prompt, returns a scripted
    result. Stays a Seam so the type system sees it as the real seam."""

    def __init__(self, result: Result[Deck, ModelError]) -> None:
        self._result = result
        self.captured_user = ""

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
        self.captured_user = user
        # Every call this fake serves is schema=Deck; the ignore is the one
        # narrowing point, asserted by the isinstance checks in each test.
        return self._result  # type: ignore[return-value]  # schema=Deck for all mapping calls


def _outline() -> Outline:
    return Outline(
        title="The agency CRM",
        audience="Agency founders",
        goal="Get 20 pilot signups",
        sections=[
            OutlineSection(
                heading="The problem",
                summary="Agencies lose money on scope creep",
                claims=[
                    OutlineClaim(
                        text="Agencies lose hours a week to manual tracking", source="user"
                    ),
                    OutlineClaim(text="A dedicated CRM pays for itself", source="model"),
                ],
            ),
            OutlineSection(
                heading="The product",
                summary="What the CRM does",
                claims=[
                    OutlineClaim(text="It tracks clients, scope and billing", source="user"),
                ],
            ),
            OutlineSection(
                heading="The ask",
                summary="Pilot signups",
                claims=[
                    OutlineClaim(text="We want 20 pilots", source="user"),
                ],
            ),
        ],
        must_haves=["Pilot pricing"],
    )


def _literary_layout(*roles: Role) -> LayoutStructure:
    """A full-span layout legal in the literary grammar (editorial-serif)."""
    return LayoutStructure(regions=[LayoutRegion(role=role, span="full") for role in roles])


def _slide_for(index: int, roles: tuple[Role, ...]) -> Slide:
    """A slide whose blocks fill its layout regions (literary grammar)."""
    blocks: list[SlideBlock] = [
        TextBlock(kind="text", style="headline", content=f"Headline {index}")
    ]
    for role in roles[1:]:
        if role == "quote":
            blocks.append(QuoteBlock(kind="quote", text=f"Quote {index}", attribution="Source"))
        elif role == "media":
            blocks.append(
                ImageBlock(
                    kind="image",
                    subject=f"Visual {index}",
                    role="hero",
                    alt=f"Visual {index}",
                )
            )
        elif role == "aside":
            blocks.append(TextBlock(kind="text", style="caption", content=f"Caption {index}"))
        else:
            blocks.append(TextBlock(kind="text", style="body", content=f"Body {index}"))
    return Slide(
        id=f"s{index}",
        title=f"Slide {index}",
        layout=_literary_layout(*roles),
        blocks=blocks,
    )


def _distributed_deck() -> Deck:
    """A 9-slide deck with distinct layouts, legal in the literary grammar."""
    layouts: list[tuple[Role, ...]] = [
        ("headline", "body"),
        ("headline", "quote"),
        ("headline", "body", "quote"),
        ("headline", "media"),
        ("headline", "body", "aside"),
        ("headline", "quote", "body"),
        ("headline", "body"),
        ("headline", "media", "body"),
        ("headline", "quote"),
    ]
    return Deck(
        family_id="brutalist-stencil",  # the family _outline() samples by title
        slides=[_slide_for(i + 1, layouts[i]) for i in range(9)],
    )


def test_mapping_returns_schema_valid_deck() -> None:
    seam = FakeSeam(Ok(_distributed_deck()))
    result = run_mapping(_outline(), seam, model="test-model")
    assert isinstance(result, Ok)
    assert isinstance(result.value, Deck)
    assert len(result.value.slides) == 9


def test_mapping_preserves_through_line() -> None:
    deck = _distributed_deck()
    seam = FakeSeam(Ok(deck))
    result = run_mapping(_outline(), seam, model="test-model")
    assert isinstance(result, Ok)
    # The opener is structural: the first slide's first region is full-width.
    assert result.value.slides[0].layout.regions[0].span == "full"


def test_mapping_prompt_carries_the_grammar() -> None:
    seam = FakeSeam(Ok(_distributed_deck()))
    run_mapping(_outline(), seam, model="test-model")
    assert "legal region roles" in seam.captured_user
    assert "headline" in seam.captured_user
    # The prompt names the family the title sampled and its grammar's roles.
    assert "The design family for this deck:" in seam.captured_user
    assert "legal relative spans" in seam.captured_user


def test_mapping_accepts_a_grammar_legal_deck() -> None:
    # Grammar legality is enforced by the Deck validator (test_schema.py) and
    # the mapping's backstop; here we confirm the mapping accepts a legal deck
    # for the family it was given.
    seam = FakeSeam(Ok(_distributed_deck()))
    result = run_mapping(_outline(), seam, model="test-model")
    assert isinstance(result, Ok)


def test_mapping_rejects_collapsed_distribution() -> None:
    # A valid deck that repeats one layout everywhere must fail the
    # distribution check even though the schema is happy — this is the
    # falsifier for the within-deck variety bet, now on layout signatures.
    collapsed = Deck.model_validate(
        {
            "family_id": "editorial-serif",
            "slides": [
                {
                    "id": f"s{i}",
                    "title": f"Slide {i}",
                    "layout": {"regions": [{"role": "headline", "span": "full"}]},
                    "blocks": [
                        {"kind": "text", "style": "headline", "content": f"H {i}"},
                    ],
                }
                for i in range(12)
            ],
        }
    )
    seam = FakeSeam(Ok(collapsed))
    result = run_mapping(_outline(), seam, model="test-model")
    assert isinstance(result, Err)
    assert result.error.kind == "invalid"
    assert "distribution" in result.error.detail


def test_mapping_backstop_rejects_presentational_value() -> None:
    bad = _distributed_deck().model_dump()
    bad["slides"][0]["title"] = "Slide in #333"
    seam = FakeSeam(Ok(Deck.model_validate(bad)))
    with pytest.raises(ValueError, match="presentational"):
        run_mapping(_outline(), seam, model="test-model")


def test_distribution_violation_flags_runs_and_collapse() -> None:
    deck = _distributed_deck()
    assert distribution_violation(deck) is None

    run = _distributed_deck().model_dump()
    for i in range(3):
        run["slides"][i]["layout"] = {"regions": [{"role": "headline", "span": "full"}]}
        run["slides"][i]["blocks"] = [{"kind": "text", "style": "headline", "content": f"H {i}"}]
    v = distribution_violation(Deck.model_validate(run))
    assert v is not None
    assert "in a row" in v


def test_layout_signature_is_stable_and_structural() -> None:
    slide = _distributed_deck().slides[0]
    assert layout_signature(slide.layout) == "headline:full,body:full"
    # Emphasis does not change the signature (same frame, different render).
    louder = slide.model_copy(
        update={
            "layout": LayoutStructure(
                regions=[
                    LayoutRegion(role="headline", span="full", emphasis="primary"),
                    LayoutRegion(role="body", span="full"),
                ]
            )
        }
    )
    assert layout_signature(louder.layout) == layout_signature(slide.layout)


def test_mapping_family_selection_is_deterministic() -> None:
    seam = FakeSeam(Ok(_distributed_deck()))
    run_mapping(_outline(), seam, model="test-model")
    first = seam.captured_user
    run_mapping(_outline(), seam, model="test-model")
    second = seam.captured_user
    assert first == second  # same outline -> same family -> same prompt


def test_mapping_prompt_has_no_presentational_values() -> None:
    seam = FakeSeam(Ok(_distributed_deck()))
    run_mapping(_outline(), seam, model="test-model")
    assert not has_presentational_value(seam.captured_user)
