"""The critic verdict schema — the vision critic's small, fixed output (phase 13).

pipeline-tools.md: the critic's output is a small fixed schema — a verdict and
a list of findings, not free text or instructions. That is the injection
containment: the critic is itself a model reading a page assembled from
untrusted content, so its output cannot carry instructions to act on.

A finding's ``kind`` is one of the structural defects findings.md measured as
the real ones (overflow, cramped spacing, contrast, an empty region, a chart
that renders as a grey rectangle). ``note`` is bounded prose about *what broke*,
never a directive. The schema carries no presentational values (rule 1) — a
critic finding cannot name a hex, a px, or a font.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CriticFinding(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """One structural defect the critic saw, or a minor observation."""

    kind: Literal["overflow", "cramped", "contrast", "empty_region", "chart_breakage"]
    severity: Literal["blocker", "minor"]
    note: str = Field(min_length=1, max_length=200)


class CriticVerdict(BaseModel):  # type: ignore[explicit-any]  # pydantic stubs are untyped
    """The critic's whole answer for one slide.

    ``accept`` means no revision. ``revise`` triggers at most one corrective
    pass (the bounded loop in vision_critic — a literal limit, never a while).
    """

    verdict: Literal["accept", "revise"]
    findings: list[CriticFinding] = Field(default_factory=list, max_length=5)
