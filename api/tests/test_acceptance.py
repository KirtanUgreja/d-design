"""Acceptance tests — the variety metric is the falsifier.

The fingerprint must distinguish two genuinely different decks, detect a
collapsed deck, and the summary must fail on a single violation. Phase 10: the
per-slide dimension is the layout signature (generated structure), not a
catalogue archetype id. These are the "53% identical" measurement made into a
gate.
"""

from __future__ import annotations

from typing import Literal

from ai.complete import ModelError, Phase, Seam, T
from lib.result import Ok, Result
from pipeline.acceptance.acceptance import acceptance_summary, run_acceptance_brief
from pipeline.acceptance.briefs import GOLDEN_BRIEFS
from pipeline.acceptance.fingerprint import (
    chart_type_ratio,
    deck_fingerprint,
    distribution_ratio,
)
from schema.deck import (
    ChartBlock,
    ChartSeries,
    Deck,
    ImageBlock,
    LayoutRegion,
    LayoutStructure,
    QuoteBlock,
    Slide,
    SlideBlock,
    TextBlock,
)
from schema.outline import Brief, Outline, OutlineClaim, OutlineSection

Role = Literal["headline", "body", "media", "stats", "quote", "chart", "aside"]


def _layout(*roles: Role) -> LayoutStructure:
    """A full-span layout legal in the literary grammar (editorial-serif)."""
    return LayoutStructure(regions=[LayoutRegion(role=role, span="full") for role in roles])


def _slide(index: int, roles: tuple[Role, ...]) -> Slide:
    """A slide whose blocks fill its layout regions (literary grammar)."""
    blocks: list[SlideBlock] = [
        TextBlock(kind="text", style="headline", content=f"Headline {index}")
    ]
    for role in roles[1:]:
        if role == "quote":
            blocks.append(QuoteBlock(kind="quote", text=f"Quote {index}", attribution="S"))
        elif role == "media":
            blocks.append(
                ImageBlock(
                    kind="image",
                    subject=f"Visual {index}",
                    role="hero",
                    alt=f"Visual {index}",
                )
            )
        else:
            blocks.append(TextBlock(kind="text", style="body", content=f"Body {index}"))
    return Slide(
        id=f"s{index}",
        title=f"Slide {index}",
        layout=_layout(*roles),
        blocks=blocks,
    )


class FakeSeam(Seam):
    """A seam that returns a scripted outline for interview and a scripted deck
    for mapping. Deterministic per family, so the fingerprint check is
    meaningful."""

    def __init__(self, layouts: list[tuple[Role, ...]], family: str = "editorial-serif") -> None:
        self.layouts = layouts
        self.family = family

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
        del system, user, model, route, image
        if phase == "interview":
            outline = Outline(
                title="A brief",
                audience="People",
                goal="Something",
                sections=[
                    OutlineSection(
                        heading="The idea",
                        summary="A deck about the idea",
                        claims=[OutlineClaim(text="The idea is good", source="user")],
                    )
                ],
                must_haves=[],
            )
            return Ok(outline)  # type: ignore[arg-type]
        # mapping
        deck = Deck(
            family_id=self.family,
            slides=[_slide(i + 1, roles) for i, roles in enumerate(self.layouts)],
        )
        return Ok(deck)  # type: ignore[arg-type]


def _brief() -> Brief:
    return GOLDEN_BRIEFS[0]


def test_fingerprint_is_deterministic() -> None:
    deck = Deck(
        family_id="editorial-serif",
        slides=[_slide(1, ("headline", "body"))],
    )
    assert deck_fingerprint(deck) == deck_fingerprint(deck)


def test_fingerprint_distinguishes_families() -> None:
    a = deck_fingerprint(
        Deck(family_id="editorial-serif", slides=[_slide(1, ("headline", "body"))])
    )
    b = deck_fingerprint(
        Deck(family_id="brutalist-stencil", slides=[_slide(1, ("headline", "body"))])
    )
    assert a != b


def test_fingerprint_distinguishes_layout_sequences() -> None:
    a = deck_fingerprint(
        Deck(family_id="editorial-serif", slides=[_slide(1, ("headline", "body"))])
    )
    b = deck_fingerprint(
        Deck(family_id="editorial-serif", slides=[_slide(1, ("headline", "quote"))])
    )
    assert a != b


def test_distribution_ratio_measures_collapse() -> None:
    varied_layouts: list[tuple[Role, ...]] = [
        ("headline", "body"),
        ("headline", "quote"),
        ("headline", "media"),
        ("headline",),
    ]
    varied = Deck(
        family_id="editorial-serif",
        slides=[_slide(i, roles) for i, roles in enumerate(varied_layouts)],
    )
    # 1 - (1/4): every slide distinct means most_common = 1 of 4.
    assert distribution_ratio(varied) == 0.75

    collapsed = Deck(
        family_id="editorial-serif",
        slides=[_slide(i, ("headline", "body")) for i in range(6)],
    )
    assert distribution_ratio(collapsed) == 0.0  # all one frame


def test_acceptance_brief_passes_with_varied_deck() -> None:
    seam = FakeSeam(
        [
            ("headline", "body"),
            ("headline", "quote"),
            ("headline", "body", "quote"),
            ("headline", "media"),
            ("headline", "quote", "body"),
            ("headline", "body"),
        ]
    )
    result = run_acceptance_brief(_brief(), seam, model="m")
    assert isinstance(result, Ok)
    assert result.value.distribution_ratio >= 0.4


def test_summary_fails_on_fingerprint_collapse() -> None:
    # Two briefs that map to identical decks (same family, same layouts).
    # Alternating two layouts passes the consecutive-check but collapses on
    # the fingerprint (the two briefs are indistinguishable).
    seam = FakeSeam([("headline", "body"), ("headline", "quote")] * 4)
    r1 = run_acceptance_brief(_brief(), seam, model="m")
    r2 = run_acceptance_brief(_brief(), seam, model="m")
    assert isinstance(r1, Ok) and isinstance(r2, Ok)
    passed, report = acceptance_summary([r1.value, r2.value])
    assert not passed
    assert "FINGERPRINT COLLAPSE" in report


def test_ratio_backstop_flags_a_thin_deck_directly() -> None:
    # The acceptance ratio backstop exists for decks that slip past the mapping
    # gate; here we construct one directly (bypassing mapping) and assert the
    # summary flags it.
    from pipeline.acceptance.acceptance import AcceptanceResult, acceptance_summary
    from pipeline.acceptance.fingerprint import distribution_ratio

    collapsed = Deck(
        family_id="editorial-serif",
        slides=[
            Slide(
                id=f"s{i}",
                title="x",
                layout=_layout("headline", "body"),
                blocks=[
                    TextBlock(kind="text", style="headline", content="H"),
                    TextBlock(kind="text", style="body", content="B"),
                ],
            )
            for i in range(6)
        ],
    )
    assert distribution_ratio(collapsed) == 0.0
    result = AcceptanceResult(
        brief=_brief(),
        deck=collapsed,
        fingerprint="x",
        distribution_ratio=distribution_ratio(collapsed),
        chart_ratio=1.0,  # no charts, so no chart collapse
    )
    passed, report = acceptance_summary([result])
    assert not passed
    assert "DISTRIBUTION COLLAPSE" in report


def test_summary_flags_chart_collapse() -> None:
    # A deck that draws the same chart type everywhere must fail the chart
    # variety check (phase 11 — chart variety is part of the fingerprint).
    from pipeline.acceptance.acceptance import AcceptanceResult, acceptance_summary

    collapsed_charts = Deck(
        family_id="scientific",  # lab grammar allows the chart role
        slides=[
            Slide(
                id=f"s{i}",
                title="x",
                layout=_layout("headline", "chart"),
                blocks=[
                    TextBlock(kind="text", style="headline", content="H"),
                    ChartBlock(
                        kind="chart",
                        chart_type="bar",
                        title="Growth",
                        series=[
                            ChartSeries(label="Q1", value=1.0),
                            ChartSeries(label="Q2", value=2.0),
                        ],
                    ),
                ],
            )
            for i in range(3)
        ],
    )
    assert chart_type_ratio(collapsed_charts) == 0.0
    result = AcceptanceResult(
        brief=_brief(),
        deck=collapsed_charts,
        fingerprint="x",
        distribution_ratio=distribution_ratio(collapsed_charts),
        chart_ratio=chart_type_ratio(collapsed_charts),
    )
    passed, report = acceptance_summary([result])
    assert not passed
    assert "CHART COLLAPSE" in report


def test_golden_briefs_are_all_valid() -> None:
    assert len(GOLDEN_BRIEFS) >= 5
    for brief in GOLDEN_BRIEFS:
        assert brief.topic
        assert 1 <= brief.slide_count <= 40
