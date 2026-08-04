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


class BlockPatch(Schema):
    scene_id: str = Field(min_length=1)
    block_id: str = Field(min_length=1)
    props: dict[str, object] = Field(min_length=1)
