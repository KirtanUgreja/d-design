"""The Pydantic source of truth for the whole system, and the catalog every
later phase reads before writing something that already exists.

This package has no TypeScript counterpart. `web` consumes generated types and
a generated Zod validator; creating a hand-written schema on the TypeScript
side is the drift this whole arrangement exists to prevent
(docs/coderules/structure.md, docs/coderules/python.md).

`EXPORTED` is the codegen's input. A model listed here is emitted into
`web/src/schema/` by `web/scripts/generate-schema.mjs`; a model not listed here
stays inside Python. Adding a row is how a shape becomes part of the contract —
`Experience` pulls in `Scene` and every block type as `$defs`, so most of the
tree below is exported without being listed twice.
"""

from pydantic import BaseModel

from schema.brief import Brief
from schema.experience import Asset, BrandKit, Experience
from schema.outline import Outline
from schema.patch import BlockPatch
from schema.scene import Block, Scene

EXPORTED: dict[str, type[BaseModel]] = {
    "Experience": Experience,
    "Scene": Scene,
    "Block": Block,
    "Asset": Asset,
    "BrandKit": BrandKit,
    "Brief": Brief,
    "Outline": Outline,
    "BlockPatch": BlockPatch,
}

__all__ = [
    "EXPORTED",
    "Asset",
    "Block",
    "BlockPatch",
    "BrandKit",
    "Brief",
    "Experience",
    "Outline",
    "Scene",
]
