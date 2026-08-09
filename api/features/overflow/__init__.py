"""Measuring what will not fit.

docs/v2/plan/13-scene-fit.md -> "Viewport overflow arrives here, not in phase
10". `fit: 'viewport'` gives every scene a frame, and the moment a scene has a
frame, content can exceed it — in **scroll** mode, four phases before slides
mode would have raised the same question.

**Its own feature, not `features/reskin/`.** Phase 13 put this in reskin's
module, which was the right guess when reskin was the only caller anyone had
named. The same phase then lists four: generation, edit, reskin and slides
mode. A concept with four callers that lives inside one of them is a concept
three features have to import across a boundary that says they should not
(rule 4), so it gets its own public surface and reskin becomes a consumer like
everything else.

**Nothing here rewrites anything.** Rule 17: overflow is reported, visibly and
deliberately annoyingly, and shortening is a separate action the user asks for.
"""

from features.overflow.measure import measure_overflow

__all__ = ["measure_overflow"]
