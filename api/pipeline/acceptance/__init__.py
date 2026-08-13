"""Acceptance — the golden run and the variety fingerprint.

Runs the golden briefs through the pipeline and asserts schema-validity and
variety (the fingerprint metric). This is the falsifier for the core bet.
"""

from pipeline.acceptance.acceptance import (
    AcceptanceResult,
    acceptance_summary,
    run_acceptance_brief,
)
from pipeline.acceptance.fingerprint import deck_fingerprint, distribution_ratio

__all__ = [
    "AcceptanceResult",
    "acceptance_summary",
    "deck_fingerprint",
    "distribution_ratio",
    "run_acceptance_brief",
]
