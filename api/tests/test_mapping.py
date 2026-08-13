"""Mapping tests.

The mapping must produce a schema-valid Deck from an approved Outline, keep
the through-line, distribute layout archetypes, and reject a collapsed deck.
The seam is stubbed so no network is involved.
"""

from __future__ import annotations

import pytest

from ai.complete import ModelError, Phase, Seam, T
from lib.result import Err, Ok, Result
from pipeline.mapping.distribution import distribution_violation
from pipeline.mapping.mapping import run_mapping
from schema.deck import Deck, Slide, TextBlock
from schema.no_style import has_presentational_value
from schema.outline import Outline, OutlineClaim, OutlineSection


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
    ) -> Result[T, ModelError]:
        del phase, schema, system, model, route
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


def _distributed_deck() -> Deck:
    """A 9-slide deck with archetypes distributed enough to pass the check."""
    archetypes = [
        "opener",
        "statement",
        "section",
        "split",
        "columns",
        "list",
        "stats",
        "quote",
        "closer",
    ]
    return Deck(
        family_id="editorial-serif",
        slides=[
            Slide(
                id=f"s{i + 1}",
                title=f"Slide {i + 1}",
                layout_archetype=archetypes[i],
                blocks=[
                    TextBlock(kind="text", style="headline", content=f"Headline {i + 1}"),
                    TextBlock(kind="text", style="body", content=f"Body {i + 1}"),
                ],
            )
            for i in range(9)
        ],
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
    # The opener is first and the closer is last.
    assert result.value.slides[0].layout_archetype == "opener"
    assert result.value.slides[-1].layout_archetype == "closer"


def test_mapping_rejects_unknown_archetype() -> None:
    bad = _distributed_deck().model_dump()
    bad["slides"][0]["layout_archetype"] = "invented-layout"
    seam = FakeSeam(Ok(Deck.model_validate(bad)))
    result = run_mapping(_outline(), seam, model="test-model")
    assert isinstance(result, Err)
    assert result.error.kind == "invalid"


def test_mapping_rejects_collapsed_distribution() -> None:
    # A valid deck that uses the same archetype everywhere must fail the
    # distribution check even though the schema is happy — this is the
    # falsifier for the within-deck variety bet.
    collapsed = Deck.model_validate(
        {
            "family_id": "editorial-serif",
            "slides": [
                {
                    "id": f"s{i}",
                    "title": f"Slide {i}",
                    "layout_archetype": "statement",
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
        run["slides"][i]["layout_archetype"] = "statement"
    v = distribution_violation(Deck.model_validate(run))
    assert v is not None
    assert "in a row" in v


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
