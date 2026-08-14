"""The acceptance runner (plan/08).

Runs a brief through the whole pipeline — interview → mapping → build — and
asserts the two things that make the product claim true:

1. **Schema-validity**: every phase's output parses against the schema.
2. **Variety**: two decks sampled from the registry differ in fingerprint
   beyond threshold, and within a deck the archetypes are distributed (no
   collapse onto one frame).

Image generation is part of the golden run — a product-launch brief wants a
hero — but is stubbed in the deterministic test path. The real image calls are
a per-deck cost the visual review (phase 07) gates on quality.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai.complete import ModelError, Seam
from lib.result import Err, Result, ok
from pipeline.acceptance.fingerprint import (
    chart_type_ratio,
    deck_fingerprint,
    distribution_ratio,
)
from pipeline.interview.interview import run_interview
from pipeline.mapping.mapping import run_mapping
from schema.deck import Deck
from schema.no_style import assert_no_presentational_values
from schema.outline import Brief

# Two sampled decks must differ in fingerprint — the falsifier for the
# combinatorial-space bet. Colliding fingerprints mean the design system is
# producing variations of one thing.
MIN_FINGERPRINT_DISTINCT = 2

# Within a deck, at least 30% of slides must not be the most-common archetype.
# The mapping's consecutive-run check (no archetype 3 in a row) bounds how far
# a single archetype can dominate in 12 slides to ~0.6; this gate catches the
# residual: a deck that spreads one archetype 2-in-a-row throughout is still a
# collapse even though no run tripped.
MIN_DISTRIBUTION_RATIO = 0.3

# Within a deck with 2+ charts, at least 50% must not be the most-common chart
# type. A deck that draws the same chart everywhere is a chart collapse (phase
# 11 — chart variety is part of the fingerprint claim).
MIN_CHART_RATIO = 0.5


@dataclass(frozen=True)
class AcceptanceResult:
    brief: Brief
    deck: Deck
    fingerprint: str
    distribution_ratio: float
    chart_ratio: float


def run_acceptance_brief(
    brief: Brief,
    seam: Seam,
    model: str,
    family_id: str | None = None,
) -> Result[AcceptanceResult, ModelError]:
    """Run one brief end to end (interview + mapping), stub the build, and
    assert the acceptance properties on the mapped Deck.

    The build pass is stubbed here (the real per-slide generation is a model
    call per slide; the acceptance run asserts the *design-space* claims that
    are deterministic: schema-validity, backstop, fingerprint, distribution).
    """
    outline_result = run_interview(brief, seam, model=model)
    if isinstance(outline_result, Err):
        return outline_result

    mapping_result = run_mapping(
        outline_result.value,
        seam,
        model=model,
        family_id=family_id,
    )
    if isinstance(mapping_result, Err):
        return mapping_result

    deck = mapping_result.value
    # Schema-validity is structural; the backstop is the second line.
    assert_no_presentational_values(deck.model_dump())

    return ok(
        AcceptanceResult(
            brief=brief,
            deck=deck,
            fingerprint=deck_fingerprint(deck),
            distribution_ratio=distribution_ratio(deck),
            chart_ratio=chart_type_ratio(deck),
        )
    )


def acceptance_summary(
    results: list[AcceptanceResult],
) -> tuple[bool, str]:
    """The overall verdict and a human-readable report.

    Returns (passed, report). The report names every violation; a single
    violation fails the run — the variety claim is a gate, not a trend.
    """
    lines: list[str] = []

    fingerprints = [r.fingerprint for r in results]
    distinct = len(set(fingerprints))
    if distinct < MIN_FINGERPRINT_DISTINCT:
        lines.append(
            f"FINGERPRINT COLLAPSE: {len(results)} briefs produced only {distinct} "
            f"distinct fingerprint(s); expected >= {MIN_FINGERPRINT_DISTINCT}"
        )
    else:
        lines.append(f"fingerprints: {distinct} distinct across {len(results)} briefs")

    bad_distribution = [r for r in results if r.distribution_ratio < MIN_DISTRIBUTION_RATIO]
    for r in bad_distribution:
        lines.append(
            f"DISTRIBUTION COLLAPSE: '{r.brief.topic[:40]}' has ratio "
            f"{r.distribution_ratio:.2f}; expected >= {MIN_DISTRIBUTION_RATIO}"
        )

    bad_charts = [r for r in results if r.chart_ratio < MIN_CHART_RATIO]
    for r in bad_charts:
        lines.append(
            f"CHART COLLAPSE: '{r.brief.topic[:40]}' has chart ratio "
            f"{r.chart_ratio:.2f}; expected >= {MIN_CHART_RATIO}"
        )

    passed = not lines or all(
        not line.startswith(("FINGERPRINT", "DISTRIBUTION", "CHART")) for line in lines
    )
    return passed, "\n".join(lines)
