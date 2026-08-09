"""Ask the browser, because nothing else can answer.

Whether copy fits is a question about line breaking, font metrics, clamped type
and the art direction's own frame. A character count cannot answer it, and a
product that guesses tells a customer their approved headline fits and then
clips it. So the measurement happens where a layout exists — the `render`
service from phase 00, which is its first customer, ahead of the critic.

`render` holds no credential and this module sends it none: a scene tree, an
art-direction record, a viewport. That is the whole payload, and it is why
calling a browser-driving service from here is safe.

**The record rather than an id, since v2 phase 01.** Art directions became
database rows, and `render` cannot read the store — it holds no credential, by
design, because that is what makes running a browser next to it safe. So the
tokens travel on the wire, and `render` parses them with the same generated
validator `web` uses. A record has no field a free-form CSS string can arrive
in, which is what keeps that safe rather than merely convenient.
"""

import httpx
from pydantic import TypeAdapter, ValidationError

from config import config
from lib.result import Result, err, ok
from schema.art_direction import ArtDirectionRecord
from schema.motion import MotionVocabularyRecord
from schema.overflow import BlockExtent, OverflowReport, SceneOverflow
from schema.scene import Scene

# Generous. A cold `render` launches Chromium on the first request, and the
# failure this guards is a hung browser rather than a slow one.
_TIMEOUT = httpx.Timeout(60.0, connect=5.0)

# One parse for the service's response, at the boundary, like every other
# external input (rule 2) — `render` is another process, so its output is not
# trusted merely because we wrote it.
_EXTENTS = TypeAdapter(list["SceneExtent"])


class SceneExtent(SceneOverflow):
    """What `render` measured, which is the same shape as what is reported —
    minus the decision about whether it counts as overflow.

    Subclassing rather than declaring a parallel model: the two differ by a
    judgement, not by a field, and two near-identical models would drift the
    first time a block gained an attribute.
    """


async def measure_overflow(
    *,
    scenes: list[Scene],
    art_direction: ArtDirectionRecord,
    motion_vocabulary: MotionVocabularyRecord,
    viewport_height: int,
    viewport_width: int = 1280,
) -> Result[OverflowReport]:
    """Every scene whose content exceeds its frame, and nothing else.

    A failure to *measure* is an error, never an empty report. "We could not
    check" and "nothing overflows" must not be the same value — the second is a
    green banner, and rule 10's reasoning applies to any check that could grant
    something, including permission to publish without a warning.
    """
    payload = {
        "scenes": [scene.model_dump(mode="json", by_alias=True) for scene in scenes],
        "artDirection": art_direction.model_dump(
            mode="json", by_alias=True, exclude_none=True
        ),
        # The second axis. `render` resolves neither and holds no credential to;
        # both travel as validated records and are parsed there by the same
        # generated validators.
        "motionVocabulary": motion_vocabulary.model_dump(mode="json", by_alias=True),
        "viewport": {"width": viewport_width, "height": viewport_height},
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(f"{config().render_url}/measure", json=payload)
    except httpx.HTTPError as e:
        return err("upstream_unavailable", f"render unreachable: {type(e).__name__}")

    if response.status_code != 200:
        return err(
            "upstream_unavailable",
            f"render {response.status_code}: {response.text[:200]}",
        )

    try:
        extents = _EXTENTS.validate_python(response.json())
    except (ValidationError, ValueError) as e:
        return err("upstream_unavailable", f"render returned an unreadable body: {e}")

    return ok(
        OverflowReport(
            scenes=[
                SceneOverflow(
                    scene_id=extent.scene_id,
                    frame_block_size=extent.frame_block_size,
                    content_block_size=extent.content_block_size,
                    # Only the blocks worth pointing at. Every block in an
                    # overflowing scene is technically implicated; the tall ones
                    # are the ones a user can do something about, and a banner
                    # listing eight is a banner nobody reads.
                    blocks=_culprits(extent.blocks),
                )
                for extent in extents
                if extent.content_block_size > extent.frame_block_size
            ]
        )
    )


def _culprits(blocks: list[BlockExtent]) -> list[BlockExtent]:
    return sorted(blocks, key=lambda b: b.block_size, reverse=True)[:3]
