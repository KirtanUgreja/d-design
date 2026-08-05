"""Brief -> Outline, one call, no tools, no retry or metering of its own
beyond what the seam already gives (docs/v1/plan/07-director.md -> "The
call"): "It gets no retry of its own, no parse of its own, no metering of
its own." `check_outline`'s failure is not repaired here either — the
UI's answer to a bad outline is "regenerate," a fresh call, not an
internal loop this function grows on its own.
"""

from ai.complete import complete
from features.director.checks import check_outline
from features.director.prompts.director import build_director_prompt
from lib.result import Err, Result, ok
from schema.brief import Brief
from schema.outline import Outline


async def direct_brief(
    *, brief: Brief, owner_id: str, experience_id: str
) -> Result[Outline]:
    system, user = build_director_prompt(brief)
    result = await complete(
        phase="director",
        schema=Outline,
        system=system,
        user=user,
        owner_id=owner_id,
        experience_id=experience_id,
    )
    if isinstance(result, Err):
        return result

    outline = result.value.value
    checked = check_outline(outline)
    if isinstance(checked, Err):
        return checked

    return ok(outline)
