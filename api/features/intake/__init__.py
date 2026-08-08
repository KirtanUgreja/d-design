"""Intake's public surface: the interview loop, and the store for what it
produces (docs/v1/plan/08-intake.md).

Behaviour only. `InterviewStep`, `Question` and `Brief` are in `schema/`
because they cross the language boundary, and a caller wanting one imports it
from there — re-exporting them here would give the same shape two import paths
and make "one source" a matter of which one you happened to type.
"""

from features.intake.intake_data import load_brief, save_brief
from features.intake.interview import advance, next_question

__all__ = [
    "advance",
    "load_brief",
    "next_question",
    "save_brief",
]
