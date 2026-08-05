"""One call per scene, streamed (docs/v1/plan/06-model-seam-and-build.md).

Sequential, not parallel-with-cache-warming — docs/v1/ai-pipeline.md leaves
parallel-vs-sequential build as an open question, and sequential is simpler,
provably correct (each call already reads the cache the previous one wrote,
since it runs after), and still streams each scene to the caller as it
completes. ponytail: the cache-warming pattern (fire scene 1, await its
first token, then fire the rest concurrently) is the upgrade path if build
latency becomes the thing to cut.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from ai.complete import complete

# Direct submodule imports, not `from features.generation import ...` — this
# module is itself re-exported through that package's `__init__.py`, and
# routing back through it here would be a circular import.
from features.generation.checks import check_scene
from features.generation.prompts.build import (
    build_scene_user_prompt,
    build_system_prompt,
)
from features.generation.tools import get_brand_kit, list_assets
from lib.result import Err, Result, ok
from schema.brief import Brief
from schema.outline import Outline
from schema.scene import Scene


@dataclass(frozen=True, slots=True)
class BuildEvent:
    """One outline position's outcome, plus its index — the route needs both
    to shape the `scene` / `repair` / `error` SSE events
    (docs/v1/plan/06-model-seam-and-build.md -> "7. Streaming to the
    client"). `repaired` is only ever true alongside an `Ok` result — a
    repair that still failed surfaces as `repair_exhausted` in `result`, not
    as `repaired=True`."""

    index: int
    result: Result[Scene]
    repaired: bool


async def build_experience(
    *,
    brief: Brief,
    outline: Outline,
    brand_id: str | None,
    owner_id: str,
    experience_id: str,
) -> AsyncIterator[BuildEvent]:
    """Yields one `BuildEvent` per outline scene, in order. A failure —
    repair-exhausted, refused, or a failed post-build check — is yielded
    rather than raised, and the loop continues: failure at scene 6 of 8
    keeps the five that already succeeded (docs/v1/plan/06-model-seam-and-build.md
    -> "7b. What the client does with those events"), and it is the
    caller's job to decide whether to keep streaming or stop."""
    brand_kit = get_brand_kit(brand_id)
    assets = list_assets()
    system = build_system_prompt(brief, outline, brand_kit, assets)
    total = len(outline.scenes)

    for index, outline_scene in enumerate(outline.scenes):
        user = build_scene_user_prompt(outline_scene, index, total)
        result = await complete(
            phase="build",
            schema=Scene,
            system=system,
            user=user,
            owner_id=owner_id,
            experience_id=experience_id,
        )
        if isinstance(result, Err):
            yield BuildEvent(index=index, result=result, repaired=False)
            continue

        completion = result.value
        checked = check_scene(completion.value, brief)
        if isinstance(checked, Err):
            yield BuildEvent(index=index, result=checked, repaired=False)
            continue

        yield BuildEvent(
            index=index, result=ok(completion.value), repaired=completion.repaired
        )
