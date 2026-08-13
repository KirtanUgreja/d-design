"""Interview — the first pipeline phase.

Turns the user's typed Brief into an approved, schema-validated Outline via one
model call through the seam. The Outline is the approved-claims record the
mapping pass consumes.
"""

from pipeline.interview.interview import run_interview

__all__ = ["run_interview"]
