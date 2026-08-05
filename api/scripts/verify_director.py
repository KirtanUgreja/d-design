"""Run every golden brief through the Director and print the outlines, to
close phase 07's exit gate (docs/v1/plan/07-director.md -> Verify -> "the 5
golden briefs each produce a valid `Outline` on the first call").

Two things this proves and one it deliberately does not. It proves the call
succeeds on the first attempt — `direct_brief` has no retry of its own, so a
`Result` back is a first-call result by construction — and that `check_outline`
passes, which is where the `layoutHint` completeness and no-adjacent-repeat
rules live. It does not judge whether the outlines *read* as narratives: the
phase doc is explicit that the quality read "is judgment and belongs to you,
not to a judge model", so this prints them for a human and scores nothing.

Real, billed calls — one per brief, five total. Cheap next to the Build eval,
which is several calls per scene.

    uv run --env-file .env python -m scripts.verify_director
"""

import asyncio
import json
import sys
from pathlib import Path

from config import config
from features.director import direct_brief
from lib.result import Err
from schema.brief import Brief

_BRIEFS = Path(__file__).parent.parent / "evals" / "briefs"


async def _run() -> int:
    failures = 0
    for path in sorted(_BRIEFS.glob("*.json")):
        brief = Brief.model_validate(json.loads(path.read_text())["brief"])
        result = await direct_brief(
            brief=brief,
            owner_id=config().local_user_id,
            # Metering needs an experience id; nothing is written to this one.
            experience_id="00000000-0000-4000-8000-0000000000dd",
        )
        if isinstance(result, Err):
            failures += 1
            print(f"\n{path.name}: FAIL {result.error.code} — {result.error.message}")
            continue

        outline = result.value
        print(f"\n{path.name}: OK — {outline.title!r}")
        for scene in outline.scenes:
            print(f"    {scene.intent:<8} [{scene.layout_hint}]  {scene.beat}")

    print(f"\n{'FAILED' if failures else 'all briefs produced a valid Outline'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_run()))
