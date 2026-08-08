"""An edit. One shape, one code path.

Property-panel edits and element-scoped AI edits produce the identical patch,
so there is one place for validation to live and one thing to get right. A full
regeneration is never triggered by an edit.

`props` is a partial — the fields the caller is changing — so it is untyped
here and typed the moment it is merged into the block and the whole tree is
re-validated. That is the one parse, at the one boundary: a patch is external
input whether it came from a panel or from a model.
"""

from pydantic import Field

from schema.base import Schema
from schema.scene import BlockProps


class BlockPatch(Schema):
    scene_id: str = Field(min_length=1)
    block_id: str = Field(min_length=1)
    props: dict[str, object] = Field(min_length=1)


class EditResult(Schema):
    """What an edit returns to `web`.

    `props` is the same partial a property-panel edit produces, so the two
    become byte-identical `BlockPatch`es on the client and there is one code
    path and one validation site. It is computed by `edit_block`, by diffing
    the model's `EditDraft` against the block it was given — the model never
    produces a partial itself, because a partial is an open dict and strict
    structured outputs cannot express one.

    `refusal` is the other half of the phase's design, not an error path.
    Someone types "make the headline smaller" and the output shape has no
    field for it; what they get back has to be a written sentence offering
    emphasis instead, because that is "the most-read sentence the product will
    ship" (docs/v1/plan/09-editor.md -> "Design the absence"). A refusal with
    empty `props` is a complete, successful response.
    """

    props: dict[str, object] = Field(default_factory=dict)
    refusal: str | None = Field(default=None, max_length=400)


class EditDraft(Schema):
    """What the Edit model actually returns — and, like `BriefDraft`, it is
    internal. `web` only ever sees the `EditResult` below.

    `props` is the block's **whole**, fully typed props object, not a partial,
    and that is forced rather than chosen: a partial is an open dict, and
    OpenAI's `strict: true` structured outputs cannot express one — every
    object must declare its properties with `additionalProperties: false`.
    Sending `dict[str, object]` produced a schema the provider rejected
    outright, which is how this was found.

    Being forced here turned out to be the stronger design. A typed
    `BlockProps` has no field for a colour, a size, a font or a duration, so
    rule 3 of the Edit prompt stops being an instruction the model may ignore
    and becomes a shape it cannot fill — the same move as `BriefDraft` having
    no `audience`. `edit_block` diffs the result against the block it sent, so
    what leaves the server is still the `Partial<BlockProps>` the phase doc
    specifies, and an edit is still a diff rather than a rewrite.

    There is no `scene_id` and no `block_id`: the caller already knows which
    block it asked about, and a model that cannot name a target cannot
    retarget an edit at a neighbour.
    """

    props: BlockProps
    refusal: str | None = Field(default=None, max_length=400)
