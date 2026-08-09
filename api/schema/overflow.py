"""Content that will not fit, reported rather than rewritten.

docs/v2/transformations.md -> "The overflow problem". The rule this schema
exists to serve is v2 rule 17: **nothing rewrites approved copy without being
asked.** Auto-shortening would be seamless and would silently alter marketing
copy someone got legal approval on — for this wedge that is not a bug, it is a
lawsuit. So overflow is a *report*, it is deliberately visible, and shortening
is a separate action the user takes.

**One report type, four producers.** Generation, edit, reskin and slides mode
can all create the condition, and the banner does not say which did — a user
who has just reskinned does not need to be told that reskinning is what
overflowed their headline. Phase 10's exit gate is explicit that if slides mode
appears to need its own overflow concept, one of the two designs is wrong.

It lives in `schema/` rather than in a feature because `web` renders the banner
and therefore needs the type, and every type crossing that boundary is
generated from Pydantic rather than hand-written twice.
"""

from pydantic import Field

from schema.base import Schema


class BlockExtent(Schema):
    """One block's measured height, so the banner can point at a culprit rather
    than at a scene."""

    block_id: str = Field(min_length=1)
    block_size: int = Field(ge=0)


class SceneOverflow(Schema):
    """One scene that does not fit its frame.

    Both sizes are carried, not just the difference: "over by 40px" and "over by
    40px in a 760px frame" are very different problems, and the second is the
    one a user can act on.
    """

    scene_id: str = Field(min_length=1)
    frame_block_size: int = Field(ge=0)
    content_block_size: int = Field(ge=0)
    blocks: list[BlockExtent] = Field(default_factory=list)

    @property
    def overflow_by(self) -> int:
        return max(0, self.content_block_size - self.frame_block_size)


class OverflowReport(Schema):
    """Only the scenes that overflow. An empty list is the ordinary case and is
    the shape the banner checks — a report that listed every scene would make
    "does anything overflow" a filter rather than a truth value."""

    scenes: list[SceneOverflow] = Field(default_factory=list)

    @property
    def any_overflow(self) -> bool:
        return len(self.scenes) > 0
