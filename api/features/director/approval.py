"""The outline-approval gate (docs/v1/plan/07-director.md -> "The gate is
the product decision", "Build cannot run until the user approves").

`build_experience`'s own signature requires an `ApprovedOutline`, not a
bare `Outline` — so the gate is enforced at the function boundary mypy
checks on every call site, not only by a UI convention a future caller
(a route, a script, a batch job) could route around. "The UI is not the
control" (docs/v1/plan/07-director.md -> "Verify").

This cannot cryptographically prove a human clicked Approve — v1 has no
session or persisted-outline state to check that against. What it does
give: the one place in the codebase where "this outline is being treated
as reviewed" has to appear in a diff, the same discipline `as_user()` and
`Result` already hold this codebase to (docs/coderules/patterns.md, rules
4 and 9).
"""

from dataclasses import dataclass

from schema.outline import Outline


@dataclass(frozen=True, slots=True)
class ApprovedOutline:
    outline: Outline


def approve_outline(outline: Outline) -> ApprovedOutline:
    return ApprovedOutline(outline)
