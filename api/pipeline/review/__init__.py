"""Review — the human visual review loop.

A human reviews the exported deck and sends slides back for regeneration with
written feedback. The repair is a per-slide re-call. This is the last human
step before the acceptance run.
"""

from pipeline.review.review import revise_slide

__all__ = ["revise_slide"]
