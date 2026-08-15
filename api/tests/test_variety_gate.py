"""Variety-gate tests (phase 15).

The gate is the falsifier for the v2 bet: if the design engine collapses —
two decks converge on a fingerprint, or a deck collapses to one frame — the
gate must fail loudly. These tests prove the gate is a gate, not decoration:
a healthy deterministic run passes, and a collapsed one fails with a named
violation.
"""

from __future__ import annotations

from lib.result import Err, Ok
from pipeline.acceptance.acceptance import acceptance_summary, run_acceptance_brief
from pipeline.acceptance.briefs import GOLDEN_BRIEFS
from pipeline.acceptance.gate import DeterministicSeam, run_variety_gate


def test_gate_passes_on_a_healthy_design_space() -> None:
    passed, report = run_variety_gate()
    assert passed, report
    assert "fingerprints:" in report
    assert "COLLAPSE" not in report


def test_gate_runs_every_golden_brief() -> None:
    seam = DeterministicSeam()
    for brief in GOLDEN_BRIEFS:
        result = run_acceptance_brief(brief, seam, model="gate-model")
        assert isinstance(result, Ok), _detail(result)
    # The healthy gate reaches every brief.
    passed, report = run_variety_gate()
    assert passed, report


def test_gate_is_deterministic() -> None:
    # The same run twice gives the same verdict — a standing gate must be
    # reproducible, or it would flake in CI.
    p1, r1 = run_variety_gate()
    p2, r2 = run_variety_gate()
    assert p1 == p2
    assert r1 == r2


def test_gate_fails_on_distribution_collapse() -> None:
    # A deck that collapses onto one layout must fail the within-deck
    # distribution claim. This is what a collapsed engine produces.
    from pipeline.acceptance.acceptance import AcceptanceResult
    from pipeline.acceptance.fingerprint import distribution_ratio
    from schema.deck import (
        Deck,
        LayoutRegion,
        LayoutStructure,
        Slide,
        TextBlock,
    )

    collapsed = Deck(
        family_id="editorial-serif",
        slides=[
            Slide(
                id=f"s{i}",
                title="x",
                layout=LayoutStructure(regions=[LayoutRegion(role="headline", span="full")]),
                blocks=[TextBlock(kind="text", style="headline", content="H")],
            )
            for i in range(6)
        ],
    )
    assert distribution_ratio(collapsed) == 0.0
    result = AcceptanceResult(
        brief=GOLDEN_BRIEFS[0],
        deck=collapsed,
        fingerprint="x",
        distribution_ratio=distribution_ratio(collapsed),
        chart_ratio=1.0,
    )
    passed, report = acceptance_summary([result])
    assert not passed
    assert "DISTRIBUTION COLLAPSE" in report


def test_gate_fails_on_cross_deck_fingerprint_collapse() -> None:
    # Two DIFFERENT briefs that produce the same fingerprint must fail the
    # cross-deck claim — the falsifier for the v2 bet (two decks converge).
    from dataclasses import replace

    from pipeline.acceptance.fingerprint import deck_fingerprint

    seam = DeterministicSeam()
    r1 = run_acceptance_brief(GOLDEN_BRIEFS[0], seam, model="gate-model")
    r2 = run_acceptance_brief(GOLDEN_BRIEFS[1], seam, model="gate-model")
    assert isinstance(r1, Ok) and isinstance(r2, Ok)

    # Force the collapse: two distinct briefs, identical fingerprints.
    r2_forced = replace(r2.value, fingerprint=r1.value.fingerprint)
    passed, report = acceptance_summary([r1.value, r2_forced])
    assert not passed
    assert "FINGERPRINT COLLAPSE" in report
    assert deck_fingerprint(r1.value.deck) != deck_fingerprint(r2.value.deck)


def _detail(result: object) -> str:
    """A readable failure detail for an Err result in an assertion message."""
    if isinstance(result, Err):
        return str(result.error)
    return ""
