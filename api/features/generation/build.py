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
from functools import partial

from ai.complete import complete
from features.director import ApprovedOutline

# Direct submodule imports, not `from features.generation import ...` — this
# module is itself re-exported through that package's `__init__.py`, and
# routing back through it here would be a circular import.
from features.generation.checks import check_scene, find_truncation
from features.generation.prompts.build import (
    build_scene_user_prompt,
    build_system_prompt,
)
from features.generation.tools import get_brand_kit, list_assets
from lib.result import Err, Result, err, ok
from schema.brief import Brief
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
    approved_outline: ApprovedOutline,
    brand_id: str | None,
    owner_id: str,
    experience_id: str,
) -> AsyncIterator[BuildEvent]:
    """Yields one `BuildEvent` per outline scene, in order. A failure —
    repair-exhausted, refused, or a failed post-build check — is yielded
    rather than raised, and the loop continues: failure at scene 6 of 8
    keeps the five that already succeeded (docs/v1/plan/06-model-seam-and-build.md
    -> "7b. What the client does with those events"), and it is the
    caller's job to decide whether to keep streaming or stop.

    Takes `ApprovedOutline`, not `Outline` — Build only ever runs against a
    structure the user already approved, and mypy enforces that on every
    call site (docs/v1/plan/07-director.md -> "The gate is the product
    decision"), not only the route layer's own discipline."""
    outline = approved_outline.outline
    brand_kit = get_brand_kit(brand_id)
    assets = list_assets()
    system = build_system_prompt(brief, outline, brand_kit, assets)
    total = len(outline.scenes)

    for index, outline_scene in enumerate(outline.scenes):
        user = build_scene_user_prompt(outline_scene, index, total)

        call = partial(
            complete,
            phase="build",
            schema=Scene,
            system=system,
            user=user,
            owner_id=owner_id,
            experience_id=experience_id,
        )

        result = await call()
        if isinstance(result, Err):
            yield BuildEvent(index=index, result=result, repaired=False)
            continue
        completion = result.value

        # The seam's own repair cannot see this one: the provider truncates
        # copy at the schema's `maxLength` during decoding, and what comes back
        # is structurally valid, so `model_validate` succeeds and there is
        # nothing for a repair prompt to be built from
        # (docs/v1/plan/06-model-seam-and-build.md -> "Open defect"). Asking
        # again is the whole remedy available here — the model wrote fine copy
        # and the transport cut it, so a second draw is a genuinely different
        # roll rather than the same failure repeated.
        redrawn = False
        if find_truncation(completion.value) is not None:
            redrawn = True
            retry = await call()
            if isinstance(retry, Err):
                yield BuildEvent(index=index, result=retry, repaired=True)
                continue
            completion = retry.value
            truncated = find_truncation(completion.value)
            if truncated is not None:
                # Losing the scene beats shipping it. Garbled copy on a
                # published page is the failure this whole check exists to
                # stop, and "failure at scene 6 of 8 keeps the five" is
                # already how this loop is designed to degrade.
                yield BuildEvent(
                    index=index,
                    result=err("invalid_input", f"truncated copy: {truncated}"),
                    repaired=True,
                )
                continue

        checked = check_scene(completion.value, brief)
        if isinstance(checked, Err):
            yield BuildEvent(index=index, result=checked, repaired=False)
            continue

        yield BuildEvent(
            index=index,
            result=ok(completion.value),
            # A redraw counts as a repair: same meaning to the client, which
            # renders it as nothing at all, and the same thing worth counting
            # in `generations` — this is now the only place a truncation rate
            # is observable at all.
            repaired=completion.repaired or redrawn,
        )
