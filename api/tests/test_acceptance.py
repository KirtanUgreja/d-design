"""Acceptance tests — the variety metric is the falsifier.

The fingerprint must distinguish two genuinely different decks, detect a
collapsed deck, and the summary must fail on a single violation. These are the
"53% identical" measurement made into a gate.
"""

from __future__ import annotations

from ai.complete import ModelError, Phase, Seam, T
from lib.result import Ok, Result
from pipeline.acceptance.acceptance import acceptance_summary, run_acceptance_brief
from pipeline.acceptance.briefs import GOLDEN_BRIEFS
from pipeline.acceptance.fingerprint import deck_fingerprint, distribution_ratio
from schema.deck import Deck, Slide, TextBlock
from schema.outline import Brief, Outline, OutlineClaim, OutlineSection


class FakeSeam(Seam):
    """A seam that returns a scripted outline for interview and a scripted deck
    for mapping. Deterministic per family, so the fingerprint check is
    meaningful."""

    def __init__(self, archetypes: list[str], family: str = "editorial-serif") -> None:
        self.archetypes = archetypes
        self.family = family

    def complete(
        self,
        phase: Phase,
        schema: type[T],
        system: str,
        user: str,
        model: str,
        route: str = "openrouter/auto",
    ) -> Result[T, ModelError]:
        del system, user, model, route
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
            slides=[
                Slide(
                    id=f"s{i + 1}",
                    title=f"Slide {i + 1}",
                    layout_archetype=a,
                    blocks=[
                        TextBlock(kind="text", style="headline", content=f"Headline {i + 1}"),
                    ],
                )
                for i, a in enumerate(self.archetypes)
            ],
        )
        return Ok(deck)  # type: ignore[arg-type]


def _brief() -> Brief:
    return GOLDEN_BRIEFS[0]


def test_fingerprint_is_deterministic() -> None:
    deck = Deck(
        family_id="editorial-serif",
        slides=[
            Slide(
                id="s1",
                title="a",
                layout_archetype="opener",
                blocks=[TextBlock(kind="text", style="headline", content="A")],
            )
        ],
    )
    assert deck_fingerprint(deck) == deck_fingerprint(deck)


def test_fingerprint_distinguishes_families() -> None:
    a = deck_fingerprint(
        Deck(
            family_id="editorial-serif",
            slides=[
                Slide(
                    id="s1",
                    title="a",
                    layout_archetype="opener",
                    blocks=[TextBlock(kind="text", style="headline", content="A")],
                )
            ],
        )
    )
    b = deck_fingerprint(
        Deck(
            family_id="brutalist-stencil",
            slides=[
                Slide(
                    id="s1",
                    title="a",
                    layout_archetype="opener",
                    blocks=[TextBlock(kind="text", style="headline", content="A")],
                )
            ],
        )
    )
    assert a != b


def test_fingerprint_distinguishes_archetype_sequences() -> None:
    a = deck_fingerprint(
        Deck(
            family_id="editorial-serif",
            slides=[
                Slide(
                    id="s1",
                    title="a",
                    layout_archetype="opener",
                    blocks=[TextBlock(kind="text", style="headline", content="A")],
                )
            ],
        )
    )
    b = deck_fingerprint(
        Deck(
            family_id="editorial-serif",
            slides=[
                Slide(
                    id="s1",
                    title="a",
                    layout_archetype="closer",
                    blocks=[TextBlock(kind="text", style="headline", content="A")],
                )
            ],
        )
    )
    assert a != b


def test_distribution_ratio_measures_collapse() -> None:
    varied = Deck(
        family_id="editorial-serif",
        slides=[
            Slide(
                id=f"s{i}",
                title="x",
                layout_archetype=a,
                blocks=[TextBlock(kind="text", style="headline", content="H")],
            )
            for i, a in enumerate(["opener", "statement", "split", "stats"])
        ],
    )
    # 1 - (1/4): every slide distinct means most_common = 1 of 4.
    assert distribution_ratio(varied) == 0.75

    collapsed = Deck(
        family_id="editorial-serif",
        slides=[
            Slide(
                id=f"s{i}",
                title="x",
                layout_archetype="statement",
                blocks=[TextBlock(kind="text", style="headline", content="H")],
            )
            for i in range(6)
        ],
    )
    assert distribution_ratio(collapsed) == 0.0  # all one frame


def test_acceptance_brief_passes_with_varied_deck() -> None:
    seam = FakeSeam(["opener", "statement", "split", "stats", "quote", "closer"])
    result = run_acceptance_brief(_brief(), seam, model="m")
    assert isinstance(result, Ok)
    assert result.value.distribution_ratio >= 0.4


def test_summary_fails_on_fingerprint_collapse() -> None:
    # Two briefs that map to identical decks (same family, same archetypes).
    # Alternating two archetypes passes the consecutive-check but collapses on
    # the fingerprint (the two briefs are indistinguishable).
    seam = FakeSeam(["statement", "split"] * 4)
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
                layout_archetype="list",
                blocks=[TextBlock(kind="text", style="headline", content="H")],
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
    )
    passed, report = acceptance_summary([result])
    assert not passed
    assert "DISTRIBUTION COLLAPSE" in report


def test_golden_briefs_are_all_valid() -> None:
    assert len(GOLDEN_BRIEFS) >= 5
    for brief in GOLDEN_BRIEFS:
        assert brief.topic
        assert 1 <= brief.slide_count <= 40
