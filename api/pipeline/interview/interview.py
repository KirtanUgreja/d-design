"""The interview orchestrator — a plain deterministic function, not an agent.

Takes the user's typed Brief, makes one schema-validated model call through
the seam, and returns an Outline (or a typed error). The Outline is validated
at the boundary, run through the no-styling backstop, and carries claim
provenance — this is the trust device the whole pipeline rests on
(spec.md risk 2).

Prompt injection is live from the first call: the user's topic, brand kit and
extra info are untrusted data framed as data (prompts.py Defense 3), and the
outline is schema-validated before it is trusted anywhere.
"""

from __future__ import annotations

from ai.complete import ModelError, Seam
from lib.result import Err, Result, ok
from pipeline.interview import prompts
from schema.no_style import assert_no_presentational_values
from schema.outline import Brief, Outline


def run_interview(brief: Brief, seam: Seam, model: str) -> Result[Outline, ModelError]:
    """Run the interview: Brief -> schema-validated Outline.

    ``seam`` is injected so tests never hit the network. The seam owns the
    single repair retry; the orchestrator owns the pipeline shape and the
    backstop, nothing else.
    """
    user = prompts.build_user_prompt(
        topic=brief.topic,
        slide_count=brief.slide_count,
        audience=brief.audience,
        goal=brief.goal,
        brand=(
            " ".join(
                part
                for part in (
                    brief.brand_kit.colors,
                    brief.brand_kit.fonts,
                    brief.brand_kit.vibe,
                )
                if part
            )
        ),
        extra=brief.extra_info,
    )

    result = seam.complete(
        phase="interview",
        schema=Outline,
        system=prompts.SYSTEM,
        user=user,
        model=model,
    )

    if isinstance(result, Err):
        return result

    outline = result.value
    # The schema is the first line; the backstop is the second. A presentational
    # value in an outline is a schema gap, never content.
    assert_no_presentational_values(outline.model_dump())
    return ok(outline)
